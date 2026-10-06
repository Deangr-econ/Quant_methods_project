import unittest

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

from var_har_notebook import prepare_har_data, aligned_design, model_specifications, columns_for
from var_irf import lag_matrices, moving_average, generalized_responses, joint_hac_covariance, estimate_irf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IRFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wide, _ = prepare_har_data(pd.read_csv(ROOT / 'datasets/realized_variance_futures.csv'))
        cls.design = aligned_design(cls.wide)
        cls.spec = model_specifications(5)['VAR + Downside (All 4: Oil + Corn + Gold + NG)']

    def test_native_var_moving_average_and_named_lag_mapping(self):
        symbols = ['ES', 'CL', 'C', 'GC', 'NG']
        spec = dict(self.spec, downside=False)
        columns = columns_for(spec)
        x = sm.add_constant(self.design['x'][columns], has_constant='add')
        b = np.linalg.lstsq(x, self.design['y'][symbols], rcond=None)[0]
        values = self.wide[[f'log_rv5_{s}' for s in symbols]].iloc[22-5:].to_numpy()
        native = VAR(values).fit(5)
        matrices = lag_matrices(b, columns, symbols, 5)
        np.testing.assert_allclose(matrices, native.coefs, atol=1e-10)
        np.testing.assert_allclose(moving_average(matrices, 20), native.ma_rep(20), atol=1e-10)

    def test_generalized_impact_and_order_invariance(self):
        matrices = np.array([[[.5, .2], [.1, .3]], [[.1, 0], [0, .1]]])
        sigma = np.array([[2., .4], [.4, 1.]])
        response = generalized_responses(matrices, sigma, 20)
        np.testing.assert_allclose(response[0], sigma / np.sqrt(np.diag(sigma))[None, :])
        reverse = generalized_responses(matrices[:, ::-1, ::-1], sigma[::-1, ::-1], 20)
        np.testing.assert_allclose(response, reverse[:, ::-1, ::-1], atol=1e-12)

    def test_joint_hac_coefficients_match_statsmodels_and_sigma_is_uncertain(self):
        keep = self.design['target_dates'] <= '2023-07-12'
        x = sm.add_constant(self.design['x'].loc[keep, columns_for(self.spec)], has_constant='add').to_numpy()
        y = self.design['y'].loc[keep].to_numpy()
        b = np.linalg.lstsq(x, y, rcond=None)[0]
        u = y - x @ b
        sigma = u.T @ u / len(u)
        covariance = joint_hac_covariance(x, u, sigma, 22)
        q = x.shape[1]
        for j in range(y.shape[1]):
            native = sm.OLS(y[:, j], x).fit(cov_type='HAC', cov_kwds={'maxlags': 22, 'use_correction': False})
            np.testing.assert_allclose(covariance[j*q:(j+1)*q, j*q:(j+1)*q], native.cov_params(), atol=1e-10, rtol=1e-8)
        self.assertTrue((np.diag(covariance)[b.size:] > 0).all())
        self.assertGreaterEqual(np.linalg.eigvalsh(covariance).min(), -1e-12)

    def test_training_only_bands_reproducible_and_future_invariant(self):
        frame, metadata = estimate_irf(self.design, self.spec, '2023-07-12', draws=200, seed=10)
        altered = dict(self.design, y=self.design['y'].copy(), x=self.design['x'].copy())
        future = self.design['target_dates'] > '2023-07-12'
        altered['y'].loc[future] += 100
        altered['x'].loc[future] += 100
        second, second_metadata = estimate_irf(altered, self.spec, '2023-07-12', draws=200, seed=10)
        pd.testing.assert_frame_equal(frame, second)
        self.assertEqual(metadata, second_metadata)
        self.assertEqual(metadata['n'], 3165)
        self.assertEqual(metadata['draws_requested'], metadata['draws_accepted'] + metadata['rejected_nonpositive_covariance'] + metadata['rejected_unstable'])
        self.assertTrue(np.isfinite(frame.select_dtypes('number')).all().all())
        self.assertTrue((frame.log_lower <= frame.log_upper).all())
        impact = frame.loc[frame.horizon.eq(0)]
        self.assertTrue((impact.log_lower < impact.log_upper).all())
        np.testing.assert_allclose(frame.variance_pct, 100*np.expm1(frame.log_response))
        np.testing.assert_allclose(frame.volatility_pct, 100*np.expm1(frame.log_response/2))

    def test_reject_invalid_covariance(self):
        with self.assertRaises(ValueError):
            generalized_responses(np.array([np.eye(2)*.5]), np.array([[1., 2.], [2., 1.]]), 20)


if __name__ == '__main__':
    unittest.main()
