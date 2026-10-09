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

**Research question:** does oil/gold variance information improve forecasts of
ES realised variance beyond equity history and the same downside-return
information used by asymmetric HAR? Corn and natural gas are extensions.

This notebook uses the latest `HAR_QTFE.ipynb` commodity specifications: RV5 from
2011, all five markets, the same decimal-unit ES downside terms, HAC(22),
fit-comparison tables, a corn/no-corn matrix,
coefficient results and a four-panel residual plot. All fitted comparison tables
use identical rows. A separate section evaluates sequential forecasts on shared
dates and independently reruns the latest LHAR function on those same inputs.
The **commodity-core calendar is frozen**, with no bond-data join. The latest
HAR's bond join is audited separately because it removes commodity observations
even from models that do not use bonds. Its standalone scores are not the scores
in our shared comparison. No bond regressor is added to VAR.

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
    forecast_metrics, stationarity_table, plot_residual_diagnostics, columns_for,
    load_yield_snapshot, reference_har_preparation, audit_reference_har_forecasts)
from var_irf import estimate_irf, plot_commodity_irfs
from var_robustness import run_robustness, plot_lag_comparison
cfg = json.loads((ROOT / 'config/var_har_notebook.json').read_text())
robust_cfg = json.loads((ROOT / 'config/var_robustness.json').read_text())
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
               for c in table.select_dtypes(include='number').columns
               if not pd.api.types.is_integer_dtype(table[c])}
    display(HTML(table.to_html(formatters={c: (lambda value, pattern=pattern: pattern.format(value))
        for c, pattern in formats.items()}, na_rep='—', border=0)))
print('Python', platform.python_version(), '| statsmodels', statsmodels.__version__)
print('Local source:', source_path.name, '| no API key or private Drive required')
""")
md("""
## 1. Match the HAR data and dates

The reviewed HAR commodity preparation computes returns and 5/22-observation variance
windows on each asset's source dates, then matches all five markets and removes
incomplete rows. We deliberately reproduce that policy for compatibility;
it is not a verified exchange calendar. The first 21 retained origins are then
used to warm up the downside-return windows. Every regression shares the same
remaining origin/target pairs, including baseline models without commodities.

ES close-to-close log returns are stored in percentage units, then divided by
100 when constructing downside terms, as in the latest HAR function. Those terms
equal `abs(min(mean(decimal return over 1/5/22 retained rows), 0))`: the negative
part is taken **after averaging**. Rescaling the three controls changes their
coefficient units, not equivalent unconstrained OLS fitted predictions.
Returns remain unadjusted for rolls.

**Separate bond-calendar audit:** reproduce the latest HAR's inner DGS10 join,
yield differences and complete-case removal using a saved, hashed
[public FRED DGS10 snapshot](https://fred.stlouisfed.org/series/DGS10).
That is a daily yield in percent, not intraday RV5; its squared change in basis
points is the HAR bond proxy. The original HAR computes changes before final
dropna, so a missing yield can also remove the next difference. We reproduce
that behaviour for the audit without imputing missing values. We do not certify
provider publication timing or historical real-time availability.
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
yield_path = ROOT / cfg['yield_snapshot']
yield_manifest = json.loads((ROOT / cfg['yield_manifest']).read_text())
assert sha(yield_path) == yield_manifest['sha256'], 'Yield snapshot differs from recorded retrieval'
yields = load_yield_snapshot(yield_path)
yield_wide, yield_excluded = prepare_har_data(raw, cfg['sample_start'], yields=yields)
pd.testing.assert_frame_equal(yield_wide, reference_har_preparation(raw, yields, ROOT / cfg['har_reference']))
calendar_rows = []
for label, panel in [('Commodity core (shared comparison)', wide), ('Latest HAR with yield join (separate)', yield_wide)]:
    audit_design = aligned_design(panel, cfg['max_lag'], cfg['common_warmup'])
    known = audit_design['target_dates'] <= pd.Timestamp(cfg['training_end'])
    calendar_rows.append({'Calendar': label, 'Panel rows': len(panel), 'Common target rows': len(audit_design['y']),
        'Initial training': int(known.sum()), 'Evaluation at fixed cutoff': int((~known).sum())})
calendar_audit = pd.DataFrame(calendar_rows).set_index('Calendar')
display(Markdown('**Calendar audit: these samples must not be mixed in a performance ranking.**'))
display(calendar_audit)
print('Commodity-core observations removed by the yield join:', len(wide.index.difference(yield_wide.index)))
calendar_audit.to_csv(OUTPUT / 'har_calendar_audit.csv')
pd.DataFrame({'date_removed_by_yield_join': wide.index.difference(yield_wide.index)}).to_csv(OUTPUT / 'har_yield_join_removed_dates.csv', index=False)
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
print('Dates rejected by commodity preparation, including initial rolling warm-up:', len(excluded))
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
## 3. Latest HAR specifications on the frozen commodity inputs

These fits use the current notebook's inspected `fit_har_x` definition, supplied
with **our frozen commodity-core panel**. They are not a reproduction of its
saved results on the newer yield-joined sample. They verify the latest commodity
features and decimal-unit downside controls. Baseline
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
sets_in_first_table.insert(1, 'Oil + Gold')
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
corn_names = ['VAR + Downside (Baseline)', 'VAR + Downside (Oil + Gold)',
    'VAR + Downside (All 4: Oil + Corn + Gold + NG)',
    'Restricted VAR + Downside (All 4: Oil + Corn + Gold + NG; Daily Only)',
    'VAR + Downside (No Corn: Oil + NG + Gold)',
    'Restricted VAR + Downside (No Corn: Oil + NG + Gold; Daily Only)']
show_table(summary.loc[corn_names, summary_columns + ['System params', 'Max root']])
lhar_names = ['LHAR (Baseline)', 'LHAR (Oil + Gold)', 'LHAR (All 4: Oil + Corn + Gold + NG)',
    'LHAR (All 4: Oil + Corn + Gold + NG; Daily Only)', 'LHAR (No Corn: Oil + NG + Gold)',
    'LHAR (No Corn: Oil + NG + Gold; Daily Only)']
display(Markdown('**Asymmetric HAR on exactly the same target rows, for reference:**'))
show_table(summary.loc[lhar_names, summary_columns])
""")
md("""
## 6. Coefficients and joint commodity tests

As in HAR, show a detailed equity-equation summary. This is the main
ES/oil/gold downside VAR; corn/gas extensions remain in the comparison tables.
Joint HAC tests use initial-history outcomes and condition on ES history and
the same downside signals. They test predictive associations, not economic causality
or out-of-sample gains. Displayed p-values are exploratory and unadjusted.
""")
code("""
selected_name = 'VAR + Downside (Oil + Gold)'
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
This five-market extension's responses are conditional VAR-X responses; they do not model feedback through future
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

**Independent latest-HAR check:** rerun its actual `fit_har_x` forecasting branch
for all six LHAR specifications. Override its default per-model 80/20 split
with the shared cutoff. Its returned index labels the **origin**, not the next
target; map that index explicitly to our target dates. The audit below requires
matching origins, targets, actual outcomes and every log forecast. The HAR
source notebook and its standalone saved outputs are not modified.
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
har_forecast_audit = audit_reference_har_forecasts(wide, design, specs, forecasts,
    cfg['training_end'], ROOT / cfg['har_reference'], cfg['hac_lags'])
display(Markdown('**Latest HAR function independently reproduces the shared LHAR forecasts:**'))
show_table(har_forecast_audit)
har_forecast_audit.to_csv(OUTPUT / 'latest_har_forecast_audit.csv')
""")
code("""
pairs = [('Add oil/gold to downside VAR', 'VAR + Downside (Oil + Gold)', 'VAR + Downside (Baseline)'),
    ('Add commodities to plain VAR', 'VAR (All 4: Oil + Corn + Gold + NG)', 'VAR (Baseline)'),
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
## 10. Data checks and focused robustness

The main VAR is **ES/oil/gold**; corn/gas specifications are extensions on the
same comparison calendar. Read `reports/var_har_notebook/DATA_AND_ROBUSTNESS_PLAN.md`
for the plan fixed before these runs. Earlier results and this evaluation period
have already been inspected, so the checks are exploratory.

**Data flags are unresolved candidates, not confirmed errors.** Display all
post-2011 flags and decompose each large close return into its measured opening
gap and open-to-close movement. The raw file and review ledger remain intact.
Daily aggregates cannot verify the underlying bid/ask quotes, contract identity,
daily interval or estimate publication cutoff. [VOLARE's methodology paper](https://arxiv.org/html/2602.19732v1)
and [Kibot rollover documentation](https://www.kibot.com/futures/rollover-rules.html)
provide context, rather than an independent reconstruction of these records.

Compare **VAR(5) and VAR(10)** on identical inputs and 802 outcomes; keep order five
as the training-BIC main specification, rather than retuning it on inspected scores.
The equity-only rows are AR(5)/AR(10). Larger systems estimate more coefficients.

At order five, compare unchanged RV5 with: training-window exclusions around the
three previously reviewed suspect records; broader non-crisis flag exclusions;
open-to-close ES downside returns; and RK predictors/outcomes. Features are built
before training rows are masked, preserving source-grid monthly averages,
retained-grid lags and following ES returns. **All 802 targets remain scored.**
Open-to-close removes genuine opening-gap information too, and may retain an
intraday switch. No scenario is certified as cleaned or back-adjusted data.
RK scores a different variance proxy: use within-scenario benchmark gains, not
raw cross-proxy MSE rankings.

The additional evaluation subset excludes broadly exposed windows retrospectively
and uses identical remaining dates for every model. It is a diagnostic, not a
new holdout or a reason to delete stress observations from the primary results.
Descriptive 95% circular-block intervals resample paired fixed forecast losses
(2,000 draws; blocks 5/20/60). They do not refit models, test a centred nested-model
null or correct prior model selection. A band containing zero does not prove
equal predictive performance.
""")
code("""
assert p == robust_cfg['main_lag'], 'Frozen lag sensitivity assumes the recorded main lag'
ledger_path = ROOT / 'datasets/volare_review_decisions.csv'
robustness = run_robustness(raw, wide, design, forecasts, pd.read_csv(ledger_path),
    source_hash, robust_cfg, cfg['training_end'])
for name, table in robustness.items():
    table.to_csv(OUTPUT / f'robustness_{name}.csv', index=False)
display(Markdown('**Post-2011 data flags: no observation is certified as erroneous.**'))
flag_columns = ['date', 'symbol', 'rk_to_rv5', 'unadjusted_close_log_return_pct',
    'opening_gap_pct', 'open_to_close_pct', 'decision']
show_table(robustness['flags'][flag_columns])
display(Markdown('**Lag comparison: same dates, target and downside information.**'))
show_table(robustness['lag_metrics'].set_index(['Model', 'Lag'])[
    ['N', 'ES_parameters', 'System_parameters', 'Fallbacks', 'MSE', 'RMSE']])
plot_lag_comparison(robustness['lag_metrics']); plt.show()
display(Markdown('**Scenario sample counts: masks affect estimation, not the lag/date grid.**'))
show_table(robustness['sample_flow'].set_index('Scenario'))
display(Markdown('**Within-scenario MSE gains (%): positive favours the candidate; RK has its own outcome.**'))
show_table(robustness['gains'].pivot(index=['Candidate', 'Benchmark'], columns='Scenario', values='MSE_gain_pct'))
display(Markdown('**Retrospective subset diagnostic: omit exposed evaluation windows for every model.**'))
show_table(robustness['subset_gains'].set_index(['Candidate', 'Benchmark']))
display(Markdown('**Baseline paired-loss intervals: descriptive, not formal nested-model significance tests.**'))
show_table(robustness['intervals'].loc[robustness['intervals'].block.eq(20)].set_index(['Candidate', 'Benchmark'])[
    ['gain_pct', 'lower_pct', 'upper_pct', 'block', 'draws']])
print('Full interval block-size sensitivity and dated forecasts are saved in robustness CSVs.')
""")
md("""
## 11. Validation and reproducibility

These checks verify matching targets, training chronology, finite predictions
and recomputed losses. The focused tests separately verify the latest HAR
commodity preparation, its separately reproduced yield join, identical decimal-unit
LHAR features/HAC covariance, native VAR predictions,
daily restrictions and forecast invariance to future-data changes.
IRF checks independently verify native VAR lag/MA matrices, market-order
invariance, HAC covariance against statsmodels, seed reproducibility and
invariance to changed evaluation observations.

Run from the repository: `.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v`.
Restart-and-run-all execution is provided by `scripts/execute_var_notebook.py`.
Generated CSVs remain local; this notebook saves displayed results for review.
For the separate calendar audit, retrieve the public snapshot once with
`.venv/bin/python scripts/fetch_fred_dgs10.py`; execution thereafter uses that
local file and verifies its recorded hash, without a live download or API key.
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
assert sha(yield_path) == yield_manifest['sha256']
assert har_forecast_audit.N.eq(len(test_dates)).all()
assert har_forecast_audit.Max_prediction_difference.lt(1e-9).all()
assert robustness['metrics'].N.eq(len(test_dates)).all()
assert robustness['forecasts'].origin_date.lt(robustness['forecasts'].date).all()
assert robustness['forecasts'].training_end.le(robustness['forecasts'].origin_date).all()
assert not robustness['forecasts'].duplicated(['scenario', 'lag', 'model', 'date']).any()
assert irf_metadata['n'] == int(training_mask.sum())
assert irf_metadata['last_target'] == cfg['training_end']
assert irf_metadata['draws_accepted'] + irf_metadata['rejected_unstable'] + irf_metadata['rejected_nonpositive_covariance'] == cfg['irf']['draws']
provenance = {'source_sha256': source_hash, 'har_notebook_sha256': sha(ROOT / cfg['har_reference']),
    'yield_snapshot_sha256': sha(yield_path), 'yield_manifest_sha256': sha(ROOT / cfg['yield_manifest']),
    'yield_join_panel_rows': len(yield_wide), 'yield_join_removed_core_rows': len(wide.index.difference(yield_wide.index)),
    'har_reference_forecasts_checked': int(har_forecast_audit.N.sum()),
    'robustness': {'settings': robust_cfg, 'records': len(robustness['forecasts']),
        'input_sha256': {name: sha(ROOT / name) for name in ['var_robustness.py', 'har_return_audit.py',
            'volare_data.py', 'volare_review.py', 'config/var_robustness.json',
            'reports/var_har_notebook/DATA_AND_ROBUSTNESS_PLAN.md', 'datasets/volare_review_decisions.csv']}},
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
## 12. Interpretation for the report

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

These numbers are recomputed on the frozen all-five commodity calendar using
the latest HAR commodity features. Its bond-data join and any yield-augmented
results use a separately restricted calendar and must be labelled separately;
they must not be mixed with the earlier 809-target ES/CL/GC analysis. Data gaps,
unadjusted futures returns, uncertain provider publication timing, model residual
dependence and prior inspection of the test period remain limitations.
""")

notebook = dict(cells=cells, metadata={"kernelspec": {"display_name": "Python 3 (project .venv)", "language": "python", "name": "python3"},
                "language_info": {"name": "python"}}, nbformat=4, nbformat_minor=5)
path = ROOT / "VAR_QTFE.ipynb"
path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
print(f"Created {path.name}: {len(cells)} cells")
