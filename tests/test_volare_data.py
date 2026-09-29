"""Checks of transformations, calendar preservation and absence of look-ahead."""

import unittest
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from volare_data import validate_source, make_panel, quality_flags, load_var_panel


def fixture():
    rows = []
    for date in ("2020-01-02", "2020-01-03", "2020-01-06"):
        for symbol in ("ES", "CL"):
            rows.append(dict(date=date, symbol=symbol, asset_type="futures",
                             open_price=100., close_price=101., high_price=102.,
                             low_price=99., rk=.0001, rv5=.00012, rv5_ss=.00011))
    return pd.DataFrame(rows)


class PreparationTests(unittest.TestCase):
    def prepare(self, frame):
        return validate_source(frame, symbols=("ES", "CL"))

    def test_duplicate_keys_are_rejected(self):
        raw = fixture()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.prepare(pd.concat([raw, raw.iloc[[0]]]))

    def test_dates_missing_observations_and_initial_variance_are_preserved(self):
        raw = fixture().drop(index=3)  # CL absent on the middle date
        panel = make_panel(self.prepare(raw), "rk", symbols=("ES", "CL"))
        self.assertEqual(len(panel), 3)
        self.assertEqual(panel.index[0], pd.Timestamp("2020-01-02"))
        self.assertTrue(np.isnan(panel.loc["2020-01-03", "rk_CL"]))
        self.assertEqual(panel.loc["2020-01-03", "rk_ES"], .0001)

    def test_transformations_retain_the_correct_measure_and_units(self):
        data = self.prepare(fixture())
        for measure, value in [("rk", .0001), ("rv5", .00012)]:
            panel = make_panel(data, measure, symbols=("ES", "CL"))
            np.testing.assert_allclose(panel[f"{measure}_ES"], value)
            np.testing.assert_allclose(panel[f"{measure}_scaled_ES"], value * 10000)
            np.testing.assert_allclose(panel[f"log_{measure}_scaled_ES"], np.log(value * 10000))

    def test_nonpositive_measure_is_flagged_without_deleting_date(self):
        raw = fixture()
        raw.loc[0, "rk"] = 0
        data = self.prepare(raw)
        panel = make_panel(data, "rk", symbols=("ES", "CL"))
        self.assertEqual(len(panel), 3)
        self.assertEqual(panel.iloc[0]["rk_ES"], 0)
        self.assertTrue(np.isnan(panel.iloc[0]["log_rk_scaled_ES"]))
        self.assertIn("nonpositive_rk", quality_flags(data).iloc[0]["flags"])

    def test_suspicious_value_retained_and_future_changes_do_not_change_past(self):
        raw = fixture()
        data = self.prepare(raw)
        changed = raw.copy()
        changed.loc[changed.date == "2020-01-06", ["rk", "low_price"]] = [2., 1.]
        later = self.prepare(changed)
        for measure in ("rk", "rv5"):
            baseline = make_panel(data, measure, symbols=("ES", "CL"))
            alternative = make_panel(later, measure, symbols=("ES", "CL"))
            assert_frame_equal(baseline.loc[:"2020-01-03"], alternative.loc[:"2020-01-03"])
        self.assertEqual(make_panel(later, "rk", symbols=("ES", "CL")).loc["2020-01-06", "rk_ES"], 2.)
        flags = quality_flags(later)
        self.assertEqual(set(flags.date), {pd.Timestamp("2020-01-06")})

    def test_sorting_and_loader_preserve_dates_and_column_order(self):
        raw = fixture().drop(index=3)
        first = make_panel(self.prepare(raw), "rv5", symbols=("ES", "CL"))
        shuffled = make_panel(self.prepare(raw.sample(frac=1, random_state=1)), "rv5", symbols=("ES", "CL"))
        assert_frame_equal(first, shuffled)
        with tempfile.TemporaryDirectory() as folder:
            first.to_csv(Path(folder) / "volare_rv5.csv")
            loaded = load_var_panel("rv5", ("CL", "ES"), folder)
            self.assertEqual(list(loaded.columns), ["log_rv5_scaled_CL", "log_rv5_scaled_ES"])
            self.assertEqual(len(loaded), 3)
            self.assertTrue(np.isnan(loaded.loc["2020-01-03"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
