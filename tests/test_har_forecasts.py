import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from har_forecasts import build_design, expanding_forecasts


class HARForecastTests(unittest.TestCase):
    def fixture(self):
        rng = np.random.default_rng(63)
        dates = pd.bdate_range("2020-01-01", periods=180)
        variance = pd.DataFrame(np.exp(rng.normal(-8, .8, (180, 3))), index=dates,
                                columns=["ES", "CL", "GC"])
        returns = pd.Series(rng.normal(0, 1, 180), index=dates)
        return variance, returns

    def test_averages_and_dates_use_information_through_origin(self):
        variance, returns = self.fixture()
        design, _ = build_design(variance, returns)
        first = design.iloc[0]
        self.assertEqual(first.target_date, variance.index[22])
        self.assertEqual(design.index[0], variance.index[21])
        self.assertAlmostEqual(first.ES_m, np.log(variance.ES.iloc[:22]).mean())
        self.assertAlmostEqual(first.ES_w, np.log(variance.ES.iloc[17:22]).mean())
        self.assertAlmostEqual(first.actual, np.log(variance.ES.iloc[22]))
        self.assertAlmostEqual(first.ES_down_w, max(-returns.iloc[17:22].mean(), 0))

    def test_changing_target_and_future_cannot_change_forecasts(self):
        variance, returns = self.fixture()
        design, groups = build_design(variance, returns)
        target = variance.index[150]
        first = expanding_forecasts(design, groups, [target])
        changed = variance.copy()
        changed.loc[target:] *= 9
        changed_ret = returns.copy()
        changed_ret.loc[target:] -= 20
        changed_design, _ = build_design(changed, changed_ret)
        second = expanding_forecasts(changed_design, groups, [target])
        assert_frame_equal(first.drop(columns="actual"), second.drop(columns="actual"))
        self.assertNotEqual(first.actual.iloc[0], second.actual.iloc[0])
        self.assertEqual(first.origin_date.iloc[0], variance.index[149])
        self.assertEqual(first.n_train.iloc[0], 150 - 22)

    def test_missing_value_is_not_silently_dropped(self):
        variance, returns = self.fixture()
        variance.iloc[70, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "positive variances"):
            build_design(variance, returns)


if __name__ == "__main__":
    unittest.main()
