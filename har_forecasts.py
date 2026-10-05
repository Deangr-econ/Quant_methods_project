"""Dated one-step comparisons on an explicitly chosen common-observation grid.

HAR components average log variance (not the log of average variance).
Dates are provider labels; this module does not validate exchange session timing.
"""

import numpy as np
import pandas as pd


def build_design(variance, es_returns):
    """Use information through origin t to forecast the next supplied row t+1.

    The caller deliberately supplies a complete ES/CL/GC grid. All models start
    estimation after 22 observations, so their fitted target samples are equal.
    ES returns are unadjusted percentage close-to-close log returns, aligned by
    origin date. Their possible roll contamination must be disclosed for LHAR.
    """
    if (not variance.index.is_monotonic_increasing or variance.index.has_duplicates
            or variance.empty or not np.isfinite(variance.to_numpy()).all()
            or not (variance > 0).all().all()):
        raise ValueError("Expected sorted unique dates and finite positive variances")
    logs = np.log(variance[["ES", "CL", "GC"]])
    x = pd.DataFrame(index=logs.index)
    groups = {}
    for symbol in logs:
        for lag in range(15):
            x[f"{symbol}_lag{lag + 1}"] = logs[symbol].shift(lag)
        for window, label in [(1, "d"), (5, "w"), (22, "m")]:
            x[f"{symbol}_{label}"] = logs[symbol].rolling(window).mean()
    ret = es_returns.reindex(logs.index)
    for window, label in [(1, "d"), (5, "w"), (22, "m")]:
        x[f"ES_down_{label}"] = -ret.rolling(window).mean().clip(upper=0)
    for p in (5, 15):
        groups[f"AR{p}"] = [f"ES_lag{lag}" for lag in range(1, p + 1)]
        groups[f"VAR{p}"] = [f"{s}_lag{lag}" for s in logs for lag in range(1, p + 1)]
    own = [f"ES_{h}" for h in ("d", "w", "m")]
    extra = [f"{s}_{h}" for s in ("CL", "GC") for h in ("d", "w", "m")]
    leverage = [f"ES_down_{h}" for h in ("d", "w", "m")]
    groups.update(HAR=own, HARX=own + extra, LHAR=own + leverage,
                  LHARX=own + leverage + extra)
    x["actual"] = logs.ES.shift(-1)
    x["target_date"] = pd.Series(logs.index, index=logs.index).shift(-1)
    x = x.iloc[21:-1].copy()
    if x.isna().any().any() or not np.isfinite(x.drop(columns="target_date")).all().all():
        raise ValueError("Missing/invalid design values; do not silently compress dates")
    return x, groups


def expanding_forecasts(design, groups, test_dates):
    """Fit only outcomes known by each origin; never use the target in fitting."""
    records = []
    for target in pd.DatetimeIndex(test_dates):
        row = design.loc[design.target_date.eq(target)]
        if len(row) != 1:
            raise ValueError(f"Expected exactly one forecast origin for {target}")
        origin = row.index[0]
        train = design.loc[design.target_date.le(origin)]
        if train.empty or train.target_date.max() != origin:
            raise ValueError("Training outcomes must end at the forecast origin")
        record = dict(date=target, origin_date=origin, training_end=origin,
                      n_train=len(train), actual=row.actual.iloc[0],
                      Naive=row.ES_d.iloc[0], Mean=train.actual.mean())
        for name, columns in groups.items():
            matrix = np.column_stack([np.ones(len(train)), train[columns].to_numpy()])
            prediction_row = np.r_[1.0, row[columns].iloc[0].to_numpy()]
            coefficients, _, rank, _ = np.linalg.lstsq(matrix, train.actual, rcond=None)
            if rank != matrix.shape[1]:
                raise ValueError(f"Rank-deficient {name} fit at {origin}")
            record[name] = prediction_row @ coefficients
        records.append(record)
    result = pd.DataFrame(records)
    if not np.isfinite(result[[*groups, "actual", "Naive", "Mean"]]).all().all():
        raise ValueError("Nonfinite forecast")
    return result


def accuracy_table(forecasts, models):
    metrics = []
    for name in models:
        error = forecasts.actual - forecasts[name]
        metrics.append(dict(model=name, n=len(error), MSE=float(np.mean(error ** 2)),
                            RMSE=float(np.sqrt(np.mean(error ** 2))),
                            MAE=float(np.mean(np.abs(error)))))
    return pd.DataFrame(metrics)
