"""Reproduce HAR notebook calculations and compare forecasts on a common sample.

Run with .venv/bin/python scripts/verify_har.py. Originals are not modified.
"""

import ast
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import scipy
from scipy import stats
import statsmodels
import statsmodels.api as sm

from har_forecasts import accuracy_table, build_design, expanding_forecasts
from volare_data import validate_source


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notebook_calculations(data, notebook, output):
    """Load only the two reviewed function definitions, not notebook side effects."""
    functions = {}
    env = dict(np=np, pd=pd, sm=sm, stats=stats)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        for node in ast.parse("".join(cell["source"])).body:
            if isinstance(node, ast.FunctionDef) and node.name in ("fit_har_x", "forecast_har_x"):
                exec(compile(ast.Module(body=[node], type_ignores=[]), "HAR_QTFE.ipynb", "exec"), env)
                functions[node.name] = env[node.name]
    d = data.copy()
    d["ret"] = d.groupby("symbol").close_price.transform(lambda s: np.log(s / s.shift(1)) * 100)
    d["log_rv5"] = np.log(d.rv5)
    d["rv5_scaled"] = d.rv5 * 10000
    for n, h in [(5, "w"), (22, "m")]:
        d[f"log_rv5_{h}"] = d.groupby("symbol").log_rv5.transform(lambda s: s.rolling(n).mean())
    wide = d.pivot(index="date", columns="symbol", values=["close_price", "ret", "log_rv5",
                   "rv5", "rv5_scaled", "log_rv5_w", "log_rv5_m"])
    wide.columns = [f"{c}_{s}" for c, s in wide.columns]
    wide = wide.dropna()  # Deliberate exact reproduction, not endorsed preparation.
    results = []
    for leverage in (False, True):
        for label, symbols in [("solo", []), ("oil", ["CL"]), ("gas", ["NG"]),
                               ("energy", ["CL", "NG"]), ("energy_gold", ["CL", "NG", "GC"])]:
            fit = functions["fit_har_x"](wide, exog_symbols=symbols,
                      include_exog_horizons=True, include_leverage=leverage)
            results.append(dict(model=("LHAR_" if leverage else "HAR_") + label,
                                n=int(fit.nobs), R2=fit.rsquared, AIC=fit.aic, BIC=fit.bic))
    table = pd.DataFrame(results)
    table.to_csv(output / "notebook_insample.csv", index=False)
    expected_r2 = np.array([.6963, .6965, .6970, .6973, .6981, .7243, .7246, .7255, .7258, .7266])
    if not np.all(np.abs(table.R2 - expected_r2) < .000051):
        raise ValueError("Notebook fit no longer matches stored R-squared values")
    forecast_metrics = []
    # Notebook's saved forecast call uses only daily commodity inputs and NO leverage.
    for label, symbols in [("HAR", []), ("HARX_all_daily", ["C", "CL", "GC", "NG"])]:
        f, metrics = functions["forecast_har_x"](wide, exog_symbols=symbols)
        f.index.name = "origin_date"
        mapping = pd.Series(wide.index, index=wide.index).shift(-1)
        f["target_date"] = mapping.reindex(f.index)
        f.to_csv(output / f"notebook_500_{label}.csv")
        forecast_metrics.append(dict(model=label, n=len(f), **metrics,
                                     target_start=str(f.target_date.min().date()),
                                     target_end=str(f.target_date.max().date())))
    pd.DataFrame(forecast_metrics).to_csv(output / "notebook_500_metrics.csv", index=False)
    return table


def main():
    output = ROOT / "reports/har_verification"
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / "datasets/realized_variance_futures.csv"
    notebook_path = ROOT / "HAR_QTFE.ipynb"
    inputs = {p.name: sha(p) for p in [source, notebook_path, ROOT / "har_forecasts.py", Path(__file__)]}
    data = validate_source(pd.read_csv(source))
    notebook = json.loads(notebook_path.read_text())
    table = notebook_calculations(data, notebook, output)
    print("Reproduced notebook in-sample R2 values.", flush=True)
    variance = data.pivot(index="date", columns="symbol", values="rv5")[["ES", "CL", "GC"]]
    variance = variance.loc["2011-01-01":]
    excluded = variance.loc[variance.isna().any(axis=1)]
    variance = variance.dropna()  # Reproduce teammate's explicit common-row definition.
    es = data.loc[data.symbol.eq("ES")].set_index("date")
    returns = 100 * np.log(es.close_price / es.close_price.shift(1))
    design, groups = build_design(variance, returns)
    n_initial = int(.8 * len(variance))
    targets = variance.index[n_initial:]
    forecasts = expanding_forecasts(design, groups, targets)
    metrics = accuracy_table(forecasts, [*groups, "Naive", "Mean"])
    forecasts.to_csv(output / "common_809_forecasts.csv", index=False)
    metrics.to_csv(output / "common_809_metrics.csv", index=False)
    excluded.to_csv(output / "excluded_incomplete_dates.csv")
    yearly = []
    for year, frame in forecasts.groupby(forecasts.date.dt.year):
        yearly.append(accuracy_table(frame, [*groups, "Naive"]).assign(year=year))
    pd.concat(yearly).to_csv(output / "common_809_yearly_metrics.csv", index=False)
    reference_path = ROOT / "reports/teammate_var/forecasts.csv"
    if reference_path.exists():
        reference = pd.read_csv(reference_path, parse_dates=["date", "origin_date"])
        if not (reference.date.equals(forecasts.date) and reference.origin_date.equals(forecasts.origin_date)
                and np.allclose(reference.actual, forecasts.actual, rtol=0, atol=1e-12)):
            raise ValueError("Comparison does not match the teammate's saved targets/origins")
    summary = dict(source_code_sha256=inputs, python=platform.python_version(),
                   numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__,
                   statsmodels=statsmodels.__version__, matched_observations=len(variance),
                   initial_history=n_initial, initial_fitted_targets=int(forecasts.n_train.iloc[0]),
                   test_observations=len(targets), target_start=str(targets.min().date()),
                   target_end=str(targets.max().date()), common_burn_in=22,
                   information_rule="training target_date <= origin_date < forecast target_date",
                   averaging="arithmetic mean of logs over 5/22 retained common observations",
                   leverage="negative part of mean unadjusted percent ES close log returns",
                   status="exploratory audit; session timing and roll treatment unverified",
                   notebook_r2_reproduced=True,
                   reference_dates_checked=reference_path.exists(),
                   output_sha256={p.name: sha(p) for p in output.glob("*.csv")})
    (output / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(metrics.to_string(index=False), flush=True)
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
