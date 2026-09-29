"""Non-destructive review helpers; a weekday grid is not an exchange calendar."""

import pandas as pd
from pandas.tseries.holiday import GoodFriday


def weekday_calendar_audit(data, symbols=("ES", "CL")):
    """Expose joint omissions as well as mismatches, retaining observed weekends.

    Holiday labels are calendar-date candidates only. They neither assert an
    exchange closure nor approve excluding a row from a forecasting sample.
    """
    selected = data.loc[data.symbol.isin(symbols)]
    first, last = selected.date.min(), selected.date.max()
    dates = pd.bdate_range(first, last).union(pd.DatetimeIndex(selected.date.unique())).sort_values()
    result = pd.DataFrame(index=dates.rename("date"))
    for symbol in symbols:
        observed = selected.loc[selected.symbol.eq(symbol), "date"]
        if observed.empty:
            raise ValueError(f"No source observations for {symbol}")
        result[f"{symbol}_observed"] = result.index.isin(observed)
        result[f"{symbol}_outside_coverage"] = (dates < observed.min()) | (dates > observed.max())
    available = result[[f"{s}_observed" for s in symbols]]
    result["observed_count"] = available.sum(axis=1)
    result["candidate_holiday"] = ""
    good_fridays = GoodFriday.dates(first, last)
    result.loc[result.index.isin(good_fridays), "candidate_holiday"] = "Good Friday"
    # Include neighbouring years so an observed New Year can fall in December.
    for year in range(first.year - 1, last.year + 2):
        for month, day, name in [(1, 1, "New Year"), (12, 25, "Christmas")]:
            actual = pd.Timestamp(year, month, day)
            observed = actual + pd.Timedelta(days={5: -1, 6: 1}.get(actual.weekday(), 0))
            result.loc[result.index.isin([actual, observed]), "candidate_holiday"] = name
    result["calendar_verified"] = False
    return result.reset_index()


def reconcile_reviews(flags, ledger, source_sha256):
    """Join annotations, rejecting stale or ambiguous decisions; never clean data."""
    required = {"date", "symbol", "flags", "decision", "evidence", "reason",
                "reviewer", "reviewed_at", "source_sha256"}
    if required - set(ledger.columns):
        raise ValueError(f"Missing review columns: {sorted(required - set(ledger.columns))}")
    ledger = ledger.copy()
    ledger["date"] = pd.to_datetime(ledger["date"], format="%Y-%m-%d", errors="raise")
    if ledger[list(required)].isna().any().any() or ledger[list(required)].eq("").any().any():
        raise ValueError("Review fields must be populated")
    if ledger.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate review keys")
    if not ledger.source_sha256.eq(source_sha256).all():
        raise ValueError("Review source hash differs; reassess against the new snapshot")
    keys = ["date", "symbol", "flags"]
    matched = ledger.merge(flags[keys], on=keys, how="left", indicator=True, validate="one_to_one")
    if not matched["_merge"].eq("both").all():
        raise ValueError("Review keys/flags no longer match the screening output")
    result = flags.drop(columns="status").merge(ledger, on=keys, how="left", validate="one_to_one")
    result["decision"] = result["decision"].fillna("unreviewed")
    return result
