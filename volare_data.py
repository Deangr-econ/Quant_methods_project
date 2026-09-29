"""Dated VOLARE variance panels and transparent, non-destructive quality checks.

No imputation, row deletion, return construction for modelling, lagging, or
train/test-dependent estimation happens here. The date grid is the union of
observed source dates, not a verified exchange trading calendar.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SYMBOLS = ("ES", "CL", "GC", "NG", "C")
MEASURES = ("rk", "rv5")
PRICE_COLUMNS = ("open_price", "close_price", "high_price", "low_price")
MEASURE_COLUMNS = ("rk", "rv5", "rv5_ss")
RULES = {
    "rk_rv5_ratio_high": 10.0,
    "rk_rv5_ratio_low": 0.1,
    "low_to_open_close": 0.75,
    "high_to_open_close": 1.25,
    "absolute_unadjusted_close_log_return_pct": 20.0,
}


def validate_source(frame, symbols=SYMBOLS):
    """Validate keys/schema; allow missing/nonpositive values for explicit review."""
    required = {"date", "symbol", "asset_type", *PRICE_COLUMNS, *MEASURE_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    data = frame.copy()
    if data["symbol"].isna().any() or data["date"].isna().any():
        raise ValueError("Missing date or symbol key")
    data["date"] = pd.to_datetime(data["date"], format="%Y-%m-%d", errors="raise")
    if (data["date"] != data["date"].dt.normalize()).any():
        raise ValueError("Expected daily dates without intraday timestamps")
    if data.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate date/symbol keys; resolve them in the source")
    absent = set(symbols) - set(data["symbol"])
    if absent:
        raise ValueError(f"Requested symbols absent: {sorted(absent)}")
    data = data.loc[data["symbol"].isin(symbols)].copy()
    if not data["asset_type"].eq("futures").all():
        raise ValueError("Expected asset_type=futures for the selected symbols")
    for column in (*PRICE_COLUMNS, *MEASURE_COLUMNS):
        data[column] = pd.to_numeric(data[column], errors="raise")
        if np.isinf(data[column].to_numpy(dtype=float)).any():
            raise ValueError(f"Infinite source values in {column}")
    return data.sort_values(["symbol", "date"]).reset_index(drop=True)


def make_panel(data, measure, symbols=SYMBOLS):
    """Return source variance, scaled variance and logs on the full source-date union."""
    if measure not in MEASURES:
        raise ValueError(f"measure must be one of {MEASURES}")
    wide = data.pivot(index="date", columns="symbol", values=measure)
    wide = wide.reindex(columns=list(symbols)).sort_index()
    panel = pd.DataFrame(index=wide.index)
    for symbol in symbols:
        value = wide[symbol]
        scaled = value * 10000.0
        # Preserve invalid source values, but do not attempt to log them.
        panel[f"{measure}_{symbol}"] = value
        panel[f"{measure}_scaled_{symbol}"] = scaled
        panel[f"log_{measure}_scaled_{symbol}"] = np.log(scaled.where(scaled > 0))
    return panel


def quality_flags(data):
    """Fixed screening rules; flags are not confirmed errors and never delete data."""
    d = data.copy()
    d["rk_to_rv5"] = d["rk"] / d["rv5"].where(d["rv5"] > 0)
    previous = d.groupby("symbol")["close_price"].shift(1)
    positive = (d["close_price"] > 0) & (previous > 0)
    d["unadjusted_close_log_return_pct"] = 100 * np.log(
        d["close_price"].where(positive) / previous.where(positive)
    )
    conditions = {}
    for column in (*PRICE_COLUMNS, *MEASURE_COLUMNS):
        conditions[f"missing_{column}"] = d[column].isna()
        conditions[f"nonpositive_{column}"] = d[column].le(0)
    conditions["ohlc_inconsistent"] = (
        (d["low_price"] > d["high_price"])
        | (d["open_price"] < d["low_price"])
        | (d["open_price"] > d["high_price"])
        | (d["close_price"] < d["low_price"])
        | (d["close_price"] > d["high_price"])
    )
    conditions["rk_rv5_disagreement"] = (
        (d["rk_to_rv5"] > RULES["rk_rv5_ratio_high"])
        | (d["rk_to_rv5"] < RULES["rk_rv5_ratio_low"])
    )
    anchor_low = d[["open_price", "close_price"]].min(axis=1, skipna=False)
    anchor_high = d[["open_price", "close_price"]].max(axis=1, skipna=False)
    conditions["low_far_below_open_close"] = (
        d["low_price"] < RULES["low_to_open_close"] * anchor_low
    )
    conditions["high_far_above_open_close"] = (
        d["high_price"] > RULES["high_to_open_close"] * anchor_high
    )
    conditions["large_unadjusted_close_move_possible_roll"] = (
        d["unadjusted_close_log_return_pct"].abs()
        > RULES["absolute_unadjusted_close_log_return_pct"]
    )
    mask = pd.DataFrame(conditions).fillna(False)
    d["flags"] = mask.apply(lambda row: ";".join(row.index[row]), axis=1)
    d["status"] = "unreviewed"
    columns = ["date", "symbol", "flags", "status", *PRICE_COLUMNS,
               *MEASURE_COLUMNS, "rk_to_rv5", "unadjusted_close_log_return_pct"]
    return d.loc[mask.any(axis=1), columns].sort_values(["date", "symbol"])


def availability_table(data, symbols=SYMBOLS):
    """Expose gaps relative to other observed assets; does not infer exchange holidays."""
    dates = pd.DatetimeIndex(sorted(data["date"].unique()), name="date")
    grid = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    source = data.set_index(["date", "symbol"])
    calendar = pd.DataFrame(index=grid)
    calendar["source_observed"] = grid.isin(source.index)
    for measure in MEASURES:
        values = source[measure].reindex(grid)
        calendar[f"{measure}_valid_for_log"] = values.notna() & values.gt(0)
    calendar["status"] = np.where(
        calendar["source_observed"], "observed", "not_observed_on_union_date"
    )
    return calendar.reset_index()


def coverage_table(data, panels, symbols=SYMBOLS):
    records = []
    for symbol in symbols:
        group = data.loc[data["symbol"] == symbol]
        record = {
            "symbol": symbol, "source_rows": len(group),
            "first_date": group["date"].min(), "last_date": group["date"].max(),
            "absent_on_union_dates": len(panels["rk"]) - len(group),
        }
        for measure in MEASURES:
            record[f"{measure}_missing_in_source"] = int(group[measure].isna().sum())
            record[f"{measure}_nonpositive"] = int(group[measure].le(0).sum())
        records.append(record)
    return pd.DataFrame(records)


def load_var_panel(measure="rk", symbols=("ES", "CL"), directory=None):
    """Load explicit logged variance columns with dates and missing rows preserved.

    This deliberately does not drop rows, construct lags or declare a frequency.
    Resolve the session calendar before fitting a VAR.
    """
    if measure not in MEASURES:
        raise ValueError(f"measure must be one of {MEASURES}")
    if not symbols or len(set(symbols)) != len(symbols) or set(symbols) - set(SYMBOLS):
        raise ValueError(f"Choose distinct symbols from {SYMBOLS}")
    directory = Path(directory) if directory is not None else ROOT / "datasets/processed/volare"
    panel = pd.read_csv(directory / f"volare_{measure}.csv", parse_dates=["date"])
    if panel["date"].isna().any() or panel["date"].duplicated().any():
        raise ValueError("Missing or duplicate panel dates")
    if not panel["date"].is_monotonic_increasing:
        raise ValueError("Panel dates must be sorted")
    columns = [f"log_{measure}_scaled_{symbol}" for symbol in symbols]
    return panel.set_index("date")[columns].copy()
