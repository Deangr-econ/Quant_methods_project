"""Supported sensitivities on the final wide dataset, without old review masks."""
import numpy as np
import pandas as pd

from har_return_audit import paired_block_intervals
from var_har_notebook import model_specifications, expanding_forecasts, forecast_metrics, columns_for


def run_final_robustness(design, forecasts, settings, training_end, main_lag):
    lag_frames, lag_scores = [], []
    for lag in sorted(set([main_lag, *settings["lags"]])):
        specs = model_specifications(lag)
        specs = {name: specs[name] for name in settings["models"] if specs[name]["family"] == "VAR"}
        frame = forecasts.loc[forecasts.model.isin(specs)].copy() if lag == main_lag else expanding_forecasts(design, specs, training_end)
        table = forecast_metrics(frame).reset_index().assign(Lag=lag)
        table["ES_parameters"] = [len(columns_for(specs[name])) + 1 for name in table.Model]
        table["System_parameters"] = [(len(columns_for(specs[name])) + 1) * (1 + len(specs[name]["commodities"])) for name in table.Model]
        lag_scores.append(table)
        lag_frames.append(frame.assign(lag=lag))
    intervals = []
    for candidate, benchmark in settings["pairs"]:
        a = forecasts.loc[forecasts.model.eq(candidate)].set_index("date")
        b = forecasts.loc[forecasts.model.eq(benchmark)].set_index("date").loc[a.index]
        if not a.origin_date.equals(b.origin_date):
            raise ValueError("Unpaired forecast origins")
        np.testing.assert_allclose(a.actual_log, b.actual_log, atol=1e-12)
        for block in settings["bootstrap"]["blocks"]:
            intervals.append(dict(Candidate=candidate, Benchmark=benchmark,
                **paired_block_intervals(a.actual_log.to_numpy(), b.predicted_log.to_numpy(),
                    a.predicted_log.to_numpy(), block=block, draws=settings["bootstrap"]["draws"],
                    seed=settings["bootstrap"]["seed"])))
    return dict(lag_metrics=pd.concat(lag_scores, ignore_index=True),
                lag_forecasts=pd.concat(lag_frames, ignore_index=True), intervals=pd.DataFrame(intervals))


def plot_lag_comparison(metrics):
    import matplotlib.pyplot as plt
    names = ["LVAR (Baseline)", "LVAR (Oil + Gold)", "LVAR (All 4: Oil + Corn + Gold + NG)", "LVAR (NatGas)"]
    table = metrics.pivot(index="Model", columns="Lag", values="MSE").loc[names]
    table.index = ["Equity only", "Oil + gold", "All four commodities", "Gas only"]
    fig, ax = plt.subplots(figsize=(10, 5))
    table.plot.barh(ax=ax, color=["#235789", "#e2a03a"])
    ax.set(xlabel="Log-variance forecast MSE (lower is better)",
           title=f'Lag sensitivity: identical {int(metrics.N.iloc[0])} final-dataset targets', ylabel="")
    ax.legend(title="Lag order")
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    return fig
