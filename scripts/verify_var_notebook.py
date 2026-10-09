"""Verify the saved HAR-aligned notebook and every forecast against source values."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "reports/var_har_notebook/generated"
notebook = json.loads((ROOT / "VAR_QTFE.ipynb").read_text())
code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
assert notebook["nbformat"] == 4
assert [c["execution_count"] for c in code] == list(range(1, len(code) + 1))
assert all(o["output_type"] != "error" for c in code for o in c["outputs"])
assert notebook["metadata"]["validated_execution"]["errors"] == 0
assert sum("image/png" in o.get("data", {}) for c in code for o in c["outputs"]) == 5
manifest = json.loads((out / "provenance.json").read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(ROOT / manifest["config"]["source"]) == manifest["source_sha256"]
assert sha(ROOT / manifest["config"]["har_reference"]) == manifest["har_notebook_sha256"]
assert sha(ROOT / "var_har_notebook.py") == manifest["module_sha256"]
assert sha(ROOT / "var_irf.py") == manifest["irf_module_sha256"]
assert sha(ROOT / manifest["config"]["yield_snapshot"]) == manifest["yield_snapshot_sha256"]
assert sha(ROOT / manifest["config"]["yield_manifest"]) == manifest["yield_manifest_sha256"]
yield_source = json.loads((ROOT / manifest["config"]["yield_manifest"]).read_text())
assert yield_source['sha256'] == manifest['yield_snapshot_sha256']
assert manifest['irf']['n'] == manifest['initial_fit_targets']
assert manifest['irf']['last_target'] == manifest['config']['training_end']
irfs = pd.read_csv(out / 'training_generalized_irfs.csv')
assert len(irfs) == 5 * (manifest['irf']['horizon'] + 1)
assert not irfs.duplicated(['impulse', 'response', 'horizon']).any()
assert (irfs.log_lower <= irfs.log_upper).all()
np.testing.assert_allclose(irfs.variance_pct, 100 * np.expm1(irfs.log_response), atol=1e-12)
np.testing.assert_allclose(irfs.volatility_pct, 100 * np.expm1(irfs.log_response/2), atol=1e-12)
for name, value in manifest["output_sha256"].items():
    assert sha(out / name) == value
raw = pd.read_csv(ROOT / manifest["config"]["source"], float_precision="round_trip")
es = raw.loc[raw.symbol.eq("ES")].set_index("date").rv5
forecasts = pd.read_csv(out / "shared_forecasts.csv", float_precision="round_trip")
metrics = pd.read_csv(out / "shared_forecast_metrics.csv", index_col=0, float_precision="round_trip")
summary = pd.read_csv(out / "common_sample_insample_results.csv", index_col=0)
har_audit = pd.read_csv(out / "latest_har_forecast_audit.csv", index_col=0)
calendar_audit = pd.read_csv(out / "har_calendar_audit.csv", index_col=0)
assert len(har_audit) == 6
assert har_audit.N.eq(manifest['evaluation_targets']).all()
assert har_audit.Initial_training.eq(manifest['initial_fit_targets']).all()
assert (har_audit.Max_prediction_difference < 1e-9).all()
assert manifest['har_reference_forecasts_checked'] == int(har_audit.N.sum())
np.testing.assert_allclose(har_audit.Native_MSE, metrics.loc[har_audit.index, 'MSE'], atol=1e-11, rtol=0)
assert calendar_audit.loc['Latest HAR with yield join (separate)', 'Panel rows'] == manifest['yield_join_panel_rows']
assert calendar_audit.loc['Commodity core (shared comparison)', 'Panel rows'] - manifest['yield_join_panel_rows'] == manifest['yield_join_removed_core_rows']
assert summary.N.nunique() == 1 and summary.N.iloc[0] == 3967
assert not forecasts.duplicated(["model", "date"]).any()
expected_dates = None
for name, frame in forecasts.groupby("model", sort=False):
    if expected_dates is None:
        expected_dates = frame.date.reset_index(drop=True)
    assert frame.date.reset_index(drop=True).equals(expected_dates)
    assert len(frame) == 802
    assert (frame.training_end == frame.origin_date).all()
    assert (frame.origin_date < frame.date).all()
    np.testing.assert_allclose(frame.actual_variance, es.reindex(frame.date), rtol=1e-12)
    np.testing.assert_allclose(frame.predicted_variance, np.exp(frame.predicted_log) * frame.smearing, rtol=1e-12)
    if name == "Persistence":
        np.testing.assert_allclose(frame.predicted_variance, es.reindex(frame.origin_date), rtol=1e-12)
    elif name.startswith("VAR") or name.startswith("Restricted VAR"):
        assert (frame.loc[frame.status.eq("ok"), "root"] < 1).all()
    error = frame.actual_log - frame.predicted_log
    ratio = frame.actual_variance / frame.predicted_variance
    expected = [np.mean(error**2), np.sqrt(np.mean(error**2)), np.mean(np.abs(error)),
                np.mean((frame.actual_variance - frame.predicted_variance)**2),
                np.mean(ratio - np.log(ratio) - 1)]
    np.testing.assert_allclose(metrics.loc[name, ["MSE", "RMSE", "MAE", "Variance_MSE", "QLIKE"]], expected, rtol=1e-12)
    assert metrics.loc[name, "Fallbacks"] == frame.status.ne("ok").sum()
from verify_var_robustness import verify
verify()
print(f"Verified {len(code)} executed cells, 5 figures, training-only IRF metadata, source/code/output hashes and all {len(forecasts):,} dated forecast records across {len(metrics)} models; {manifest['har_reference_forecasts_checked']:,} latest-HAR forecasts independently matched and the separate yield calendar audited.")
