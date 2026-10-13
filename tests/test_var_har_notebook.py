from pathlib import Path
import unittest

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from final_model_data import prepare_final_data, validate_final_frame

from var_har_notebook import (prepare_har_data, aligned_design, select_shared_lag,
    model_specifications, fit_models, expanding_forecasts, columns_for,
    reference_har_function, reference_har_preparation, load_yield_snapshot,
    audit_reference_har_forecasts)

ROOT = Path(__file__).resolve().parents[1]


class AlignedVARTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(ROOT / "datasets/vol_data_futures_yield_final_version.csv", float_precision="round_trip")
        cls.wide, _ = prepare_final_data(cls.raw)
        cls.design = aligned_design(cls.wide)
        cls.p, _ = select_shared_lag(cls.design, "2023-07-12")
        cls.specs = model_specifications(cls.p)

    def test_preparation_exactly_matches_current_har_cell(self):
        reference = reference_har_preparation(self.raw, None, ROOT / "HAR_QTFE.ipynb")
        pd.testing.assert_frame_equal(self.wide, reference)

    def test_final_yields_are_validated_without_imputation(self):
        altered = self.raw.copy()
        altered.loc[10, "dgs10"] = np.nan
        with self.assertRaises(ValueError):
            prepare_final_data(altered)
        altered = self.raw.copy()
        altered.loc[10, "rv_yield_10"] += 100
        with self.assertRaises(ValueError):
            prepare_final_data(altered)

    def test_final_calendar_and_supplied_returns_are_preserved(self):
        supplied = validate_final_frame(self.raw)
        self.assertTrue(self.wide.index.equals(supplied.index[21:]))
        pd.testing.assert_frame_equal(self.wide[["ret_ES", "dgs10", "rv_yield_10"]],
                                     supplied.loc[self.wide.index, ["ret_ES", "dgs10", "rv_yield_10"]])

    def test_native_var_same_es_equation_and_forecast(self):
        for name in ["VAR (All 4: Oil + Corn + Gold + NG)", "VAR (Gold)", "LVAR (Gold)",
                     "VAR (Corn)", "LVAR (Corn)", "VAR (Corn + Gold)", "LVAR (Corn + Gold)"]:
            with self.subTest(model=name):
                spec = self.specs[name]
                symbols = ["ES", *spec["commodities"]]
                fits, _ = fit_models(self.design, {name: spec})
                native_values = self.wide[[f"log_rv5_{s}" for s in symbols]].iloc[22 - self.p:]
                controls = [f"ES_down_{h}" for h in ["d", "w", "m"]]
                exog = None
                if spec["downside"]:
                    # Native VAR drops its first p rows. Pad only those unused
                    # rows, then align each target with its origin's controls.
                    exog = np.vstack([np.zeros((self.p, 3)), self.design["x"][controls].to_numpy()])
                native = VAR(native_values.to_numpy(), exog=exog).fit(self.p)
                np.testing.assert_allclose(fits[name].fittedvalues, native.fittedvalues[:, 0], atol=1e-10)
                row = pd.DataFrame({f"{s}.l{lag}": [self.wide[f"log_rv5_{s}"].iloc[-lag]]
                      for s in symbols for lag in range(1, self.p + 1)})
                future_exog = None
                if spec["downside"]:
                    ret = self.wide.ret_ES / 100
                    for window, column in zip([1, 5, 22], controls):
                        row[column] = -min(float(ret.tail(window).mean()), 0)
                    future_exog = row[controls].to_numpy()
                expected = native.forecast(native_values.to_numpy()[-self.p:], 1, exog_future=future_exog)[0, 0]
                got = fits[name].predict(sm.add_constant(row[columns_for(spec)], has_constant="add"))[0]
                self.assertAlmostEqual(expected, got, places=10)

    def test_har_reference_features_and_hac_are_identical(self):
        names = ["HAR (Baseline)", "HAR (Oil + Gold)", "HAR (Energy: Oil + NG)",
                 "LHAR (Oil + Gold)", "LHAR (Energy: Oil + NG)", "LHAR (No Corn: Oil + NG + Gold)"]
        for name in names:
            with self.subTest(model=name):
                spec = self.specs[name]
                fits, summary = fit_models(self.design, {name: spec})
                wide = self.wide if spec["downside"] else self.wide.loc[self.design["x"].index[0]:]
                reference = reference_har_function(ROOT / "HAR_QTFE.ipynb")(
                    wide, exog_symbols=spec["commodities"], include_exog_horizons=True,
                    include_leverage=spec["downside"], hac_lags=22)
                # Our feature order is different; align by named columns.
                fit = fits[name]
                np.testing.assert_allclose(fit.params, reference.params.reindex(fit.params.index), atol=1e-10)
                np.testing.assert_allclose(fit.cov_params(), reference.cov_params().reindex(index=fit.params.index, columns=fit.params.index), atol=1e-10)
                self.assertEqual(summary.iloc[0]["N"], int(reference.nobs))

    def test_downside_definition_timing_and_future_invariance(self):
        name = "LVAR (All 4: Oil + Corn + Gold + NG)"
        spec = {name: self.specs[name]}
        cutoff = self.wide.index[100]
        small = self.wide.iloc[:105]
        d = aligned_design(small)
        result = expanding_forecasts(d, spec, cutoff)
        origin = result.iloc[0].origin_date
        self.assertEqual(result.iloc[0].training_end, origin)
        self.assertGreater(result.iloc[0].date, origin)
        for window, label in [(1, "d"), (5, "w"), (22, "m")]:
            expected = -min(float((small.loc[:origin, "ret_ES"] / 100).tail(window).mean()), 0)
            self.assertAlmostEqual(d["x"].loc[origin, f"ES_down_{label}"], expected)
        altered = small.copy()
        future = altered.index > origin
        for c in altered.columns:
            if c.startswith("log_rv5") or c == "ret_ES":
                altered.loc[future, c] += 4
        second = expanding_forecasts(aligned_design(altered), spec, cutoff)
        np.testing.assert_allclose(result.iloc[0][["predicted_log", "predicted_variance", "smearing"]].astype(float),
                                   second.iloc[0][["predicted_log", "predicted_variance", "smearing"]].astype(float), atol=1e-12)
        self.assertNotEqual(result.iloc[0].actual_log, second.iloc[0].actual_log)

    def test_latest_har_forecasts_share_cutoff_origins_targets_and_predictions(self):
        small = self.wide.iloc[:130]
        design = aligned_design(small)
        cutoff = small.index[-8]
        names = ["HAR (Baseline)", "HAR (Oil + Gold)", "HAR (Energy: Oil + NG)",
                 "LHAR (Oil + Gold)", "LHAR (Energy: Oil + NG)", "LHAR (No Corn: Oil + NG + Gold)"]
        specs = {name: self.specs[name] for name in names}
        forecasts = expanding_forecasts(design, specs, cutoff)
        audit = audit_reference_har_forecasts(small, design, specs, forecasts,
            cutoff, ROOT / "HAR_QTFE.ipynb")
        self.assertEqual(audit.N.tolist(), [7] * len(names))
        self.assertTrue((audit.Max_prediction_difference < 1e-9).all())
        self.assertTrue((audit.First_origin < audit.First_target).all())
        self.assertTrue((forecasts.training_end == forecasts.origin_date).all())

    def test_return_rescaling_changes_coefficients_but_not_predictions(self):
        name = "LVAR (Baseline)"
        spec = {name: self.specs[name]}
        decimal, _ = fit_models(self.design, spec)
        percent_design = dict(self.design, x=self.design['x'].copy())
        cols = [f"ES_down_{h}" for h in ["d", "w", "m"]]
        percent_design['x'][cols] *= 100
        percent, _ = fit_models(percent_design, spec)
        np.testing.assert_allclose(decimal[name].fittedvalues, percent[name].fittedvalues, atol=1e-10)
        np.testing.assert_allclose(decimal[name].params[cols], percent[name].params[cols]*100, atol=1e-8)

    def test_models_use_the_common_fit_and_evaluation_sample(self):
        fits, summary = fit_models(self.design, self.specs)
        self.assertEqual(summary.N.nunique(), 1)
        self.assertEqual(int(summary.N.iloc[0]), len(self.raw) - 43)
        self.assertEqual(int((self.design["target_dates"] > "2023-07-12").sum()),
                         int(pd.to_datetime(self.raw.date).gt("2023-07-12").sum()))


if __name__ == "__main__":
    unittest.main()
