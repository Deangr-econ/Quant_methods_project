"""Verify the executed VAR notebook and independent HAR function comparisons.

The Colab HAR notebook is a read-only function reference. Its native
80/20 outputs are not assumed to be an executed local common-date HAR run.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_notebook(filename):
    notebook = json.loads((ROOT / filename).read_text())
    code = [cell for cell in notebook['cells'] if cell['cell_type'] == 'code' and ''.join(cell['source']).strip()]
    assert [cell['execution_count'] for cell in code] == list(range(1, len(code) + 1))
    assert all(output['output_type'] != 'error' for cell in code for output in cell['outputs'])
    assert notebook['metadata']['validated_execution']['errors'] == 0
    return notebook, code


def expected_grid(raw, cfg):
    dates = pd.DatetimeIndex(pd.to_datetime(raw.date))
    first_target = 21 + cfg['common_warmup']
    origins, targets = dates[first_target - 1:-1], dates[first_target:]
    keep = targets > pd.Timestamp(cfg['training_end'])
    return targets, origins[keep], targets[keep]


def scores(frame):
    error = frame.actual_log - frame.predicted_log
    ratio = frame.actual_variance / frame.predicted_variance
    return np.array([np.mean(error**2), np.sqrt(np.mean(error**2)), np.mean(np.abs(error)),
                     np.mean((frame.actual_variance - frame.predicted_variance)**2),
                     np.mean(ratio - np.log(ratio) - 1)])


def verify_lag_run(out, manifest, raw):
    cfg = manifest['config']
    all_targets, origins, targets = expected_grid(raw, cfg)
    forecasts = pd.read_csv(out / 'robustness_lag_forecasts.csv', float_precision='round_trip',
                            parse_dates=['date', 'origin_date', 'training_end'])
    metrics = pd.read_csv(out / 'robustness_lag_metrics.csv', float_precision='round_trip').set_index(['Model', 'Lag'])
    main = pd.read_csv(out / 'shared_forecasts.csv', float_precision='round_trip', parse_dates=['date']).set_index(['model', 'date'])
    es = pd.Series(raw.rv5_ES.to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(raw.date)))
    assert len(forecasts) == manifest['robustness']['lag_forecasts']
    assert not forecasts.duplicated(['model', 'lag', 'date']).any()
    columns = ['MSE', 'RMSE', 'MAE', 'Variance_MSE', 'QLIKE']
    for (name, lag), frame in forecasts.groupby(['model', 'lag'], sort=False):
        assert pd.DatetimeIndex(frame.date).equals(targets)
        assert pd.DatetimeIndex(frame.origin_date).equals(origins)
        np.testing.assert_array_equal(frame.n_train, np.searchsorted(all_targets.to_numpy(), origins.to_numpy(), side='right'))
        assert frame.training_end.eq(frame.origin_date).all()
        np.testing.assert_allclose(frame.actual_variance, es.reindex(frame.date), rtol=1e-12)
        np.testing.assert_allclose(frame.predicted_variance, np.exp(frame.predicted_log) * frame.smearing, rtol=1e-12)
        ok = frame.status.eq('ok')
        assert frame.loc[ok, 'root'].lt(1).all()
        if (~ok).any():
            np.testing.assert_allclose(frame.loc[~ok, 'predicted_variance'], es.reindex(frame.loc[~ok, 'origin_date']), rtol=1e-12)
        if lag == manifest['shared_lag']:
            np.testing.assert_allclose(frame.predicted_log, main.loc[(name, frame.date.tolist()), 'predicted_log'], atol=1e-12)
        np.testing.assert_allclose(metrics.loc[(name, lag), columns].astype(float), scores(frame), rtol=1e-12)
    intervals = pd.read_csv(out / 'robustness_intervals.csv')
    assert np.isfinite(intervals[['gain_pct', 'lower_pct', 'upper_pct']]).all().all()
    assert (intervals.lower_pct <= intervals.upper_pct).all()
    print(f'Verified {len(forecasts):,} final-data lag forecasts and {len(intervals)} paired-loss interval rows.')


def main():
    cfg = json.loads((ROOT / 'config/var_har_notebook.json').read_text())
    assert cfg['input_format'] == 'prepared_wide'
    out = ROOT / cfg['output_dir']
    manifest = json.loads((out / 'provenance.json').read_text())
    assert sha(ROOT / cfg['source']) == manifest['source_sha256']
    assert sha(ROOT / cfg['har_reference']) == manifest['har_notebook_sha256']
    for name, value in manifest['code_sha256'].items():
        assert sha(ROOT / name) == value
    for name, value in manifest['output_sha256'].items():
        assert sha(out / name) == value
    notebook, code = check_notebook('VAR_QTFE.ipynb')
    assert sum('image/png' in output.get('data', {}) for cell in code for output in cell['outputs']) == 5
    raw = pd.read_csv(ROOT / cfg['source'], float_precision='round_trip')
    all_targets, origins, targets = expected_grid(raw, cfg)
    assert len(all_targets) == manifest['common_fit_targets']
    assert len(targets) == manifest['evaluation_targets']
    es = pd.Series(raw.rv5_ES.to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(raw.date)))
    forecasts = pd.read_csv(out / 'shared_forecasts.csv', float_precision='round_trip', parse_dates=['date', 'origin_date', 'training_end'])
    metrics = pd.read_csv(out / 'shared_forecast_metrics.csv', float_precision='round_trip', index_col=0)
    fits = pd.read_csv(out / 'common_sample_insample_results.csv', index_col=0)
    assert fits.N.eq(len(all_targets)).all()
    assert len(metrics) == manifest['models']
    assert not fits.index.str.contains('Restricted', case=False).any()
    assert not metrics.index.str.contains('Restricted', case=False).any()
    assert not forecasts.duplicated(['model', 'date']).any()
    columns = ['MSE', 'RMSE', 'MAE', 'Variance_MSE', 'QLIKE']
    for name, frame in forecasts.groupby('model', sort=False):
        assert pd.DatetimeIndex(frame.date).equals(targets)
        assert pd.DatetimeIndex(frame.origin_date).equals(origins)
        assert frame.training_end.eq(frame.origin_date).all()
        np.testing.assert_array_equal(frame.n_train, np.searchsorted(all_targets.to_numpy(), origins.to_numpy(), side='right'))
        np.testing.assert_allclose(frame.actual_variance, es.reindex(frame.date), rtol=1e-12)
        np.testing.assert_allclose(frame.actual_log, np.log(frame.actual_variance), atol=1e-12)
        np.testing.assert_allclose(frame.predicted_variance, np.exp(frame.predicted_log) * frame.smearing, rtol=1e-12)
        if name == 'Persistence' or frame.status.ne('ok').any():
            use = np.ones(len(frame), dtype=bool) if name == 'Persistence' else frame.status.ne('ok')
            np.testing.assert_allclose(frame.loc[use, 'predicted_variance'], es.reindex(frame.loc[use, 'origin_date']), rtol=1e-12)
        if name.startswith(('VAR', 'LVAR')):
            assert frame.loc[frame.status.eq('ok'), 'root'].lt(1).all()
        np.testing.assert_allclose(metrics.loc[name, columns].astype(float), scores(frame), rtol=1e-12)
        assert metrics.loc[name, 'Fallbacks'] == frame.status.ne('ok').sum()
    native = pd.read_csv(out / 'latest_har_forecast_audit.csv', index_col=0)
    assert set(native.index) == set(fits.index[fits.index.str.startswith(('HAR (', 'LHAR ('))])
    assert native.N.eq(len(targets)).all()
    assert native.N.sum() == manifest['har_reference_forecasts_checked']
    assert native.Max_prediction_difference.lt(1e-9).all()
    irfs = pd.read_csv(out / 'training_generalized_irfs.csv')
    assert len(irfs) == 5 * (cfg['irf']['horizon'] + 1)
    assert manifest['irf']['last_target'] == cfg['training_end']
    assert manifest['irf']['n'] == manifest['initial_fit_targets']
    np.testing.assert_allclose(irfs.variance_pct, 100 * np.expm1(irfs.log_response), atol=1e-12)
    verify_lag_run(out, manifest, raw)

    print(f'Verified the fully executed VAR notebook, final input/code/output hashes, {len(forecasts):,} shared forecasts across {len(metrics)} models, and {int(native.N.sum()):,} independent HAR/LHAR forecast matches. The HAR notebook was used as a read-only function reference.')


if __name__ == '__main__':
    main()
