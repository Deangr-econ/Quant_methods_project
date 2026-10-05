"""HAR-aligned VAR results: shared dates, downside controls and HAC(22).

Daily-only variants constrain commodity coefficients beyond lag one to zero.
Negative-return terms are predetermined exogenous controls, not new endogenous
VAR variables. Full-sample fits are descriptive; forecasts fit past targets only.
"""
import ast
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, kpss


def prepare_har_data(raw, start="2011-01-01"):
    """Reproduce reviewed HAR cell 2 exactly; report its complete-case exclusions."""
    data = raw.copy()
    data["date"] = pd.to_datetime(data["date"])
    if data.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate asset/date")
    data = data.loc[(data.date >= start) & data.symbol.isin(["ES", "CL", "C", "GC", "NG"])].sort_values(["symbol", "date"])
    if not np.isfinite(data[["rv5", "close_price"]]).all().all() or not (data[["rv5", "close_price"]] > 0).all().all():
        raise ValueError("HAR alignment requires finite positive prices and RV5")
    data["ret"] = data.groupby("symbol").close_price.transform(lambda s: np.log(s / s.shift(1)) * 100)
    data["log_rv5"] = np.log(data.rv5)
    data["rv5_scaled"] = data.rv5 * 10000
    for window, label in [(5, "w"), (22, "m")]:
        for metric in ["log_rv5", "rv5_scaled"]:
            data[f"{metric}_{label}"] = data.groupby("symbol")[metric].transform(lambda s: s.rolling(window).mean())
    fields = ["close_price", "ret", "log_rv5", "rv5", "rv5_scaled", "rv5_scaled_w", "rv5_scaled_m", "log_rv5_w", "log_rv5_m"]
    wide = data.pivot(index="date", columns="symbol", values=fields).sort_index()
    wide.columns = [f"{metric}_{symbol}" for metric, symbol in wide.columns]
    rejected = wide.loc[wide.isna().any(axis=1)].copy()
    wide = wide.dropna().copy()
    if not wide.index.is_unique or not np.isfinite(wide).all().all():
        raise ValueError("Invalid prepared HAR panel")
    return wide, rejected


def reference_har_function(path):
    """Read only the inspected HAR function; no Drive or notebook side effects."""
    notebook = json.loads(Path(path).read_text())
    namespace = dict(np=np, pd=pd, sm=sm)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        for node in ast.parse("".join(cell["source"])).body:
            if isinstance(node, ast.FunctionDef) and node.name == "fit_har_x":
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
                return namespace["fit_har_x"]
    raise ValueError("Current HAR notebook lacks fit_har_x")


def aligned_design(wide, max_lag=20, warmup=22):
    if max_lag >= warmup:
        raise ValueError("Common warm-up must cover every VAR lag and 22-row downside feature")
    symbols = ["ES", "CL", "C", "GC", "NG"]
    features = {}
    for symbol in symbols:
        for lag in range(1, max_lag + 1):
            features[f"{symbol}.l{lag}"] = wide[f"log_rv5_{symbol}"].shift(lag - 1)
        for horizon in ["d", "w", "m"]:
            column = f"log_rv5_{symbol}" if horizon == "d" else f"log_rv5_{horizon}_{symbol}"
            features[f"{symbol}_{horizon}"] = wide[column]
    for window, label in [(1, "d"), (5, "w"), (22, "m")]:
        features[f"ES_down_{label}"] = -wide.ret_ES.rolling(window).mean().clip(upper=0)
    features = pd.DataFrame(features, index=wide.index)
    targets = wide[[f"log_rv5_{s}" for s in symbols]].shift(-1)
    targets.columns = symbols
    target_dates = pd.Series(wide.index, index=wide.index).shift(-1)
    idx = features.index[warmup - 1:-1]
    features, targets, target_dates = features.loc[idx], targets.loc[idx], target_dates.loc[idx]
    if features.isna().any().any() or targets.isna().any().any():
        raise ValueError("Missing common design: do not compress dates again")
    return dict(x=features, y=targets, target_dates=target_dates, symbols=symbols)


def columns_for(spec):
    if spec["family"] == "LHAR":
        columns = [f"ES_{h}" for h in ["d", "w", "m"]]
        columns += [f"{s}_{h}" for s in spec["commodities"] for h in (["d"] if spec["daily_only"] else ["d", "w", "m"])]
    else:
        columns = [f"ES.l{lag}" for lag in range(1, spec["p"] + 1)]
        columns += [f"{s}.l{lag}" for s in spec["commodities"] for lag in range(1, (1 if spec["daily_only"] else spec["p"]) + 1)]
    if spec["downside"]:
        columns += [f"ES_down_{h}" for h in ["d", "w", "m"]]
    return columns


def system_root(coefficients, columns, symbols, p):
    k = len(symbols)
    top = np.zeros((k, k * p))
    for lag in range(1, p + 1):
        for j, symbol in enumerate(symbols):
            name = f"{symbol}.l{lag}"
            if name in columns:
                top[:, (lag - 1) * k + j] = coefficients[1 + columns.index(name)]
    companion = top if p == 1 else np.vstack([top, np.column_stack([np.eye(k * (p - 1)), np.zeros((k * (p - 1), k))])])
    return float(np.abs(np.linalg.eigvals(companion)).max())


def select_shared_lag(design, training_end, max_lag=20):
    keep = design["target_dates"] <= pd.Timestamp(training_end)
    records = []
    for p in range(1, max_lag + 1):
        spec = dict(family="VAR", p=p, commodities=["CL", "C", "GC", "NG"], downside=False, daily_only=False)
        columns = columns_for(spec)
        x = np.column_stack([np.ones(keep.sum()), design["x"].loc[keep, columns]])
        y = design["y"].loc[keep].to_numpy()
        b, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
        if rank != x.shape[1]:
            raise ValueError("Rank-deficient lag candidate")
        residual = y - x @ b
        sign, determinant = np.linalg.slogdet(residual.T @ residual / len(y))
        if sign <= 0:
            raise ValueError("Singular residual covariance")
        parameters = b.size
        records.append(dict(p=p, N=len(y), System_params=parameters,
                            AIC=determinant + 2 * parameters / len(y),
                            BIC=determinant + np.log(len(y)) * parameters / len(y)))
    table = pd.DataFrame(records).set_index("p")
    return int(table.BIC.idxmin()), table


def model_specifications(p):
    sets = {"Baseline": [], "Oil": ["CL"], "NatGas": ["NG"],
            "Energy: Oil + NG": ["CL", "NG"], "No Corn: Oil + NG + Gold": ["CL", "NG", "GC"],
            "All 4: Oil + Corn + Gold + NG": ["CL", "C", "GC", "NG"]}
    specs = {}
    for downside in [False, True]:
        for label, commodities in sets.items():
            prefix = "VAR + Downside" if downside else "VAR"
            name = f"{prefix} ({label})"
            specs[name] = dict(family="VAR", p=p, commodities=commodities,
                               downside=downside, daily_only=False)
    for label in ["All 4: Oil + Corn + Gold + NG", "No Corn: Oil + NG + Gold"]:
        specs[f"Restricted VAR + Downside ({label}; Daily Only)"] = dict(
            family="VAR", p=p, commodities=sets[label], downside=True, daily_only=True)
    for label in ["Baseline", "No Corn: Oil + NG + Gold", "All 4: Oil + Corn + Gold + NG"]:
        specs[f"LHAR ({label})"] = dict(family="LHAR", p=0, commodities=sets[label],
                                        downside=True, daily_only=False)
    for label in ["All 4: Oil + Corn + Gold + NG", "No Corn: Oil + NG + Gold"]:
        specs[f"LHAR ({label}; Daily Only)"] = dict(family="LHAR", p=0, commodities=sets[label],
                                                  downside=True, daily_only=True)
    return specs


def fit_models(design, specs, hac_lags=22, mask=None):
    if mask is None:
        mask = np.ones(len(design["x"]), dtype=bool)
    fits, summaries = {}, []
    for name, spec in specs.items():
        columns = columns_for(spec)
        x = sm.add_constant(design["x"].loc[mask, columns], has_constant="add")
        y = design["y"].loc[mask, "ES"]
        fit = sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags, "use_correction": False})
        symbols = ["ES", *spec["commodities"]]
        root = np.nan
        if spec["family"] == "VAR":
            b = np.linalg.lstsq(x, design["y"].loc[mask, symbols], rcond=None)[0]
            root = system_root(b, columns, symbols, spec["p"])
        fits[name] = fit
        summaries.append({"Model": name, "N": int(fit.nobs), "Params (k)": len(fit.params),
            "System params": len(fit.params) * len(symbols) if spec["family"] == "VAR" else len(fit.params),
            "Lag p": spec["p"], "R²": fit.rsquared, "Adj. R²": fit.rsquared_adj,
            "AIC": fit.aic, "BIC": fit.bic, "F-Stat": fit.fvalue, "Prob(F-Stat)": fit.f_pvalue,
            "Log-Likelihood": fit.llf, "Max root": root})
    return fits, pd.DataFrame(summaries).set_index("Model")


def expanding_forecasts(design, specs, training_end):
    xdf, ydf, dates = design["x"], design["y"], design["target_dates"]
    records = []
    for name, spec in specs.items():
        columns = columns_for(spec)
        symbols = ["ES", *spec["commodities"]] if spec["family"] == "VAR" else ["ES"]
        x = np.column_stack([np.ones(len(xdf)), xdf[columns].to_numpy()])
        y = ydf[symbols].to_numpy()
        for i in np.flatnonzero((dates > pd.Timestamp(training_end)).to_numpy()):
            origin, target = xdf.index[i], dates.iloc[i]
            train = (dates <= origin).to_numpy()
            last = float(xdf.iloc[i]["ES.l1"])
            predicted, variance, smear, root = last, np.exp(last), 1.0, np.nan
            status, detail = "ok", ""
            try:
                b, _, rank, _ = np.linalg.lstsq(x[train], y[train], rcond=None)
                if rank != x.shape[1]:
                    raise ValueError("Rank-deficient fit")
                if spec["family"] == "VAR":
                    root = system_root(b, columns, symbols, spec["p"])
                    if root >= 1:
                        raise ValueError("Unstable conditional VAR dynamics")
                value = float(x[i] @ b[:, 0])
                residual = y[train, 0] - x[train] @ b[:, 0]
                factor = float(np.exp(residual).mean())
                v = np.exp(value) * factor
                if not np.isfinite(value) or not np.isfinite(v) or v <= 0:
                    raise ValueError("Invalid forecast")
                predicted, variance, smear = value, v, factor
            except (ValueError, np.linalg.LinAlgError) as error:
                status, detail = "fallback_persistence", str(error)
            records.append(dict(model=name, date=target, origin_date=origin,
                training_end=dates.loc[train].max(), n_train=int(train.sum()),
                actual_log=float(y[i, 0]), predicted_log=predicted,
                actual_variance=np.exp(y[i, 0]), predicted_variance=variance,
                smearing=smear, root=root, status=status, detail=detail))
    return pd.DataFrame(records)


def forecast_metrics(forecasts):
    records = []
    for name, frame in forecasts.groupby("model", sort=False):
        error = frame.actual_log - frame.predicted_log
        ratio = frame.actual_variance / frame.predicted_variance
        records.append(dict(Model=name, N=len(frame), Fallbacks=int(frame.status.ne("ok").sum()),
            MSE=np.mean(error**2), RMSE=np.sqrt(np.mean(error**2)), MAE=np.mean(np.abs(error)),
            Variance_MSE=np.mean((frame.actual_variance - frame.predicted_variance)**2),
            QLIKE=np.mean(ratio - np.log(ratio) - 1)))
    return pd.DataFrame(records).set_index("Model")


def stationarity_table(wide, training_end):
    records = []
    for symbol in ["ES", "CL", "C", "GC", "NG"]:
        s = wide.loc[:training_end, f"log_rv5_{symbol}"]
        a = adfuller(s, regression="c", autolag="AIC", result_object=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            k = kpss(s, regression="c", nlags="auto", result_object=False)
        bound = "<=" if k[1] == .01 else ">=" if k[1] == .1 else ""
        agree = a[1] < .05 and k[1] > .05
        records.append(dict(Symbol=symbol, N=len(s), ADF_stat=a[0], ADF_p=a[1],
            KPSS_stat=k[0], KPSS_p=f"{bound}{k[1]:.4f}",
            Interpretation="Both support stationarity" if agree else "Investigate persistence/conflicting tests",
            Warning="; ".join(str(w.message) for w in caught)))
    return pd.DataFrame(records).set_index("Symbol")


def plot_residual_diagnostics(fit, model_name, lags=30, bins=70):
    import matplotlib.pyplot as plt
    residual = fit.resid
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes[0, 0].plot(residual.index, residual, lw=.8, alpha=.85)
    axes[0, 0].axhline(0, color="black", ls="--", lw=.8)
    axes[0, 0].set(title=f"Residuals over time: {model_name}", xlabel="Forecast origin date", ylabel="ES residual")
    axes[0, 1].hist(residual, bins=bins, density=True, alpha=.55, color="#2ca02c")
    mu, sigma = stats.norm.fit(residual)
    grid = np.linspace(*axes[0, 1].get_xlim(), 500)
    axes[0, 1].plot(grid, stats.norm.pdf(grid, mu, sigma), "r--", label="Fitted normal reference")
    axes[0, 1].set_title(f"Density: kurtosis {stats.kurtosis(residual, fisher=False):.2f}, skew {stats.skew(residual):.2f}")
    axes[0, 1].legend()
    sm.qqplot(residual, line="45", fit=True, ax=axes[1, 0], alpha=.5)
    axes[1, 0].set_title("Normal Q–Q plot")
    sm.graphics.tsa.plot_acf(residual, lags=lags, ax=axes[1, 1])
    axes[1, 1].set_title(f"Residual ACF: {lags} lags")
    for ax in axes.flat:
        ax.grid(True, alpha=.25)
    fig.tight_layout()
    return fig
