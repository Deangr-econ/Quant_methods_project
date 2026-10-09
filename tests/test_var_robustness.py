import unittest
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

from var_har_notebook import (prepare_har_data, aligned_design, model_specifications,
    fit_models, expanding_forecasts)
from var_robustness import exposure_mask, sensitivity_panel, flag_evidence


class RobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(77)
        cls.dates = pd.bdate_range("2020-01-01", periods=180)
        rows = []
        for symbol in ["ES", "CL", "C", "GC", "NG"]:
            prices = 100*np.exp(np.cumsum(rng.normal(0, .01, len(cls.dates))))
            for i, date in enumerate(cls.dates):
                variance = np.exp(rng.normal(-9, .6))
                rows.append(dict(date=date, symbol=symbol, close_price=prices[i],
                    open_price=prices[i]*np.exp(rng.normal(0, .005)), rv5=variance,
                    rk=variance*np.exp(rng.normal(0, .15))))
        cls.raw = pd.DataFrame(rows)
        cls.wide, _ = prepare_har_data(cls.raw)
        cls.design = aligned_design(cls.wide)

    def test_exposure_covers_targets_and_following_es_return_without_compression(self):
        issue = self.wide.index[50]
        mask = exposure_mask(self.raw, self.wide, self.design,
            [{"date": issue, "symbol": "ES"}])
        pos = self.wide.index.get_loc(issue)
        self.assertTrue(mask.loc[self.wide.index[pos-1]])  # Suspect next target.
        self.assertTrue(mask.loc[self.wide.index[pos+22]])  # Following return in 22-row mean.
        self.assertFalse(mask.loc[self.wide.index[pos+23]])
        original = self.design['x'].copy()
        retained = original.loc[~mask]
        date = self.wide.index[pos+23]
        self.assertEqual(retained.loc[date, 'ES.l10'], original.loc[date, 'ES.l10'])
        self.assertEqual(self.design['target_dates'].loc[date], self.wide.index[pos+24])

    def test_source_grid_issue_is_not_lost_when_date_absent_from_common_panel(self):
        issue = self.dates[80]
        raw = self.raw.loc[~(self.raw.symbol.eq('C') & self.raw.date.eq(issue))]
        wide, _ = prepare_har_data(raw)
        design = aligned_design(wide)
        self.assertNotIn(issue, wide.index)
        mask = exposure_mask(raw, wide, design, [{"date": issue, "symbol": "GC"}])
        self.assertTrue(mask.loc[self.dates[81]])
        self.assertTrue(mask.loc[self.dates[101]])
        self.assertFalse(mask.loc[self.dates[102]])

    def test_unknown_issue_date_is_rejected(self):
        with self.assertRaises(ValueError):
            exposure_mask(self.raw, self.wide, self.design,
                [{"date": "1990-01-01", "symbol": "ES"}])

    def test_sensitivity_proxy_returns_and_dates_preserve_original_input(self):
        before = self.raw.copy(deep=True)
        rk = sensitivity_panel(self.raw, self.wide, 'rk_proxy')
        open_close = sensitivity_panel(self.raw, self.wide, 'open_to_close_returns')
        es = self.raw.loc[self.raw.symbol.eq('ES')].set_index('date')
        np.testing.assert_allclose(rk.log_rv5_ES, np.log(es.rk.reindex(rk.index)))
        np.testing.assert_allclose(open_close.ret_ES,
            100*np.log(es.close_price/es.open_price).reindex(open_close.index))
        pd.testing.assert_frame_equal(open_close.drop(columns='ret_ES'), self.wide.drop(columns='ret_ES'))
        self.assertTrue(rk.index.equals(self.wide.index))
        pd.testing.assert_frame_equal(self.raw, before)

    def test_three_market_var10_agrees_with_native_var(self):
        name = 'VAR (Oil + Gold)'
        spec = {name: model_specifications(10)[name]}
        fit, _ = fit_models(self.design, spec)
        values = self.wide[['log_rv5_ES', 'log_rv5_CL', 'log_rv5_GC']].iloc[22-10:].to_numpy()
        native = VAR(values).fit(10)
        np.testing.assert_allclose(fit[name].fittedvalues, native.fittedvalues[:, 0], atol=1e-10)

    def test_masked_forecast_matches_native_past_only_fit_and_future_mask_invariance(self):
        spec = {'VAR (Baseline)': model_specifications(1)['VAR (Baseline)']}
        cutoff = self.design['target_dates'].iloc[-6]
        eligible = pd.Series(True, index=self.design['x'].index)
        eligible.iloc[:4] = False
        before = self.design['x'].copy(deep=True)
        forecasts = expanding_forecasts(self.design, spec, cutoff, training_eligible=eligible)
        first = forecasts.iloc[0]
        mask = (self.design['target_dates'] <= first.origin_date) & eligible
        x = sm.add_constant(self.design['x'][['ES.l1']], has_constant='add')
        native = sm.OLS(self.design['y'].loc[mask, 'ES'], x.loc[mask]).fit()
        self.assertAlmostEqual(first.predicted_log,
            float(native.predict(x.loc[[first.origin_date]]).iloc[0]), places=10)
        self.assertEqual(first.n_train, int(mask.sum()))
        altered = eligible.copy()
        altered.loc[self.design['target_dates'] > first.origin_date] = False
        second = expanding_forecasts(self.design, spec, cutoff, training_eligible=altered)
        self.assertAlmostEqual(first.predicted_log, second.iloc[0].predicted_log, places=12)
        pd.testing.assert_frame_equal(self.design['x'], before)

    def test_training_mask_requires_exact_date_alignment(self):
        eligible = pd.Series(True, index=self.design['x'].index[::-1])
        with self.assertRaises(ValueError):
            expanding_forecasts(self.design, {'VAR (Baseline)': model_specifications(1)['VAR (Baseline)']},
                self.wide.index[-6], training_eligible=eligible)

    def test_review_status_distinguishes_crisis_moves_from_unconfirmed_errors(self):
        root = Path(__file__).resolve().parents[1]
        source = root/'datasets/realized_variance_futures.csv'
        flags = flag_evidence(pd.read_csv(source),
            pd.read_csv(root/'datasets/volare_review_decisions.csv'),
            hashlib.sha256(source.read_bytes()).hexdigest())
        crisis = flags.loc[flags.decision.eq('retain_crisis_move_provisional')]
        self.assertEqual(len(crisis), 9)
        self.assertFalse(flags.confirmed_error.any())
        self.assertTrue(crisis.assessment.str.startswith('Crisis move').all())
        self.assertTrue(flags.loc[flags.symbol.eq('GC'), 'assessment'].str.contains('unresolved').all())


if __name__ == '__main__':
    unittest.main()
