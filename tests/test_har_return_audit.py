import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from har_forecasts import build_design, expanding_forecasts
from har_return_audit import equity_return_audit, add_return_controls, paired_block_intervals, exposed_design_rows


class ReturnAuditTests(unittest.TestCase):
    def test_return_identity_and_historical_roll_convention(self):
        dates = pd.bdate_range("2022-01-03", "2022-06-30")
        prices = pd.DataFrame({"open_price": np.arange(len(dates)) + 100.,
                               "close_price": np.arange(len(dates)) + 101.}, index=dates)
        audit, _ = equity_return_audit(prices)
        self.assertTrue(audit.loc["2022-03-10", "roll_candidate"])
        self.assertTrue(audit.loc["2022-06-13", "roll_candidate"])
        self.assertFalse(audit.calendar_verified.any())
        np.testing.assert_allclose(audit.close_to_close.iloc[1:],
            (audit.open_to_close + audit.opening_gap).iloc[1:], atol=1e-10)

    def test_matched_return_controls_and_no_future_leakage(self):
        rng = np.random.default_rng(19)
        dates = pd.bdate_range("2020-01-01", periods=170)
        variance = pd.DataFrame(np.exp(rng.normal(-8, 1, (170, 3))), index=dates,
                                columns=["ES", "CL", "GC"])
        returns = pd.Series(rng.normal(size=170), index=dates)
        design, groups = build_design(variance, returns)
        groups = add_return_controls(groups)
        self.assertEqual(groups["AR15_returns"][-3:], groups["LHAR"][-3:])
        target = dates[150]
        first = expanding_forecasts(design, groups, [target])
        variance.loc[target:] *= 8
        returns.loc[target:] -= 10
        changed, _ = build_design(variance, returns)
        second = expanding_forecasts(changed, groups, [target])
        assert_frame_equal(first.drop(columns="actual"), second.drop(columns="actual"))

    def test_paired_resampling_preserves_exact_loss_ratio(self):
        actual = np.arange(80) / 10
        baseline = actual + np.linspace(1, 2, 80)
        candidate = actual + .5 * np.linspace(1, 2, 80)
        result = paired_block_intervals(actual, baseline, candidate, draws=100)
        for field in ["gain_pct", "lower_pct", "upper_pct"]:
            self.assertAlmostEqual(result[field], 75.)
        null = paired_block_intervals(actual, baseline, baseline, draws=100)
        self.assertAlmostEqual(null["lower_pct"], 0.)
        self.assertAlmostEqual(null["upper_pct"], 0.)

    def test_suspect_mask_covers_target_and_lag_window_without_compressing_dates(self):
        dates = pd.bdate_range("2020-01-01", periods=90)
        design = pd.DataFrame({"target_date": dates[1:], "fixed_feature": np.arange(89)}, index=dates[:-1])
        issue = dates[40]
        mask = exposed_design_rows(design, dates, [issue], [issue])
        self.assertEqual(list(design.index[mask]), list(dates[39:62]))
        retained = design.loc[~mask]
        self.assertEqual(retained.loc[dates[62], "fixed_feature"], 62)
        self.assertEqual(retained.loc[dates[62], "target_date"], dates[63])


if __name__ == "__main__":
    unittest.main()
