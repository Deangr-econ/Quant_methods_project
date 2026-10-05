"""Independent NumPy/SVD audit of saved R VAR forecasts on real source data.

Run with .venv/bin/python scripts/audit_var.py [generated-output-directory].
This audit never imports the R estimation module or changes source/results.
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports/var_final/generated"
cfg = json.loads((ROOT / "config/var_analysis.json").read_text())
raw = pd.read_csv(ROOT / "datasets/realized_variance_futures.csv", parse_dates=["date"], float_precision="round_trip")
panel = pd.read_csv(OUT / "main_variance_panel.csv", parse_dates=["date"], float_precision="round_trip")
specs = pd.read_csv(OUT / "model_specs.csv", keep_default_na=False)
grid = pd.DatetimeIndex(panel.date)
rv = raw.pivot(index="date", columns="symbol", values=cfg["primary_measure"])
expected_grid = rv.loc[cfg["sample_start"]:cfg["test_end"], cfg["main_symbols"]].dropna().index
assert grid.equals(expected_grid), "Main grid differs from raw selected-measure availability"
np.testing.assert_allclose(panel[cfg["main_symbols"]], rv.loc[grid, cfg["main_symbols"]], rtol=1e-13, atol=0)
targets = grid[grid > pd.Timestamp(cfg["training_end"])]
checks = []
for scenario in specs.scenario.unique():
    measure = cfg["robustness_measure"] if scenario == "rk" else cfg["primary_measure"]
    symbols = cfg["extension_symbols"] if scenario == "corn_gas" else cfg["main_symbols"]
    source_panel = raw.pivot(index="date", columns="symbol", values=measure).reindex(grid)[symbols]
    logs = np.log(source_panel.to_numpy())
    saved = pd.read_csv(OUT / f"{scenario}_forecasts.csv", parse_dates=["date", "origin_date"], float_precision="round_trip")
    for spec in specs.loc[specs.scenario == scenario].itertuples():
        rows = saved.loc[saved.model == spec.model].reset_index(drop=True)
        assert pd.DatetimeIndex(rows.date).equals(targets)
        np.testing.assert_allclose(rows.actual_variance, source_panel.loc[targets, "ES"], rtol=1e-13, atol=0)
        chosen = {0, len(rows) // 2, len(rows) - 1}
        failures = np.flatnonzero(rows.status.to_numpy() != "ok")
        if len(failures):
            chosen.add(int(failures[0]))
        for position in sorted(chosen):
            record = rows.iloc[position]
            i = grid.get_loc(record.date)
            history = logs[:i]
            assert record.origin_date == grid[i - 1] and record.history_rows == i
            if spec.kind == "Naive":
                np.testing.assert_allclose(record.predicted_log, history[-1, 0], atol=1e-12, rtol=0)
                np.testing.assert_allclose(record.predicted_variance, np.exp(history[-1, 0]), rtol=1e-12)
                checks.append((scenario, spec.model, str(record.date.date()), 0.0))
                continue
            differenced = bool(spec.difference)
            values = np.diff(history, axis=0) if differenced else history
            value_dates = grid[1:i] if differenced else grid[:i]
            p = int(spec.p)
            target_rows = np.arange(p, len(values))
            full_x = np.column_stack([np.ones(len(target_rows))] + [values[target_rows - lag] for lag in range(1, p + 1)])
            full_y = values[target_rows]
            selected_names = ["ES"] if spec.kind == "AR" else symbols
            if spec.subset_symbols:
                selected_names = spec.subset_symbols.split("/")
            selected = values[:, [symbols.index(s) for s in selected_names]]
            x = np.column_stack([np.ones(len(target_rows))] + [selected[target_rows - lag] for lag in range(1, p + 1)])
            y = selected[target_rows]
            keep = np.isfinite(full_x).all(axis=1) & np.isfinite(full_y).all(axis=1)
            if spec.model == "AR_selected":
                keep = np.isfinite(x).all(axis=1) & np.isfinite(y).all(axis=1)
            if scenario == "suspect_training":
                for suspect in pd.to_datetime(cfg["suspect_dates"]):
                    if suspect in grid[:i]:
                        start = grid.get_loc(suspect)
                        exposed = grid[start:start + cfg["max_lag"] + 2]
                        keep &= ~value_dates[target_rows].isin(exposed)
            # SVD least squares is independent of the R QR implementation.
            coefficients, _, rank, _ = np.linalg.lstsq(x[keep], y[keep], rcond=None)
            assert rank == x.shape[1]
            assert record.fitted_rows == int(keep.sum())
            assert record.omitted_rows == int((~keep).sum())
            assert record.parameters == coefficients.size
            k = selected.shape[1]
            if p:
                top = coefficients[1:].T
                companion = top if p == 1 else np.vstack([top, np.column_stack([np.eye(k * (p - 1)), np.zeros((k * (p - 1), k))])])
                root = float(np.abs(np.linalg.eigvals(companion)).max())
            else:
                root = 0.0
            np.testing.assert_allclose(record.root, root, atol=1e-8, rtol=0)
            xnext = np.concatenate([np.ones(1), selected[-p:][::-1].ravel()]) if p else np.ones(1)
            available = np.isfinite(xnext).all() and root < 1
            if not available:
                assert record.status == "fallback_persistence"
                predicted = history[-1, 0]
                variance = np.exp(predicted)
                smear = 1.0
            else:
                assert record.status == "ok"
                predicted = float(xnext @ coefficients[:, 0]) + (history[-1, 0] if differenced else 0)
                residuals = y[keep, 0] - x[keep] @ coefficients[:, 0]
                smear = float(np.exp(residuals).mean())
                variance = np.exp(predicted) * smear
            difference = abs(predicted - record.predicted_log)
            np.testing.assert_allclose(record.predicted_log, predicted, atol=1e-9, rtol=0)
            np.testing.assert_allclose(record.smearing, smear, rtol=1e-10)
            np.testing.assert_allclose(record.predicted_variance, variance, rtol=1e-9)
            checks.append((scenario, spec.model, str(record.date.date()), difference))

print(json.dumps({"checked_forecasts": len(checks), "scenarios": list(specs.scenario.unique()),
                  "max_absolute_log_forecast_difference": max(x[3] for x in checks),
                  "raw_main_panel_matches": True,
                  "checks": "Real-data first/middle/last and first fallback: independent SVD forecasts, roots, masks, size, smearing, targets and source values"}, indent=2))
