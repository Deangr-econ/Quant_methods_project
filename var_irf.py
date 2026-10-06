"""Conditional generalized VAR-X responses and exploratory joint-HAC bands.

The innovation is one residual standard deviation of log variance. Predetermined
downside controls follow an identical path in the shocked and baseline system.
Bands simulate joint uncertainty in OLS coefficients AND residual covariance;
they are pointwise, asymptotic and conditional on stable/positive-definite draws.
They are not identified causal effects, forecast intervals or bootstrap bands.
"""
import numpy as np
import pandas as pd

from var_har_notebook import columns_for, system_root


def lag_matrices(coefficients, columns, symbols, p):
    """Convert named equation-major regressors to A_l[response, impulse]."""
    matrices = np.zeros((p, len(symbols), len(symbols)))
    for lag in range(1, p + 1):
        for j, symbol in enumerate(symbols):
            name = f"{symbol}.l{lag}"
            if name in columns:
                matrices[lag - 1, :, j] = coefficients[1 + columns.index(name)]
    return matrices


def moving_average(matrices, horizon):
    k = matrices.shape[1]
    phi = np.zeros((horizon + 1, k, k))
    phi[0] = np.eye(k)
    for h in range(1, horizon + 1):
        for lag in range(1, min(h, len(matrices)) + 1):
            phi[h] += matrices[lag - 1] @ phi[h - lag]
    return phi


def generalized_responses(matrices, sigma, horizon):
    """Pesaran-Shin one-standard-deviation responses: Phi_h Sigma / sd_j."""
    if np.linalg.eigvalsh(sigma).min() <= 0:
        raise ValueError("Innovation covariance must be positive definite")
    return moving_average(matrices, horizon) @ (sigma / np.sqrt(np.diag(sigma))[None, :])


def joint_hac_covariance(x, residual, sigma, nlags):
    """Bartlett HAC of stacked OLS and residual-second-moment influences.

Coefficient vector is B.flatten(order='F'); Sigma uses its lower triangle.
The coefficient block equals uncorrected Newey-West OLS covariance. The
second-moment block and cross block account for innovation-covariance uncertainty.
OLS orthogonality makes the sample second-moment derivative with respect to B
zero. Weak dependence and the usual stationary asymptotics are required.
"""
    n, k = residual.shape
    if not 0 <= nlags < n:
        raise ValueError("HAC lag length must be between zero and N-1")
    pinv = np.linalg.pinv(x)
    coefficient_influence = np.concatenate([pinv.T * residual[:, j:j+1] for j in range(k)], axis=1)
    lower = np.tril_indices(k)
    sigma_influence = (residual[:, lower[0]] * residual[:, lower[1]] - sigma[lower]) / n
    influence = np.column_stack([coefficient_influence, sigma_influence])
    covariance = influence.T @ influence
    for lag in range(1, nlags + 1):
        cross = influence[lag:].T @ influence[:-lag]
        covariance += (1 - lag / (nlags + 1)) * (cross + cross.T)
    return (covariance + covariance.T) / 2


def estimate_irf(design, spec, training_end, horizon=20, hac_lags=22, draws=2000, seed=20261005):
    """Fit initial history only and return curves plus reproducible band metadata."""
    if spec['family'] != 'VAR':
        raise ValueError("IRFs require a VAR specification")
    if horizon < 0 or draws < 100:
        raise ValueError("Use a nonnegative horizon and at least 100 simulations")
    keep = design['target_dates'] <= pd.Timestamp(training_end)
    columns = columns_for(spec)
    symbols = ['ES', *spec['commodities']]
    x = np.column_stack([np.ones(keep.sum()), design['x'].loc[keep, columns]])
    y = design['y'].loc[keep, symbols].to_numpy()
    b, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank != x.shape[1]:
        raise ValueError("Rank-deficient IRF design")
    residual = y - x @ b
    sigma = residual.T @ residual / len(y)
    root = system_root(b, columns, symbols, spec['p'])
    if root >= 1:
        raise ValueError("Unstable point-estimate dynamics: do not report a fading stable IRF")
    matrices = lag_matrices(b, columns, symbols, spec['p'])
    point = generalized_responses(matrices, sigma, horizon)
    covariance = joint_hac_covariance(x, residual, sigma, hac_lags)
    values, vectors = np.linalg.eigh(covariance)
    # Bartlett HAC is PSD; permit floating-point roundoff, never a material repair.
    if values.min() < -1e-9 * max(values.max(), 1):
        raise ValueError("Joint HAC covariance has materially negative eigenvalues")
    factor = vectors * np.sqrt(np.maximum(values, 0))[None, :]
    k, q = len(symbols), x.shape[1]
    lower = np.tril_indices(k)
    center = np.r_[b.ravel(order='F'), sigma[lower]]
    simulated = center + np.random.default_rng(seed).standard_normal((draws, len(center))) @ factor.T
    accepted, nonpositive, unstable = [], 0, 0
    for sample in simulated:
        sample_b = sample[:q*k].reshape((q, k), order='F')
        sample_sigma = np.zeros((k, k))
        sample_sigma[lower] = sample[q*k:]
        sample_sigma += np.tril(sample_sigma, -1).T
        if np.linalg.eigvalsh(sample_sigma).min() <= 0:
            nonpositive += 1
            continue
        if system_root(sample_b, columns, symbols, spec['p']) >= 1:
            unstable += 1
            continue
        accepted.append(generalized_responses(lag_matrices(sample_b, columns, symbols, spec['p']), sample_sigma, horizon))
    if len(accepted) < 100:
        raise ValueError("Too few admissible simulations for IRF bands")
    low, high = np.quantile(np.asarray(accepted), [0.025, 0.975], axis=0)
    records = []
    for j, impulse in enumerate(symbols):
        for h in range(horizon + 1):
            d, lo, hi = point[h, 0, j], low[h, 0, j], high[h, 0, j]
            records.append(dict(impulse=impulse, response='ES', horizon=h,
                log_response=d, log_lower=lo, log_upper=hi,
                variance_pct=100*np.expm1(d), variance_lower=100*np.expm1(lo), variance_upper=100*np.expm1(hi),
                volatility_pct=100*np.expm1(d/2), volatility_lower=100*np.expm1(lo/2), volatility_upper=100*np.expm1(hi/2)))
    metadata = dict(training_end=str(pd.Timestamp(training_end).date()), n=int(keep.sum()),
        first_target=str(design['target_dates'][keep].min().date()),
        last_target=str(design['target_dates'][keep].max().date()),
        p=int(spec['p']), root=root, horizon=horizon, hac_lags=hac_lags,
        seed=seed, draws_requested=draws, draws_accepted=len(accepted),
        rejected_nonpositive_covariance=nonpositive, rejected_unstable=unstable,
        interval='95% pointwise joint-HAC normal parameter simulation, conditional on admissible draws',
        shock='One residual standard deviation of commodity log RV5, with contemporaneously correlated innovations',
        controls='Identical predetermined ES-downside-control path in shocked and baseline systems',
        time_unit='Next retained all-five-market observation, not necessarily next trading/calendar day')
    return pd.DataFrame(records), metadata


def plot_commodity_irfs(curves):
    import matplotlib.pyplot as plt
    names = {'CL': 'Oil', 'C': 'Corn', 'GC': 'Gold', 'NG': 'Natural gas'}
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for ax, (symbol, label) in zip(axes.flat, names.items()):
        frame = curves.loc[curves.impulse.eq(symbol)].sort_values('horizon')
        ax.fill_between(frame.horizon, frame.variance_lower, frame.variance_upper, color='#235789', alpha=.18, label='Exploratory 95% pointwise band')
        ax.plot(frame.horizon, frame.variance_pct, color='#235789', lw=2, label='Estimated response')
        ax.axhline(0, color='black', lw=.8, ls='--')
        ax.set_title(f'{label} variance innovation → ES variance', loc='left')
        ax.set_ylabel('ES variance change (%)')
        ax.set_xlabel('Retained observations after innovation (0 = contemporaneous)')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Conditional generalized IRFs: initial-training five-market VAR(5) + downside controls', fontsize=12)
    fig.tight_layout()
    return fig
