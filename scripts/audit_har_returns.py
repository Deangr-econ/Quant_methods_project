"""Run the fixed return-control and sensitivity plan in reports/har_followup/."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from har_forecasts import build_design, expanding_forecasts, accuracy_table
from har_return_audit import equity_return_audit, add_return_controls, paired_block_intervals, exposed_design_rows
from volare_data import validate_source

PAIRS = [("AR15_returns", "AR15"), ("HAR", "AR15"), ("LHAR", "HAR"),
         ("LHAR", "AR15_returns"), ("LHARX", "LHAR")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / "reports/har_followup"
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT / "datasets/realized_variance_futures.csv"
    raw = validate_source(pd.read_csv(source))
    es = raw.loc[raw.symbol.eq("ES")].set_index("date")
    returns, schedule = equity_return_audit(es)
    returns.to_csv(out / "es_return_audit.csv", index_label="date")
    schedule.to_csv(out / "candidate_roll_schedule.csv", index=False)
    returns.loc[returns.opening_gap.abs().nlargest(20).index].sort_index().to_csv(out / "largest_opening_gaps.csv")
    panels = {m: raw.pivot(index="date", columns="symbol", values=m)[["ES", "CL", "GC"]]
              .loc["2011-01-01":].dropna() for m in ["rv5", "rk"]}
    if not panels["rv5"].index.equals(panels["rk"].index):
        raise ValueError("RK/RV5 sensitivity requires identical dates")
    variance = panels["rv5"]
    targets = variance.index[int(.8 * len(variance)):]
    if len(targets) != 809 or targets[0] != pd.Timestamp("2023-07-13"):
        raise ValueError("Source no longer matches the frozen comparison period")
    configs = [("rv5_close", "rv5", "close_to_close", False),
               ("rv5_open_close", "rv5", "open_to_close", False),
               ("rv5_roll_neighbourhood", "rv5", "neighbourhood_open_close", False),
               ("rk_close", "rk", "close_to_close", False),
               ("rv5_suspect_training", "rv5", "close_to_close", True)]
    scores, yearly, counts, comparisons, influences = [], [], [], [], []
    baseline = None
    for name, measure, return_column, omit_suspects in configs:
        design, groups = build_design(panels[measure], returns[return_column])
        groups = add_return_controls(groups)
        excluded_count = 0
        if omit_suspects:
            # Conservative design-row mask, not a new compressed price/variance series.
            exposed = exposed_design_rows(design, variance.index,
                ["2018-03-26", "2020-04-16", "2021-03-29", "2021-03-30"], ["2021-03-29"])
            excluded = design.loc[exposed, ["target_date"]].copy()
            excluded.index.name = "origin_date"
            excluded.to_csv(out / "suspect_training_rows.csv")
            if not excluded.target_date.lt(targets[0]).all():
                raise ValueError("This sensitivity is restricted to pre-test suspect dates")
            excluded_count = len(excluded)
            design = design.loc[~exposed]
        forecasts = expanding_forecasts(design, groups, targets)
        if baseline is None:
            baseline = forecasts
            prior_path = ROOT / "reports/har_verification/common_809_forecasts.csv"
            if prior_path.exists():
                prior = pd.read_csv(prior_path, parse_dates=["date"])
                if not prior.date.equals(forecasts.date):
                    raise ValueError("Earlier HAR audit has different dates")
                np.testing.assert_allclose(prior[["actual", "AR15", "HAR", "LHAR", "LHARX"]],
                                           forecasts[["actual", "AR15", "HAR", "LHAR", "LHARX"]], atol=1e-10, rtol=0)
        if not forecasts.date.equals(baseline.date) or not forecasts.origin_date.equals(baseline.origin_date):
            raise ValueError("Sensitivity comparison changed forecast origins/targets")
        forecasts.to_csv(out / f"forecasts_{name}.csv", index=False)
        metrics = accuracy_table(forecasts, [*groups, "Naive"]).assign(scenario=name)
        scores.append(metrics)
        counts.append(dict(scenario=name, variance_measure=measure, return_definition=return_column,
                           observations=len(forecasts), initial_fitted_targets=int(forecasts.n_train.iloc[0]),
                           omitted_training_rows=excluded_count))
        for year, chunk in forecasts.groupby(forecasts.date.dt.year):
            yearly.append(accuracy_table(chunk, [*groups, "Naive"]).assign(scenario=name, year=year))
        for candidate, benchmark in PAIRS:
            base_loss = (forecasts.actual - forecasts[benchmark]) ** 2
            new_loss = (forecasts.actual - forecasts[candidate]) ** 2
            contribution = base_loss - new_loss
            influential = contribution.abs().nlargest(5).index
            keep = ~forecasts.index.isin(influential)
            comparisons.append(dict(scenario=name, candidate=candidate, benchmark=benchmark,
                                    gain_pct=100 * (1 - new_loss.mean() / base_loss.mean()),
                                    gain_without_top5_abs_contributions=100 * (1 - new_loss.loc[keep].mean() / base_loss.loc[keep].mean())))
            if name == "rv5_close":
                for i in influential:
                    influences.append(dict(candidate=candidate, benchmark=benchmark,
                                           date=forecasts.date.iloc[i], origin_date=forecasts.origin_date.iloc[i],
                                           base_squared_error=base_loss.iloc[i], candidate_squared_error=new_loss.iloc[i],
                                           loss_advantage=contribution.iloc[i]))
        print(f"Completed {name}: {len(forecasts)} targets, {excluded_count} training rows omitted", flush=True)
    pd.concat(scores).to_csv(out / "metrics.csv", index=False)
    pd.concat(yearly).to_csv(out / "yearly_metrics.csv", index=False)
    pd.DataFrame(counts).to_csv(out / "sample_flow.csv", index=False)
    pd.DataFrame(comparisons).to_csv(out / "paired_gains.csv", index=False)
    pd.DataFrame(influences).to_csv(out / "influential_dates.csv", index=False)
    intervals = []
    losses = pd.DataFrame({"date": baseline.date})
    for candidate, benchmark in PAIRS:
        losses[f"{benchmark}_minus_{candidate}"] = ((baseline.actual - baseline[benchmark]) ** 2
                                                    - (baseline.actual - baseline[candidate]) ** 2)
        for block in (5, 20, 60):
            result = paired_block_intervals(baseline.actual, baseline[benchmark], baseline[candidate], block=block)
            intervals.append(dict(candidate=candidate, benchmark=benchmark, **result))
    losses.to_csv(out / "paired_losses.csv", index=False)
    pd.DataFrame(intervals).to_csv(out / "descriptive_intervals.csv", index=False)
    files = [source, ROOT / "har_forecasts.py", ROOT / "har_return_audit.py", Path(__file__),
             out / "ANALYSIS_PLAN.md"]
    metadata = dict(input_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
                    output_sha256={p.name: sha(p) for p in out.glob("*.csv")},
                    source_urls=["https://www.kibot.com/futures/rollover-rules.html",
                                 "https://www.kibot.com/futures/futures-expirations.html",
                                 "https://arch.readthedocs.io/en/latest/bootstrap/timeseries-bootstraps.html"],
                    sources_accessed="2026-10-04", roll_schedule_verified=False,
                    sensitivity_is_correction=False, interval_interpretation="exploratory, conditional on fixed forecasts; not adjusted for model selection",
                    seed=20261004, bootstrap_draws=2000, bootstrap_blocks=[5, 20, 60])
    (out / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(pd.DataFrame(comparisons).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
