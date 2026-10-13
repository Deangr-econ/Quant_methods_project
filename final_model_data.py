"""Validate the team's final wide CSV and construct causal HAR features.

The supplied calendar, returns and yield measures are authoritative inputs.
Only variance averages and model features are derived; no old-file values,
external yield joins, imputation or quote corrections are introduced.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

SYMBOLS = ["ES", "CL", "C", "GC", "NG"]


def validate_final_frame(frame):
    required = {"date", "dgs10", "abs_dyield_10", "rv_yield_10"}
    required |= {f"{field}_{symbol}" for field in ["close_price", "rv5", "ret"] for symbol in SYMBOLS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing main-model columns: {sorted(missing)}")
    data = frame.copy()
    data["date"] = pd.to_datetime(data.date, format="%Y-%m-%d", errors="raise")
    if data.date.isna().any() or data.date.duplicated().any():
        raise ValueError("Dates must be present and unique")
    if not data.date.is_monotonic_increasing or not data.date.eq(data.date.dt.normalize()).all():
        raise ValueError("Expected increasing daily dates without timestamps")
    numeric = [column for column in data.columns if column != "date"]
    data[numeric] = data[numeric].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(data[numeric]).all().all():
        raise ValueError("The final input contains missing or infinite numeric values")
    for symbol in SYMBOLS:
        if not data[[f"close_price_{symbol}", f"rv5_{symbol}"]].gt(0).all().all():
            raise ValueError(f"Prices and RV5 must be positive for {symbol}")
        column = f"log_rv5_{symbol}"
        if column in data:
            if not np.allclose(data[column], np.log(data[f"rv5_{symbol}"]), rtol=0, atol=1e-9):
                raise ValueError(f"{column} is inconsistent with RV5")
        expected = 100 * np.log(data[f"close_price_{symbol}"] / data[f"close_price_{symbol}"].shift())
        if not np.allclose(data[f"ret_{symbol}"].iloc[1:], expected.iloc[1:], rtol=0, atol=1e-8):
            raise ValueError(f"ret_{symbol} must match close log returns in percentage units")
    change = 100 * data.dgs10.diff()
    if not np.allclose(data.abs_dyield_10.iloc[1:], change.abs().iloc[1:], rtol=0, atol=1e-8):
        raise ValueError("abs_dyield_10 must be absolute changes in basis points")
    if not np.allclose(data.rv_yield_10.iloc[1:], (change**2).iloc[1:], rtol=0, atol=1e-6):
        raise ValueError("rv_yield_10 must be squared basis-point changes")
    return data.set_index("date")


def prepare_final_data(frame, start="2011-01-01"):
    data = validate_final_frame(frame).loc[start:].copy()
    for symbol in SYMBOLS:
        data[f"log_rv5_{symbol}"] = np.log(data[f"rv5_{symbol}"])
        for window, horizon in [(5, "w"), (22, "m")]:
            data[f"log_rv5_{horizon}_{symbol}"] = data[f"log_rv5_{symbol}"].rolling(window).mean()
    excluded = data.loc[data.isna().any(axis=1)].copy()
    ready = data.dropna().copy()
    if len(ready) < 100:
        raise ValueError("Insufficient history after the 22-observation variance warm-up")
    return ready, excluded


def audit_final_data(frame):
    data = validate_final_frame(frame)
    errors = {}
    for symbol in SYMBOLS:
        expected = 100 * np.log(data[f"close_price_{symbol}"] / data[f"close_price_{symbol}"].shift())
        errors[f"return_{symbol}"] = float((data[f"ret_{symbol}"] - expected).iloc[1:].abs().max())
        if f"log_rv5_{symbol}" in data:
            errors[f"log_rv5_{symbol}"] = float((data[f"log_rv5_{symbol}"] - np.log(data[f"rv5_{symbol}"])).abs().max())
    change = 100 * data.dgs10.diff()
    errors["absolute_yield_change"] = float((data.abs_dyield_10 - change.abs()).iloc[1:].abs().max())
    errors["squared_yield_change"] = float((data.rv_yield_10 - change**2).iloc[1:].abs().max())
    return dict(rows=len(data), first_date=str(data.index.min().date()), last_date=str(data.index.max().date()),
                columns=list(frame.columns), missing_values=int(frame.isna().sum().sum()),
                duplicate_dates=0, ordered_dates=True, finite_numeric_values=True,
                positive_prices_and_variances=True, max_identity_errors=errors,
                return_units="percentage log returns; divide by 100 for downside controls",
                yield_units="dgs10 in percent; absolute/squared changes in basis points",
                first_row_note="The first supplied return/yield change needs a preceding observation absent from this file; it is preserved, not imputed.",
                unavailable_checks={"open_to_close_returns": "open_price_* absent",
                                    "rk_proxy": "rk_* absent", "full_ohlc_audit": "open/high/low prices absent",
                                    "old_review_masks": "Earlier review decisions belong to a different source hash"})


def large_return_flags(frame, threshold=15):
    data = validate_final_frame(frame)
    rows = []
    for symbol in SYMBOLS:
        for date, value in data.loc[data[f"ret_{symbol}"].abs().gt(threshold), f"ret_{symbol}"].items():
            rows.append(dict(date=date, symbol=symbol, return_pct=value,
                             flag="Large supplied close return; no quote/roll correction inferred"))
    return pd.DataFrame(rows, columns=["date", "symbol", "return_pct", "flag"]).sort_values(["date", "symbol"])


def test_stationarity_table(frame):
    rows = []
    for column in frame:
        values = frame[column].dropna()
        adf = adfuller(values, regression="c", autolag="AIC")
        with warnings.catch_warnings(record=True) as caught:
            result = kpss(values, regression="c", nlags="auto")
        bound = "<=" if result[1] == .01 else ">=" if result[1] == .1 else ""
        rows.append(dict(Variable=column, N=len(values), ADF_stat=adf[0], ADF_p=adf[1],
                         KPSS_stat=result[0], KPSS_p=f"{bound}{result[1]:.4f}",
                         Interpretation="Both support level stationarity" if adf[1] < .05 and result[1] > .05 else "Investigate persistence/conflicting tests",
                         Warning="; ".join(str(item.message) for item in caught)))
    return pd.DataFrame(rows).set_index("Variable")
