"""Verify saved sensitivity records against raw outcomes and training dates."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def verify():
    out = ROOT/'reports/var_har_notebook/generated'
    manifest = json.loads((out/'provenance.json').read_text())
    settings = manifest['robustness']['settings']
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for name, digest in manifest['robustness']['input_sha256'].items():
        assert sha(ROOT/name) == digest, f'Changed sensitivity input: {name}'
    raw = pd.read_csv(ROOT/manifest['config']['source'], float_precision='round_trip')
    raw['date'] = pd.to_datetime(raw.date)
    selected = raw.loc[raw.date.ge(manifest['config']['sample_start'])].sort_values(['symbol', 'date']).copy()
    assert np.isfinite(selected[['rv5', 'rk', 'close_price']]).all().all()
    assert selected[['rv5', 'rk', 'close_price']].gt(0).all().all()
    # Independent reconstruction of the frozen complete-case/warm-up date grid.
    ready = selected.loc[selected.groupby('symbol').cumcount().ge(21)]
    counts = ready.groupby('date').symbol.nunique()
    panel_dates = pd.DatetimeIndex(counts.loc[counts.eq(5)].index)
    warmup = manifest['config']['common_warmup']
    origins, targets = panel_dates[warmup-1:-1], panel_dates[warmup:]
    assert len(targets) == manifest['common_fit_targets']
    evaluation = targets > pd.Timestamp(manifest['config']['training_end'])
    evaluation_targets = targets[evaluation]
    assert len(evaluation_targets) == manifest['evaluation_targets']
    forecasts = pd.read_csv(out/'robustness_forecasts.csv', float_precision='round_trip',
        parse_dates=['date', 'origin_date', 'training_end'])
    assert len(forecasts) == manifest['robustness']['records']
    assert not forecasts.duplicated(['scenario', 'lag', 'model', 'date']).any()
    assert np.isfinite(forecasts[['actual_log', 'predicted_log', 'predicted_variance']]).all().all()
    exclusions = pd.read_csv(out/'robustness_exclusions.csv', parse_dates=['origin_date', 'target_date'])
    metrics = pd.read_csv(out/'robustness_metrics.csv', float_precision='round_trip').set_index(['Scenario', 'Model'])
    lag_metrics = pd.read_csv(out/'robustness_lag_metrics.csv', float_precision='round_trip').set_index(['Lag', 'Model'])
    main = pd.read_csv(out/'shared_forecasts.csv', float_precision='round_trip', parse_dates=['date']).set_index(['model', 'date'])
    es = raw.loc[raw.symbol.eq('ES')].set_index('date')
    for (scenario, lag, name), frame in forecasts.groupby(['scenario', 'lag', 'model'], sort=False):
        assert pd.DatetimeIndex(frame.date).equals(evaluation_targets)
        assert pd.DatetimeIndex(frame.origin_date).equals(origins[evaluation])
        proxy = 'rk' if scenario == 'rk_proxy' else 'rv5'
        np.testing.assert_allclose(frame.actual_variance, es[proxy].reindex(frame.date), rtol=1e-12)
        np.testing.assert_allclose(frame.actual_log, np.log(frame.actual_variance), atol=1e-12)
        np.testing.assert_allclose(frame.predicted_variance, np.exp(frame.predicted_log)*frame.smearing, rtol=1e-12)
        omitted = exclusions.loc[exclusions.Scenario.eq(scenario)]
        eligible = ~origins.isin(omitted.origin_date)
        known_dates = targets[eligible]
        expected_n = np.searchsorted(known_dates.to_numpy(), frame.origin_date.to_numpy(), side='right')
        np.testing.assert_array_equal(frame.n_train, expected_n)
        assert pd.DatetimeIndex(frame.training_end).equals(known_dates[expected_n-1])
        assert (frame.training_end <= frame.origin_date).all()
        if scenario == 'baseline_rv5':
            original = main.loc[(name, frame.date.tolist()), :]
            np.testing.assert_allclose(frame.predicted_log, original.predicted_log, atol=1e-12)
        fallback = frame.status.ne('ok')
        if fallback.any():
            np.testing.assert_allclose(frame.loc[fallback, 'predicted_variance'],
                es[proxy].reindex(frame.loc[fallback, 'origin_date']), rtol=1e-12)
        if name.startswith('VAR'):
            assert frame.loc[~fallback, 'root'].lt(1).all()
        error = frame.actual_log-frame.predicted_log
        ratio = frame.actual_variance/frame.predicted_variance
        expected_scores = [np.mean(error**2), np.sqrt(np.mean(error**2)), np.mean(np.abs(error)),
            np.mean((frame.actual_variance-frame.predicted_variance)**2), np.mean(ratio-np.log(ratio)-1)]
        saved = lag_metrics.loc[(lag, name)] if scenario == 'lag_sensitivity' else metrics.loc[(scenario, name)]
        np.testing.assert_allclose(saved[['MSE', 'RMSE', 'MAE', 'Variance_MSE', 'QLIKE']].astype(float), expected_scores, rtol=1e-12)
        assert saved.Fallbacks == int(fallback.sum()) and saved.N == len(evaluation_targets)
    exposure = pd.read_csv(out/'robustness_evaluation_exposure.csv', parse_dates=['origin_date', 'target_date'])
    assert pd.DatetimeIndex(exposure.target_date).equals(evaluation_targets)
    subset_dates = exposure.loc[~exposure.broad_exposure, 'target_date']
    subset_metrics = pd.read_csv(out/'robustness_subset_metrics.csv').set_index('Model')
    for name, frame in forecasts.loc[forecasts.scenario.eq('baseline_rv5')].groupby('model', sort=False):
        subset = frame.loc[frame.date.isin(subset_dates)]
        assert subset_metrics.loc[name, 'N'] == len(subset_dates)
        np.testing.assert_allclose(subset_metrics.loc[name, 'MSE'],
            np.mean((subset.actual_log-subset.predicted_log)**2), rtol=1e-12)
    assert len(set(forecasts.scenario)-{'lag_sensitivity'}) == len(settings['scenarios'])
    print(f"Verified {len(forecasts):,} sensitivity forecasts: identical target/origin grids, raw RV5/RK outcomes, past-only eligible training, fallback counts and losses; {len(subset_dates)} paired retrospective subset targets.")


if __name__ == '__main__':
    verify()
