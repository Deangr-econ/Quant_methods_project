"""Fixed, exploratory VAR lag/data sensitivities on unchanged forecast dates."""
import numpy as np
import pandas as pd

from har_return_audit import paired_block_intervals
from var_har_notebook import (prepare_har_data, aligned_design, model_specifications,
    expanding_forecasts, forecast_metrics, columns_for)
from volare_data import validate_source, quality_flags
from volare_review import reconcile_reviews


def flag_evidence(raw, ledger, source_sha256, start="2011-01-01"):
    """Screen/reconcile the unchanged source; price identities are not validation."""
    data = validate_source(raw)
    flags = reconcile_reviews(quality_flags(data), ledger, source_sha256)
    prices = data.copy()
    previous = prices.groupby("symbol").close_price.shift()
    prices["opening_gap_pct"] = 100*np.log(prices.open_price/previous)
    prices["open_to_close_pct"] = 100*np.log(prices.close_price/prices.open_price)
    flags = flags.merge(prices[["date", "symbol", "opening_gap_pct", "open_to_close_pct"]],
        on=["date", "symbol"], validate="one_to_one")
    np.testing.assert_allclose(flags.unadjusted_close_log_return_pct,
        flags.opening_gap_pct + flags.open_to_close_pct, atol=1e-10)
    flags = flags.loc[flags.date.ge(start)].copy()
    flags["assessment"] = np.where(flags.decision.eq("retain_crisis_move_provisional"),
        "Crisis move provisionally retained; quote/session not independently verified",
        np.where(flags["flags"].str.contains("rk_rv5_disagreement"),
            "Suspected quote/estimator contamination; unresolved",
            "Large price move or possible contract transition; unresolved"))
    flags["confirmed_error"] = False
    return flags


def exposure_mask(raw, wide, design, issues, window=22):
    """Conservative row eligibility after building features on the fixed grids.

    Cover source-grid HAR means, retained-grid lags/downside means and flagged
    system outcomes. An ES quote affects the following ES close return too.
    Never reconstruct lags after removing a date.
    """
    if window < 22:
        raise ValueError("Exposure window must cover monthly/downside features")
    issues = pd.DataFrame(issues, columns=["date", "symbol"]).copy()
    issues["date"] = pd.to_datetime(issues.date)
    source = raw.copy()
    source["date"] = pd.to_datetime(source.date)
    keys = pd.MultiIndex.from_frame(source[["date", "symbol"]])
    if not pd.MultiIndex.from_frame(issues).isin(keys).all():
        raise ValueError("Issue asset/date is absent from the source")
    exposed = pd.Series(False, index=wide.index)
    for symbol in design["symbols"]:
        grid = pd.DatetimeIndex(source.loc[source.symbol.eq(symbol), "date"]).sort_values()
        if not grid.is_unique:
            raise ValueError("Duplicate source dates")
        dates = issues.loc[issues.symbol.eq(symbol), "date"]
        flag = pd.Series(grid.isin(dates), index=grid)
        source_window = flag.rolling(window, min_periods=1).max().reindex(wide.index)
        retained_flag = flag.reindex(wide.index).fillna(False).astype(bool)
        retained_window = retained_flag.rolling(window, min_periods=1).max()
        exposed |= source_window.fillna(0).astype(bool) | retained_window.astype(bool)
        if symbol == "ES":
            return_flag = (flag | flag.shift(1, fill_value=False)).reindex(wide.index).fillna(False)
            exposed |= return_flag.rolling(window, min_periods=1).max().astype(bool)
    target_exposed = design["target_dates"].isin(issues.date)
    return (exposed.reindex(design["x"].index) | target_exposed).astype(bool)


def sensitivity_panel(raw, core, scenario, start="2011-01-01"):
    """Change a scenario's inputs, retaining the core grid and unmodified raw file."""
    if scenario == "rk_proxy":
        proxy = raw.copy()
        # Normalized internal feature names are retained; output metadata marks
        # that both predictors AND outcomes represent RK in this scenario.
        proxy["rv5"] = proxy["rk"]
        panel, _ = prepare_har_data(proxy, start)
    else:
        panel = core.copy()
    if scenario == "open_to_close_returns":
        es = raw.loc[raw.symbol.eq("ES")].copy()
        es["date"] = pd.to_datetime(es.date)
        values = pd.Series(100*np.log(es.close_price.to_numpy()/es.open_price.to_numpy()),
            index=pd.DatetimeIndex(es.date))
        if not np.isfinite(values).all():
            raise ValueError("Invalid open-to-close sensitivity input")
        panel["ret_ES"] = values.reindex(panel.index)
    if not panel.index.equals(core.index):
        raise ValueError("Data sensitivity changed the frozen date grid")
    return panel


def gain_table(frame, pairs):
    """Paired within-scenario gains; proxies/samples are never pooled."""
    rows = []
    for candidate, benchmark in pairs:
        a = frame.loc[frame.model.eq(candidate)].set_index("date").sort_index()
        b = frame.loc[frame.model.eq(benchmark)].set_index("date").sort_index()
        if not a.index.equals(b.index) or not a.origin_date.equals(b.origin_date):
            raise ValueError("Unpaired comparison dates")
        np.testing.assert_allclose(a.actual_log, b.actual_log, atol=1e-12, rtol=0)
        candidate_loss = np.mean((a.actual_log-a.predicted_log)**2)
        benchmark_loss = np.mean((b.actual_log-b.predicted_log)**2)
        rows.append(dict(Candidate=candidate, Benchmark=benchmark, N=len(a),
            MSE_gain_pct=100*(1-candidate_loss/benchmark_loss)))
    return pd.DataFrame(rows)


def run_robustness(raw, wide, design, main_forecasts, ledger, source_sha256, settings, training_end):
    """Run the frozen plan, returning CSV-ready tables and complete forecasts."""
    specs5 = model_specifications(settings["main_lag"])
    specs = {name: specs5[name] for name in settings["models"]}
    baseline = main_forecasts.loc[main_forecasts.model.isin(specs)].copy()
    expected = pd.DatetimeIndex(design["target_dates"][design["target_dates"] > pd.Timestamp(training_end)])
    if set(baseline.model) != set(specs):
        raise ValueError("Missing planned baseline model")
    flags = flag_evidence(raw, ledger, source_sha256)
    broad_issues = flags.loc[flags.decision.ne(settings["crisis_decision_to_retain"]), ["date", "symbol"]]
    reviewed_mask = exposure_mask(raw, wide, design, settings["reviewed_issues"], settings["exposure_window"])
    broad_mask = exposure_mask(raw, wide, design, broad_issues, settings["exposure_window"])
    scenarios, scores, gains, flow, exclusions = [], [], [], [], []
    for scenario in settings["scenarios"]:
        panel = sensitivity_panel(raw, wide, scenario)
        scenario_design = aligned_design(panel)
        if not scenario_design["target_dates"].equals(design["target_dates"]):
            raise ValueError("Sensitivity changed origin/target mapping")
        omit = reviewed_mask if scenario == "reviewed_training_windows" else broad_mask if scenario == "broad_flag_training_windows" else pd.Series(False, index=design["x"].index)
        frame = baseline.copy() if scenario == "baseline_rv5" else expanding_forecasts(
            scenario_design, specs, training_end, training_eligible=~omit)
        for _, model in frame.groupby("model", sort=False):
            if not pd.DatetimeIndex(model.date).equals(expected):
                raise ValueError("Sensitivity changed evaluation dates")
            if not (model.training_end <= model.origin_date).all():
                raise ValueError("Sensitivity used future training outcomes")
        metrics = forecast_metrics(frame).reset_index().assign(Scenario=scenario)
        scores.append(metrics)
        gains.append(gain_table(frame, settings["pairs"]).assign(Scenario=scenario))
        first = frame.loc[frame.model.eq(settings["models"][0])].iloc[0]
        flow.append(dict(Scenario=scenario, Proxy="RK" if scenario == "rk_proxy" else "RV5",
            Return_definition="open-to-close" if scenario == "open_to_close_returns" else "close-to-close",
            N=len(expected), Initial_training=int(first.n_train),
            Initially_omitted=int((omit & (design["target_dates"] <= pd.Timestamp(training_end))).sum()),
            Total_eligible_training_rows=int((~omit).sum())))
        if omit.any():
            exclusions.append(pd.DataFrame({"origin_date": design["x"].index[omit],
                "target_date": design["target_dates"][omit].to_numpy(), "Scenario": scenario}))
        scenarios.append(frame.assign(scenario=scenario, lag=settings["main_lag"]))
    # Lag sensitivity keeps original RV5 inputs and all evaluation observations.
    lag_scores = []
    for lag in settings["lags"]:
        candidates = model_specifications(lag)
        selected = {name: candidates[name] for name in settings["models"] if candidates[name]["family"] == "VAR"}
        frame = baseline.loc[baseline.model.isin(selected)].copy() if lag == settings["main_lag"] else expanding_forecasts(design, selected, training_end)
        table = forecast_metrics(frame).reset_index().assign(Lag=lag)
        table["ES_parameters"] = [len(columns_for(selected[name]))+1 for name in table.Model]
        table["System_parameters"] = [(len(columns_for(selected[name]))+1)*(1+len(selected[name]["commodities"])) for name in table.Model]
        lag_scores.append(table)
        if lag != settings["main_lag"]:
            scenarios.append(frame.assign(scenario="lag_sensitivity", lag=lag))
    # Retrospective quality subset: every model loses the same dates, no refitting.
    exposed = broad_mask.reindex(pd.DatetimeIndex(baseline.origin_date)).to_numpy()
    subset = baseline.loc[~exposed].copy()
    subset_metrics = forecast_metrics(subset).reset_index()
    subset_gains = gain_table(subset, settings["pairs"])
    evaluation_mask = pd.DataFrame({"origin_date": design["x"].index,
        "target_date": design["target_dates"].to_numpy(), "broad_exposure": broad_mask.to_numpy()})
    evaluation_mask = evaluation_mask.loc[evaluation_mask.target_date > pd.Timestamp(training_end)]
    intervals = []
    for candidate, benchmark in settings["pairs"]:
        a = baseline.loc[baseline.model.eq(candidate)].set_index("date")
        b = baseline.loc[baseline.model.eq(benchmark)].set_index("date").loc[a.index]
        for block in settings["bootstrap"]["blocks"]:
            intervals.append(dict(Candidate=candidate, Benchmark=benchmark,
                **paired_block_intervals(a.actual_log.to_numpy(), b.predicted_log.to_numpy(),
                    a.predicted_log.to_numpy(), block=block, draws=settings["bootstrap"]["draws"],
                    seed=settings["bootstrap"]["seed"])))
    return dict(flags=flags, forecasts=pd.concat(scenarios, ignore_index=True),
        metrics=pd.concat(scores, ignore_index=True), gains=pd.concat(gains, ignore_index=True),
        sample_flow=pd.DataFrame(flow), exclusions=pd.concat(exclusions, ignore_index=True),
        lag_metrics=pd.concat(lag_scores, ignore_index=True), subset_metrics=subset_metrics,
        subset_gains=subset_gains, evaluation_exposure=evaluation_mask,
        intervals=pd.DataFrame(intervals))


def plot_lag_comparison(metrics):
    import matplotlib.pyplot as plt
    names = ["VAR + Downside (Baseline)", "VAR + Downside (Oil + Gold)",
        "VAR + Downside (All 4: Oil + Corn + Gold + NG)", "VAR + Downside (NatGas)"]
    table = metrics.pivot(index="Model", columns="Lag", values="MSE").loc[names]
    table.index = ["Equity only", "Oil + gold (main)", "All four commodities", "Gas only"]
    fig, ax = plt.subplots(figsize=(10, 5))
    table.plot.barh(ax=ax, color=["#235789", "#e2a03a"])
    ax.set(xlabel="Log-variance forecast MSE (lower is better)",
        title="Lag sensitivity: identical 802 targets and downside information", ylabel="")
    ax.legend(title="Lag order")
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    return fig
