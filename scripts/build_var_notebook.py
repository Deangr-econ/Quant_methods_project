"""Create the HAR-aligned, portable Python VAR results notebook."""
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(source):
    cells.append(dict(cell_type="markdown", metadata={}, id=f"var-{len(cells):02d}", source=textwrap.dedent(source).strip() + "\n"))


def code(source):
    cells.append(dict(cell_type="code", metadata={}, id=f"var-{len(cells):02d}", execution_count=None,
                      outputs=[], source=textwrap.dedent(source).strip() + "\n"))


md("""
# VAR results aligned with the asymmetric HAR

**Research question:** does oil, corn, gold and natural-gas variance information
improve forecasts of ES realised variance beyond equity history and the same
downside-return information used by asymmetric HAR?

This notebook mirrors `HAR_QTFE.ipynb`: RV5 from 2011, all five markets, the same
ES downside terms, HAC(22), fit-comparison tables, a corn/no-corn matrix,
coefficient results and a four-panel residual plot. All fitted comparison tables
use identical rows. A separate section evaluates sequential forecasts on shared
dates and recomputes LHAR controls in this notebook.

**Definitions:** the outcome is `log(rv5_ES)`, a log **variance**, as in the current
HAR code. No square root or annualisation is introduced. Volatility is its square
root. VAR uses individual lags; HAR uses daily/weekly/monthly averages.

Full-sample results are descriptive. The evaluation period has already been
examined. Provider session timing and contract/quote issues remain unresolved.
""")
code("""
%matplotlib inline
from pathlib import Path
import hashlib, json, platform, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown, HTML
import statsmodels
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'config/var_har_notebook.json').exists())
sys.path.insert(0, str(ROOT))
from var_har_notebook import (prepare_har_data, reference_har_function, aligned_design,
    select_shared_lag, model_specifications, fit_models, expanding_forecasts,
    forecast_metrics, stationarity_table, plot_residual_diagnostics, columns_for)
from var_irf import estimate_irf, plot_commodity_irfs
cfg = json.loads((ROOT / 'config/var_har_notebook.json').read_text())
OUTPUT = ROOT / 'reports/var_har_notebook/generated'
OUTPUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
source_path = ROOT / cfg['source']
source_hash = sha(source_path)
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_colwidth', 70)
plt.rcParams.update({'figure.dpi': 110, 'axes.spines.top': False, 'axes.spines.right': False})
def show_table(table):
    formats = {c: ('{:.3e}' if c in ['Prob(F-Stat)', 'p (HAC)', 'Variance_MSE'] else '{:.4f}')
               for c in table.select_dtypes(include='number').columns if c not in ['N', 'Params (k)', 'System params', 'Lag p', 'Fallbacks']}
    display(HTML(table.to_html(formatters={c: (lambda value, pattern=pattern: pattern.format(value))
        for c, pattern in formats.items()}, na_rep='—', border=0)))
print('Python', platform.python_version(), '| statsmodels', statsmodels.__version__)
print('Local source:', source_path.name, '| no API key or private Drive required')
""")
md("""
## 1. Match the HAR data and dates

The reviewed HAR preparation computes returns and 5/22-observation variance
windows on each asset's source dates, then matches all five markets and removes
incomplete rows. We deliberately reproduce that policy for compatibility;
it is not a verified exchange calendar. The first 21 retained origins are then
used to warm up the downside-return windows. Every regression shares the same
remaining origin/target pairs, including baseline models without commodities.

ES returns are percentage close-to-close log returns. Downside terms equal
`abs(min(mean(return over 1/5/22 retained rows), 0))`: the negative part is taken
**after averaging**, exactly as in HAR. Returns remain unadjusted for rolls.
""")
code("""
raw = pd.read_csv(source_path, float_precision='round_trip')
coverage = raw.assign(date=pd.to_datetime(raw['date'])).pivot(index='date', columns='symbol', values='rv5')[cfg['symbols']].sort_index()
gold_only = coverage['GC'].notna() & coverage.drop(columns='GC').isna().all(axis=1)
coverage_rows = []
for label, period in [('2009–2010', coverage.loc[:'2010-12-31']), ('2011 onward', coverage.loc['2011-01-01':])]:
    coverage_rows.append({'Period': label, 'Union dates': len(period), 'All-five RV5 dates': int(period.notna().all(axis=1).sum()),
        'Incomplete dates': int(period.isna().any(axis=1).sum()), 'Gold-only RV5 dates': int(gold_only.reindex(period.index).sum())})
coverage_table = pd.DataFrame(coverage_rows).set_index('Period')
display(coverage_table)
coverage_table.to_csv(OUTPUT / 'raw_rv5_calendar_coverage.csv')
coverage.isna().loc[coverage.isna().any(axis=1)].to_csv(OUTPUT / 'raw_rv5_missing_markets.csv')
wide, excluded = prepare_har_data(raw, cfg['sample_start'])
design = aligned_design(wide, cfg['max_lag'], cfg['common_warmup'])
training_mask = design['target_dates'] <= pd.Timestamp(cfg['training_end'])
test_dates = pd.DatetimeIndex(design['target_dates'][~training_mask])
sample_table = pd.DataFrame([
    ['Prepared all-five HAR dates', len(wide), wide.index.min(), wide.index.max()],
    ['Common descriptive regression targets', len(design['y']), design['target_dates'].min(), design['target_dates'].max()],
    ['Initial fitted training targets', int(training_mask.sum()), design['target_dates'][training_mask].min(), design['target_dates'][training_mask].max()],
    ['Shared evaluation targets', len(test_dates), test_dates.min(), test_dates.max()],
], columns=['Sample', 'N', 'First target/date', 'Last target/date']).set_index('Sample')
display(sample_table)
print('Dates rejected by the HAR preparation, including initial rolling warm-up:', len(excluded))
excluded.to_csv(OUTPUT / 'har_preparation_exclusions.csv')
sample_table.to_csv(OUTPUT / 'sample_counts.csv')
print(f'Initial fitted split: {100*training_mask.mean():.2f}% training / {100*(1-training_mask.mean()):.2f}% evaluation; fixed 2023-07-12 cutoff.')
""")
code("""
fig, axes = plt.subplots(5, 1, figsize=(12, 10), sharex=True)
for ax, symbol in zip(axes, cfg['symbols']):
    ax.plot(wide.index, wide[f'log_rv5_{symbol}'], lw=.65)
    ax.axvline(pd.Timestamp(cfg['training_end']), color='black', ls='--', alpha=.65)
    ax.set_title(f'{symbol}: log RV5', loc='left')
    ax.grid(alpha=.25)
axes[-1].set_xlabel('Retained provider date; dashed line is initial training cutoff')
fig.tight_layout(); plt.show()
""")
md("""
## 2. Check stationarity and choose one shared lag order

Tests and lag selection use initial history only. ADF/KPSS disagreement prompts
investigation; it is not labelled a structural break. The five-market plain VAR's
initial-training BIC selects one order from 1–20, held fixed across every VAR
comparison and forecast refit. Candidate models use identical training outcomes.
""")
code("""
stationarity = stationarity_table(wide, cfg['training_end'])
show_table(stationarity.drop(columns='Warning'))
for text in stationarity.Warning.unique():
    if text: print('KPSS warning:', text)
p, lag_table = select_shared_lag(design, cfg['training_end'], cfg['max_lag'])
show_table(lag_table)
print('Shared training-selected BIC lag:', p)
specs = model_specifications(p)
stationarity.to_csv(OUTPUT / 'training_stationarity.csv')
lag_table.to_csv(OUTPUT / 'initial_lag_selection.csv')
""")
md("""
## 3. Reproduce the asymmetric HAR reference

These are the current notebook's original full-sample fits, reconstructed from
its reviewed `fit_har_x` definition. They verify data/method alignment. Original
HAR and LHAR have different warm-up samples; compare their R² descriptively,
not their raw AIC/BIC across unequal samples. Below, the aligned VAR and LHAR
tables instead use **the same regression rows** for every model.
""")
code("""
har_reference = reference_har_function(ROOT / cfg['har_reference'])
reference_rows = []
for downside in [False, True]:
    for label, assets in [('Baseline', []), ('Oil', ['CL']), ('NatGas', ['NG']), ('Energy', ['CL', 'NG']), ('No Corn', ['CL', 'NG', 'GC'])]:
        fit = har_reference(wide, exog_symbols=assets, include_exog_horizons=True,
                            include_leverage=downside, hac_lags=cfg['hac_lags'])
        reference_rows.append({'Model': ('LHAR' if downside else 'HAR') + f' ({label})',
                               'N': int(fit.nobs), 'R²': fit.rsquared, 'AIC': fit.aic, 'BIC': fit.bic})
reference_table = pd.DataFrame(reference_rows).set_index('Model')
show_table(reference_table)
reference_table.to_csv(OUTPUT / 'current_har_reference.csv')
""")
md("""
## 4. Plain VAR versus VAR with the same downside information

Each system includes ES and the indicated commodities. The baseline is the
one-variable AR analogue. Downside versions add HAR's three predetermined ES
return terms to every equation; they are **VARs with exogenous downside controls**,
not HAR models and not systems treating returns as another endogenous market.

The table mirrors HAR's R², adjusted R², AIC/BIC, robust F statistic and
log-likelihood layout. These statistics refer to the **ES equation** on identical
full-sample target rows. System parameter counts are separate. AIC/BIC here are
Gaussian ES-equation criteria, whereas the earlier lag search used system criteria.
HAC(22) affects reported inference, not OLS coefficient estimates or forecasts.
""")
code("""
fits, summary = fit_models(design, specs, cfg['hac_lags'])
sets_in_first_table = ['Baseline', 'Oil', 'NatGas', 'Energy: Oil + NG', 'No Corn: Oil + NG + Gold']
first_names = [f'{prefix} ({label})' for prefix in ['VAR', 'VAR + Downside'] for label in sets_in_first_table]
summary_columns = ['N', 'Lag p', 'Params (k)', 'R²', 'Adj. R²', 'AIC', 'BIC', 'F-Stat', 'Prob(F-Stat)', 'Log-Likelihood']
show_table(summary.loc[first_names, summary_columns])
summary.to_csv(OUTPUT / 'common_sample_insample_results.csv')
""")
md("""
## 5. With corn / without corn: full memory and daily-only commodities

This mirrors the second asymmetric HAR results matrix. **Full memory** means
all selected VAR lags for every market. **Daily only** sets commodity coefficients
after lag one to zero, while retaining all ES lags and the same downside controls.
Those rows are restricted VAR systems. HAR's full d/w/m averages and VAR's full
lag history are different representations of memory, not identical regressors.
""")
code("""
corn_names = ['VAR + Downside (Baseline)',
    'VAR + Downside (All 4: Oil + Corn + Gold + NG)',
    'Restricted VAR + Downside (All 4: Oil + Corn + Gold + NG; Daily Only)',
    'VAR + Downside (No Corn: Oil + NG + Gold)',
    'Restricted VAR + Downside (No Corn: Oil + NG + Gold; Daily Only)']
show_table(summary.loc[corn_names, summary_columns + ['System params', 'Max root']])
lhar_names = ['LHAR (Baseline)', 'LHAR (All 4: Oil + Corn + Gold + NG)',
    'LHAR (All 4: Oil + Corn + Gold + NG; Daily Only)', 'LHAR (No Corn: Oil + NG + Gold)',
    'LHAR (No Corn: Oil + NG + Gold; Daily Only)']
display(Markdown('**Asymmetric HAR on exactly the same target rows, for reference:**'))
show_table(summary.loc[lhar_names, summary_columns])
""")
md("""
## 6. Coefficients and joint commodity tests

As in HAR, show a detailed equity-equation summary. This is the downside-augmented
VAR without corn; all-four-market results remain in the comparison tables.
Joint HAC tests use initial-history outcomes and condition on ES history and
the same downside signals. They test predictive associations, not economic causality
or out-of-sample gains. Displayed p-values are exploratory and unadjusted.
""")
code("""
selected_name = 'VAR + Downside (No Corn: Oil + NG + Gold)'
print(fits[selected_name].summary())
training_fits, training_summary = fit_models(design, specs, cfg['hac_lags'], training_mask)
joint_rows = []
for name in corn_names:
    fit = training_fits[name]
    for group, markets in [('Oil', ['CL']), ('Natural gas', ['NG']), ('Gold', ['GC']), ('Corn', ['C']), ('All included commodities', specs[name]['commodities'])]:
        indices = [i for i, col in enumerate(fit.params.index) if any(col.startswith(s + '.l') for s in markets)]
        if not indices: continue
        restriction = np.eye(len(fit.params))[indices]
        test = fit.wald_test(restriction, scalar=True)
        joint_rows.append({'Model': name, 'Restriction': group, 'N': int(fit.nobs),
                           'Lags tested': len(indices), 'Wald statistic': float(test.statistic), 'p (HAC)': float(test.pvalue)})
joint_table = pd.DataFrame(joint_rows).set_index(['Model', 'Restriction'])
show_table(joint_table)
joint_table.to_csv(OUTPUT / 'training_joint_hac_tests.csv')
""")
md("""
## 7. Residual diagnostics in the HAR layout

The same four panels show residuals over time, density against a normal reference,
Q–Q plot and ACF. Residual dates are taken directly from each fitted design,
avoiding a date shift when return windows remove initial rows. The additional
training-only tests report remaining serial dependence and ARCH; robust errors
do not resolve those dynamics. Conditional root stability does not model the
return-control process or prove overall specification adequacy.
Ljung–Box is an unadjusted ES residual screening statistic (`model_df=0`),
not a calibrated multivariate VAR whiteness test. Its p-values and the residual
ARCH test are exploratory diagnostics; do not claim a model is adequate because
one test passes.
""")
code("""
plot_residual_diagnostics(fits[selected_name], selected_name)
plt.show()
diagnostic_rows = []
for name in corn_names:
    fit = training_fits[name]
    lb = acorr_ljungbox(fit.resid, lags=[30], model_df=0, return_df=True).iloc[0]
    arch = het_arch(fit.resid, nlags=5, ddof=len(fit.params))
    diagnostic_rows.append({'Model': name, 'N': int(fit.nobs),
        'ES Ljung-Box p (30; unadjusted)': lb.lb_pvalue, 'ES ARCH p (5 lags)': arch[1],
        'Conditional max root': training_summary.loc[name, 'Max root']})
diagnostics = pd.DataFrame(diagnostic_rows).set_index('Model')
show_table(diagnostics)
diagnostics.to_csv(OUTPUT / 'training_es_diagnostics.csv')
""")
md("""
## 8. Impulse response curves: commodity variance innovations → ES

An **impulse response function (IRF)** traces how an unexpected change today
propagates through the fitted lag system. Here the shock is **one residual
standard deviation of commodity log RV5**, not a price jump or a negative return.
The full five-market downside VAR is estimated on initial history only (through
12 July 2023), with the same training-selected five lags. No evaluation outcomes
enter this fit. The four panels cover oil, corn, gold and natural gas.

We use [Pesaran–Shin generalized responses](https://www.sciencedirect.com/science/article/pii/S0165176597002140):
`GIRF(h, j) = Phi(h) @ Sigma[:, j] / sqrt(Sigma[j, j])`.
They are invariant to market ordering, unlike default Cholesky responses.
Innovations are correlated: **the horizon-zero response is contemporaneous
co-movement**, not proof that a commodity causes an equity shock. A positive
curve means higher implied ES variance relative to the unshocked path; fading
towards zero means the association dissipates. The horizon counts retained
all-five observations, not necessarily consecutive ES trading days.

Downside-return controls follow the **same fixed path** in both scenarios.
These are conditional VAR-X responses; they do not model feedback through future
returns or constitute a nonlinear leverage-shock experiment. A log response `d`
becomes `100*(exp(d)-1)` percent implied variance, and `100*(exp(d/2)-1)` percent
volatility. These back-transformations describe the log-model path, not a
separately estimated arithmetic conditional-variance mean.

The shading is an **exploratory 95% pointwise band** from 2,000 seeded joint
normal parameter simulations using Bartlett HAC(22) for both OLS coefficients
and residual covariance (including their cross covariance). This accommodates
weak residual dependence and heteroskedasticity asymptotically; it does not cure
misspecification, uncertain stationarity or breaks. Simulations with unstable
dynamics or non-positive-definite covariance are rejected and counted. Bands
are conditional on admissible draws, not simultaneous, causal or prediction
intervals. Read long-horizon certainty cautiously, especially with persistent
variance and the remaining data issues.
""")
code("""
irf_name = cfg['irf']['model']
irf_curves, irf_metadata = estimate_irf(design, specs[irf_name], cfg['training_end'],
    horizon=cfg['irf']['horizon'], hac_lags=cfg['hac_lags'],
    draws=cfg['irf']['draws'], seed=cfg['irf']['seed'])
plot_commodity_irfs(irf_curves)
plt.show()
irf_points = irf_curves.loc[irf_curves.impulse.ne('ES') & irf_curves.horizon.isin([0, 1, 5, 10, 20]),
    ['impulse', 'horizon', 'variance_pct', 'variance_lower', 'variance_upper', 'volatility_pct']].set_index(['impulse', 'horizon'])
show_table(irf_points)
print('Training targets:', irf_metadata['n'], '| conditional max root:', round(irf_metadata['root'], 6))
print('Simulations accepted:', irf_metadata['draws_accepted'], '/', irf_metadata['draws_requested'],
      '| unstable:', irf_metadata['rejected_unstable'], '| nonpositive covariance:', irf_metadata['rejected_nonpositive_covariance'])
irf_curves.to_csv(OUTPUT / 'training_generalized_irfs.csv', index=False)
irf_points.to_csv(OUTPUT / 'training_irf_selected_horizons.csv')
display(Markdown('**Reading this run:** oil and gold show larger immediate correlated ES responses than corn/gas. '
    'All four fitted curves are positive at horizon five and fade overall. Corn’s horizon-20 band includes zero. '
    'Shock sizes differ by market, so magnitudes are not responses to an equal absolute shock. '
    'These associations can coexist with tiny or negative incremental forecast gains: the latter asks whether '
    'commodity history adds useful information beyond ES history and downside controls.'))
""")
md("""
## 9. Shared-date forecasts: VAR and asymmetric HAR

All models forecast **the next retained all-five-market row** and use the same
initial training cutoff, 22-row warm-up and expanding refits. At origin t, only
training outcomes dated at or before t may enter estimation. Neither future
commodity observations nor future returns are fed into the forecast.

The current initial fitted split is **79.78% / 20.22%**, approximately the 80/20
split inherited from the original analysis. Keep the fixed cutoff so every
comparison uses the same evaluation dates. An expanding window first estimates
on the initial history, predicts one observation, then adds the now-observed
outcome before predicting the next one. By the last forecast it uses 3,966
known target outcomes. This mimics sequential updating and avoids fitting the
first forecast to future outcomes. Exactly 80% is not a statistical requirement;
chronological evaluation is needed for our forecasting claim. Expanding history
assumes older observations remain useful; a fixed rolling window is an optional
break/adaptation robustness exercise, not a prerequisite for this main result.

Lower MSE/RMSE/MAE is better. These losses score log variance. Supporting
variance-unit MSE and QLIKE use `exp(log forecast) × historical residual smearing`.
The smearing factor is estimated at each origin; it need not track changing
conditional dispersion perfectly. Failed or unstable VAR fits use persistence,
retain their dates and are counted. No Gaussian forecast intervals are claimed.
""")
code("""
print(f'Fitting {len(specs)} models on {len(test_dates)} shared forecast targets...')
forecasts = expanding_forecasts(design, specs, cfg['training_end'])
# A common last-observation benchmark uses the same dates and original variance units.
baseline_rows = forecasts[forecasts.model.eq('VAR (Baseline)')].copy()
baseline_rows['model'] = 'Persistence'
baseline_rows['predicted_log'] = design['x'].loc[pd.DatetimeIndex(baseline_rows.origin_date), 'ES.l1'].to_numpy()
baseline_rows['predicted_variance'] = np.exp(baseline_rows.predicted_log)
baseline_rows['smearing'] = 1.; baseline_rows['root'] = np.nan
baseline_rows['status'] = 'ok'; baseline_rows['detail'] = ''
forecasts = pd.concat([forecasts, baseline_rows], ignore_index=True)
metrics = forecast_metrics(forecasts)
show_table(metrics)
forecasts.to_csv(OUTPUT / 'shared_forecasts.csv', index=False)
metrics.to_csv(OUTPUT / 'shared_forecast_metrics.csv')
print('Scored target dates:', test_dates.min().date(), 'to', test_dates.max().date())
""")
code("""
pairs = [('Add commodities to plain VAR', 'VAR (All 4: Oil + Corn + Gold + NG)', 'VAR (Baseline)'),
    ('Add commodities to downside VAR', 'VAR + Downside (All 4: Oil + Corn + Gold + NG)', 'VAR + Downside (Baseline)'),
    ('Add corn to downside VAR', 'VAR + Downside (All 4: Oil + Corn + Gold + NG)', 'VAR + Downside (No Corn: Oil + NG + Gold)'),
    ('Add commodities to LHAR', 'LHAR (All 4: Oil + Corn + Gold + NG)', 'LHAR (Baseline)'),
    ('Downside VAR versus matched LHAR', 'VAR + Downside (All 4: Oil + Corn + Gold + NG)', 'LHAR (All 4: Oil + Corn + Gold + NG)')]
gains = pd.DataFrame([{'Comparison': label, 'Candidate': candidate, 'Benchmark': benchmark,
    'N': int(metrics.loc[candidate, 'N']), 'MSE gain (%)': 100 * (1 - metrics.loc[candidate, 'MSE'] / metrics.loc[benchmark, 'MSE']),
    'MAE gain (%)': 100 * (1 - metrics.loc[candidate, 'MAE'] / metrics.loc[benchmark, 'MAE'])}
    for label, candidate, benchmark in pairs]).set_index('Comparison')
show_table(gains)
display(Markdown('Positive gain favours the candidate. These are descriptive differences, not significance tests.'))
gains.to_csv(OUTPUT / 'shared_forecast_gains.csv')
plot_names = ['VAR (Baseline)', 'VAR + Downside (Baseline)',
              'VAR + Downside (All 4: Oil + Corn + Gold + NG)', 'LHAR (Baseline)']
fig, ax = plt.subplots(figsize=(11, 5))
metrics.loc[plot_names, 'MSE'].plot.barh(ax=ax, color=['#7d8a96', '#235789', '#4aa3a2', '#e2a03a'])
ax.set(xlabel='Out-of-sample log-variance MSE (lower is better)', title=f'Shared-date forecasts: {len(test_dates)} targets')
ax.grid(axis='x', alpha=.25); fig.tight_layout(); plt.show()
""")
md("""
## 10. Validation and reproducibility

These checks verify matching targets, training chronology, finite predictions
and recomputed losses. The focused tests separately verify exact current HAR
preparation, identical LHAR features/HAC covariance, native VAR predictions,
daily restrictions and forecast invariance to future-data changes.
IRF checks independently verify native VAR lag/MA matrices, market-order
invariance, HAC covariance against statsmodels, seed reproducibility and
invariance to changed evaluation observations.

Run from the repository: `.venv/bin/python -m unittest tests.test_var_har_notebook -v`.
Restart-and-run-all execution is provided by `scripts/execute_var_notebook.py`.
Generated CSVs remain local; this notebook saves displayed results for review.
""")
code("""
assert summary.N.nunique() == 1
for name, frame in forecasts.groupby('model', sort=False):
    assert pd.DatetimeIndex(frame.date).equals(test_dates)
    assert frame.training_end.le(frame.origin_date).all()
    assert frame.origin_date.lt(frame.date).all()
    assert np.isfinite(frame[['actual_log', 'predicted_log', 'predicted_variance']]).all().all()
    assert frame.predicted_variance.gt(0).all()
    recomputed = np.mean((frame.actual_log - frame.predicted_log) ** 2)
    assert np.isclose(recomputed, metrics.loc[name, 'MSE'], rtol=0, atol=1e-12)
assert sha(source_path) == source_hash
assert irf_metadata['n'] == int(training_mask.sum())
assert irf_metadata['last_target'] == cfg['training_end']
assert irf_metadata['draws_accepted'] + irf_metadata['rejected_unstable'] + irf_metadata['rejected_nonpositive_covariance'] == cfg['irf']['draws']
provenance = {'source_sha256': source_hash, 'har_notebook_sha256': sha(ROOT / cfg['har_reference']),
    'module_sha256': sha(ROOT / 'var_har_notebook.py'), 'config': cfg,
    'irf_module_sha256': sha(ROOT / 'var_irf.py'), 'irf': irf_metadata,
    'run_time': pd.Timestamp.now(tz='Europe/Amsterdam').isoformat(),
    'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
    'statsmodels': statsmodels.__version__, 'shared_lag': p, 'common_fit_targets': len(design['y']),
    'initial_fit_targets': int(training_mask.sum()), 'evaluation_targets': len(test_dates),
    'output_sha256': {f.name: sha(f) for f in OUTPUT.glob('*.csv')}}
(OUTPUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\\n')
print('All notebook checks passed. Saved results:', OUTPUT)
""")
md("""
## 11. Interpretation for the report

Assess commodity contribution against the **matching equity-only model**:
plain VAR versus AR, or downside VAR versus AR with the same downside controls.
Assess VAR versus LHAR using shared assets, dates and return information.
R² measures full-sample fit; forecast MSE answers the predictive question.
VAR's selected individual variance lags and LHAR's 22-observation variance
averages intentionally differ; shared controls do not make those features identical.

Corn/no-corn comparisons isolate adding corn within the stated model. Daily-only
restrictions test a different representation of commodity history. Report all
these exploratory comparisons, including negative results and fallback counts.
Conditional joint significance does not establish improved forecasting or causality.

These numbers are recomputed on the current HAR's all-five retained calendar;
they must not be mixed with the earlier 809-target ES/CL/GC analysis. Data gaps,
unadjusted futures returns, uncertain provider publication timing, model residual
dependence and prior inspection of the test period remain limitations.
""")

notebook = dict(cells=cells, metadata={"kernelspec": {"display_name": "Python 3 (project .venv)", "language": "python", "name": "python3"},
                "language_info": {"name": "python"}}, nbformat=4, nbformat_minor=5)
path = ROOT / "VAR_QTFE.ipynb"
path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
print(f"Created {path.name}: {len(cells)} cells")
