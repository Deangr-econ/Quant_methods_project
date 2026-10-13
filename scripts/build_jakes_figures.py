"""Build report figures from Jake's verified final-data outputs; fit no models."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/final_dataset/var/generated"
OUT = ROOT / "latex_report/jakes_figures"
OUT.mkdir(parents=True, exist_ok=True)
manifest = json.loads((SOURCE / "provenance.json").read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(ROOT / manifest["config"]["source"]) == manifest["source_sha256"]
for name in ["shared_forecast_metrics.csv", "robustness_intervals.csv",
             "initial_lag_selection.csv", "training_generalized_irfs.csv"]:
    assert sha(SOURCE / name) == manifest["output_sha256"][name], name

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "axes.titleweight": "normal"})

def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

metrics = pd.read_csv(SOURCE / "shared_forecast_metrics.csv").set_index("Model")
names = ["VAR (Baseline)", "LVAR (Baseline)", "LVAR (Oil + Gold)", "LVAR (NatGas)",
         "LVAR (No Corn: Oil + NG + Gold)",
         "Restricted LVAR (No Corn: Oil + NG + Gold; Daily Only)",
         "LVAR (All 4: Oil + Corn + Gold + NG)",
         "Restricted LVAR (All 4: Oil + Corn + Gold + NG; Daily Only)",
         "LHAR (Baseline)"]
labels = ["Equity-only VAR(5)", "Equity-only LVAR(5)", "LVAR: oil + gold",
          "LVAR: natural gas", "LVAR: no corn", "Restricted LVAR: no corn",
          "LVAR: all four commodities", "Restricted LVAR: all four", "Matched equity-only LHAR"]
fig, ax = plt.subplots(figsize=(8.4, 4.6))
y = np.arange(len(names))
values = metrics.loc[names, "MSE"].to_numpy()
ax.barh(y, values, color=["#909da9", "#235789", "#235789", "#235789", "#235789",
                         "#c78629", "#235789", "#c78629", "#429b96"], height=.62)
ax.set_yticks(y, labels)
ax.invert_yaxis()
ax.set_xlim(0, .414)
for pos, value in zip(y, values):
    ax.text(value + .004, pos, f"{value:.5f}", va="center", fontsize=8)
ax.set_xlabel("Forecast MSE of ES log RV5 (lower is better)")
ax.set_title("Identical 783 targets: 13 July 2023 to 31 August 2026", pad=12)
ax.grid(axis="x", alpha=.2)
ax.set_axisbelow(True)
fig.tight_layout()
save(fig, "forecast_accuracy")

intervals = pd.read_csv(SOURCE / "robustness_intervals.csv")
table = intervals.loc[intervals.block.eq(20)].set_index(["Candidate", "Benchmark"])
pairs = [("LVAR (Baseline)", "VAR (Baseline)"),
         ("LVAR (Oil + Gold)", "LVAR (Baseline)"),
         ("LVAR (All 4: Oil + Corn + Gold + NG)", "LVAR (Baseline)"),
         ("LVAR (NatGas)", "LVAR (Baseline)"),
         ("LHAR (Baseline)", "LVAR (Baseline)")]
labels = ["Downside controls: LVAR vs plain VAR", "Oil + gold vs equity-only LVAR",
          "All four vs equity-only LVAR", "Natural gas vs equity-only LVAR",
          "Matched LHAR vs equity-only LVAR"]
fig, ax = plt.subplots(figsize=(8.4, 3.7))
for pos, pair in enumerate(pairs):
    row = table.loc[pair]
    ax.errorbar(row.gain_pct, pos,
                xerr=[[row.gain_pct-row.lower_pct], [row.upper_pct-row.gain_pct]],
                fmt="o", capsize=4, color="#235789" if pos in [0,4] else "#c78629")
ax.set_yticks(range(len(pairs)), labels)
ax.invert_yaxis()
ax.axvline(0, ls="--", color="black", lw=.8)
ax.set_xlabel("Reduction in MSE relative to the named benchmark (%)")
ax.set_title("Descriptive paired-loss intervals: 2,000 circular-block draws, block length 20", pad=12, fontsize=9)
ax.grid(axis="x", alpha=.2)
fig.tight_layout()
save(fig, "incremental_gains")

lag = pd.read_csv(SOURCE / "initial_lag_selection.csv")
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharex=True)
for ax, criterion, color in zip(axes, ["BIC", "AIC"], ["#235789", "#c78629"]):
    selected = int(lag.loc[lag[criterion].idxmin(), "p"])
    ax.plot(lag.p, lag[criterion], marker="o", markersize=3, lw=1.2, color=color)
    ax.axvline(selected, ls="--", color=color, alpha=.8)
    ax.set(title=f"{criterion}: selected lag {selected}", xlabel="VAR lag order", ylabel=criterion)
    ax.set_xticks([1,5,10,15,20]); ax.grid(alpha=.2)
fig.suptitle("Five-market plain VAR; same 3,084 initial-training outcomes", fontsize=10)
fig.tight_layout()
save(fig, "lag_selection")

irf = pd.read_csv(SOURCE / "training_generalized_irfs.csv")
fig, axes = plt.subplots(2, 2, figsize=(8.4, 5.0), sharex=True)
for ax, symbol, title in zip(axes.flat, ["CL", "C", "GC", "NG"], ["Oil", "Corn", "Gold", "Natural gas"]):
    frame = irf.loc[irf.impulse.eq(symbol)].sort_values("horizon")
    ax.fill_between(frame.horizon, frame.variance_lower, frame.variance_upper, color="#235789", alpha=.18)
    ax.plot(frame.horizon, frame.variance_pct, color="#235789", lw=1.5)
    ax.axhline(0, color="black", ls="--", lw=.7)
    ax.set_title(f"{title} innovation")
    ax.set_ylabel("ES variance response (%)")
    ax.grid(alpha=.18)
for ax in axes[1]:
    ax.set_xlabel("Retained observations after innovation")
fig.suptitle("Initial-training all-four LVAR(5): conditional generalized responses", fontsize=10)
fig.tight_layout()
save(fig, "conditional_irfs")

(OUT / "provenance.json").write_text(json.dumps({
    "input_source_sha256": manifest["source_sha256"],
    "result_run_time": manifest["run_time"],
    "builder_sha256": sha(__file__),
    "inputs": {name: sha(SOURCE / name) for name in ["shared_forecast_metrics.csv",
        "robustness_intervals.csv", "initial_lag_selection.csv", "training_generalized_irfs.csv"]},
    "outputs": {p.name: sha(p) for p in sorted(OUT.glob("*.pdf"))},
}, indent=2) + "\n")
print("Built four PDF/PNG figure pairs from verified final-data outputs:", OUT)
