"""Return decomposition and explicitly approximate roll candidates."""

import numpy as np
import pandas as pd


def equity_return_audit(es):
    if es.index.has_duplicates or not es.index.is_monotonic_increasing:
        raise ValueError("ES dates must be unique and sorted")
    prices = es[["open_price", "close_price"]]
    if not np.isfinite(prices).all().all() or not prices.gt(0).all().all():
        raise ValueError("ES open/close prices must be positive and finite")
    result = prices.copy()
    result["previous_es_date"] = pd.Series(es.index, index=es.index).shift()
    previous = es.close_price.shift()
    result["close_to_close"] = 100 * np.log(es.close_price / previous)
    result["open_to_close"] = 100 * np.log(es.close_price / es.open_price)
    result["opening_gap"] = 100 * np.log(es.open_price / previous)
    np.testing.assert_allclose(result.close_to_close.iloc[1:],
                               (result.open_to_close + result.opening_gap).iloc[1:], atol=1e-10)
    result["roll_candidate"] = False
    result["roll_neighbourhood"] = False
    result["calendar_verified"] = False
    schedule = []
    for year in range(es.index.min().year, es.index.max().year + 1):
        for month in (3, 6, 9, 12):
            first = pd.Timestamp(year, month, 1)
            friday = first + pd.Timedelta(days=(4 - first.weekday()) % 7 + 14)
            # Kibot's inclusive counting: 7 through March 2022; 5 from June 2022.
            # Weekdays approximate trading days; do NOT assert historical holiday accuracy.
            count = 7 if friday < pd.Timestamp("2022-06-01") else 5
            day = friday - pd.offsets.BDay(count - 1)
            if day < es.index.min() or day > es.index.max():
                continue
            schedule.append(dict(expiration_candidate=friday, roll_candidate=day,
                                 inclusive_count=count, calendar_verified=False))
            pos = es.index.searchsorted(day)
            if day in es.index:
                result.loc[day, "roll_candidate"] = True
            result.iloc[max(0, pos - 1):min(len(es), pos + 2),
                        result.columns.get_loc("roll_neighbourhood")] = True
    result["neighbourhood_open_close"] = result.close_to_close.where(
        ~result.roll_neighbourhood, result.open_to_close)
    return result, pd.DataFrame(schedule)


def add_return_controls(groups):
    result = {k: list(v) for k, v in groups.items()}
    terms = [f"ES_down_{h}" for h in ("d", "w", "m")]
    for p in (5, 15):
        result[f"AR{p}_returns"] = result[f"AR{p}"] + terms
    return result


def exposed_design_rows(design, source_index, issue_dates, suspect_target_dates=()):
    """Mask design rows exposed to known suspect inputs without rebuilding lags.

    A uniform 22-row window is deliberately conservative for comparisons with
    shorter lags. Target exclusions are explicit and separate from input issues.
    """
    issue = pd.Series(source_index.isin(pd.to_datetime(issue_dates)), index=source_index)
    exposed = issue.rolling(22, min_periods=1).max().astype(bool).reindex(design.index)
    if exposed.isna().any():
        raise ValueError("Design origins must belong to the source grid")
    return exposed | design.target_date.isin(pd.to_datetime(suspect_target_dates))


def paired_block_intervals(actual, baseline, candidate, block=20, draws=2000, seed=20261004):
    """Descriptive percentile intervals for fixed paired forecast losses.

    Circular blocks retain within-block order. No model refits, null centering,
    nested-model adjustment or multiplicity correction is performed.
    """
    losses = np.column_stack([(np.asarray(actual) - baseline) ** 2,
                              (np.asarray(actual) - candidate) ** 2])
    n = len(losses)
    if n < block or block < 1 or not np.isfinite(losses).all() or losses[:, 0].mean() <= 0:
        raise ValueError("Need finite paired losses and a valid block length")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(draws, int(np.ceil(n / block))))
    indices = ((starts[:, :, None] + np.arange(block)) % n).reshape(draws, -1)[:, :n]
    means = losses[indices].mean(axis=1)
    gains = 100 * (1 - means[:, 1] / means[:, 0])
    lower, upper = np.quantile(gains, [.025, .975])
    return dict(block=block, draws=draws, seed=seed,
                gain_pct=float(100 * (1 - losses[:, 1].mean() / losses[:, 0].mean())),
                lower_pct=float(lower), upper_pct=float(upper))
