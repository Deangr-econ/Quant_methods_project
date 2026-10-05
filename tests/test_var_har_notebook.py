import ast
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

from var_har_notebook import (prepare_har_data, aligned_design, select_shared_lag,
    model_specifications, fit_models, expanding_forecasts, columns_for,
    reference_har_function)

ROOT = Path(__file__).resolve().parents[1]


class AlignedVARTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(ROOT / "datasets/realized_variance_futures.csv")
        cls.wide, _ = prepare_har_data(cls.raw)
        cls.design = aligned_design(cls.wide)
        cls.p, _ = select_shared_lag(cls.design, "2023-07-12")
        cls.specs = model_specifications(cls.p)

    def test_preparation_exactly_matches_current_har_cell(self):
        notebook = json.loads((ROOT / "HAR_QTFE.ipynb").read_text())
        env = dict(pd=pd, np=np, data_futures=self.raw)
        source = next("".join(c["source"]) for c in notebook["cells"]
                      if c["cell_type"] == "code" and "data.groupby" in "".join(c["source"]) and "rv5_scaled_m" in "".join(c["source"]))
        exec(compile(ast.parse(source), "reviewed HAR preparation", "exec"), env)
        pd.testing.assert_frame_equal(self.wide, env["df"])

    def test_native_var_same_es_equation_and_forecast(self):
        name = "VAR (All 4: Oil + Corn + Gold + NG)"
        fits, _ = fit_models(self.design, {name: self.specs[name]})
        native_values = self.wide[[f"log_rv5_{s}" for s in ["ES", "CL", "C", "GC", "NG"]]].iloc[22 - self.p:]
        # Retained observations are deliberately irregular provider dates.
        native = VAR(native_values.to_numpy()).fit(self.p)
        np.testing.assert_allclose(fits[name].fittedvalues, native.fittedvalues[:, 0], atol=1e-10)
        frame = self.design["x"]
        row = pd.DataFrame({f"{s}.l{lag}": [self.wide[f"log_rv5_{s}"].iloc[-lag]]
              for s in ["ES", "CL", "C", "GC", "NG"] for lag in range(1, self.p + 1)})
        expected = native.forecast(native_values.to_numpy()[-self.p:], 1)[0, 0]
        got = fits[name].predict(sm.add_constant(row[columns_for(self.specs[name])], has_constant="add"))[0]
        self.assertAlmostEqual(expected, got, places=10)

    def test_lhar_reference_features_and_hac_are_identical(self):
        name = "LHAR (No Corn: Oil + NG + Gold)"
        fits, summary = fit_models(self.design, {name: self.specs[name]})
        reference = reference_har_function(ROOT / "HAR_QTFE.ipynb")(
            self.wide, exog_symbols=["CL", "NG", "GC"], include_exog_horizons=True,
            include_leverage=True, hac_lags=22)
        # Our feature order is different; align by named columns.
        fit = fits[name]
        np.testing.assert_allclose(fit.params, reference.params.reindex(fit.params.index), atol=1e-10)
        np.testing.assert_allclose(fit.cov_params(), reference.cov_params().reindex(index=fit.params.index, columns=fit.params.index), atol=1e-10)
        self.assertEqual(summary.iloc[0]["N"], int(reference.nobs))

    def test_downside_definition_timing_and_future_invariance(self):
        name = "VAR + Downside (All 4: Oil + Corn + Gold + NG)"
        spec = {name: self.specs[name]}
        cutoff = self.wide.index[100]
        small = self.wide.iloc[:105]
        d = aligned_design(small)
        result = expanding_forecasts(d, spec, cutoff)
        origin = result.iloc[0].origin_date
        self.assertEqual(result.iloc[0].training_end, origin)
        self.assertGreater(result.iloc[0].date, origin)
        for window, label in [(1, "d"), (5, "w"), (22, "m")]:
            expected = -min(float(small.loc[:origin, "ret_ES"].tail(window).mean()), 0)
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

    def test_daily_restrictions_and_common_sample(self):
        daily = self.specs["Restricted VAR + Downside (All 4: Oil + Corn + Gold + NG; Daily Only)"]
        columns = columns_for(daily)
        self.assertIn("ES.l5", columns) if self.p >= 5 else None
        self.assertIn("C.l1", columns)
        self.assertNotIn("C.l2", columns)
        fits, summary = fit_models(self.design, self.specs)
        self.assertEqual(summary.N.nunique(), 1)
        self.assertEqual(int(summary.N.iloc[0]), 3967)
        self.assertEqual(int((self.design["target_dates"] > "2023-07-12").sum()), 802)


if __name__ == "__main__":
    unittest.main()
