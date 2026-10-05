# VAR methods and results — integration draft

Updated 4 October 2026. These numbers describe the specified exploratory VAR
analysis. Integrate the data paragraphs into the report's data section and the
remaining paragraphs into methodology/results; reconcile notation and add the
group's approved literature citations before submission.

## Data and empirical question

We investigate whether oil and gold futures' realised variances improve forecasts
of E-mini S&P 500 futures realised variance beyond the equity market's own
variance history. The main system comprises ES, WTI crude oil futures (CL) and
gold futures (GC). Corn and natural gas enter a separate extension. This revises
the initial interest-rate proposal to a commodity information question; neither
gold nor another commodity is treated as a substitute measurement of bond risk.

The analysis uses the saved VOLARE futures export. RV5 is a realised variance
measure based on five-minute intraday sampling. The dependent variable is its
logarithm, not its square root. Taking the square root would express realised
volatility; here log variance provides the forecasting target used throughout
the VAR equations and matched AR comparisons. It respects the positivity of
variance after retransformation and permits a common scale for modelling its
persistence. It does not establish normality or eliminate measurement error.
No annualisation or additional rolling-variance transformation is applied.

The main sample contains 4,045 jointly observed ES/CL/GC RV5 dates between
3 January 2011 and 31 August 2026. Seven partially observed dates in the
post-2011 union of main-market source dates are excluded and listed separately.
This is not a count of all missing exchange sessions: dates absent for all
markets require a separate calendar check. Eligibility depends only on the
chosen main variances, not on closing prices, returns or corn/gas coverage.

The original export remains unchanged. Potential quote and contract-switch
issues are documented separately; the main results use the preserved snapshot.
The statistical forecast horizon is the next jointly observed main-market
provider date. Provider session boundaries and publication timing remain
unverified, so the analysis assumes completed origin-date measures are available
before the next target. It should not be described as a verified clock-time
trading strategy.

## Methodology

Let y_t be the vector of logged ES, CL and GC realised variances. We estimate
an intercept VAR, y_t = c + sum(A_j y_(t-j), j=1,...,p) + u_t. The restricted
benchmark is an ES-only autoregression with the same lag order; an independently
BIC-selected ES AR and last-observation persistence provide additional controls.
An expanding estimation window ends at each forecast origin, and the next common
row is predicted without realised future commodity inputs.

The initial history comprises 3,236 observations through 12 July 2023. The
evaluation period has 809 targets from 13 July 2023 through 31 August 2026.
Candidate orders up to 20 are compared using only the initial history, with a
common warm-up sample within each search. Orders remain fixed at subsequent
refits. BIC selects level VAR(5) and AIC selects VAR(15); corresponding
differenced variants select orders 4 and 14. The independently selected ES AR
also has order 5. Differenced forecasts are reconstructed in log levels before
evaluation. These choices preserve the existing analysis. Because the evaluation
period has already been inspected, the reported evidence is exploratory.

Log-variance MSE is the primary loss. Log RMSE/MAE, variance MSE and QLIKE provide
supporting evaluations. Variance forecasts multiply the exponentiated log
forecast by an origin-specific smearing factor, calculated as the mean of the
exponentiated fitted ES training residuals. This factor uses no future residuals.
It addresses average retransformation bias under suitable assumptions, but does
not guarantee accurate conditional mean variance when residual dispersion changes.
QLIKE is evaluated as v/h - log(v/h) - 1, where v and h are observed and forecast
variance in the export's original units. An unstable, failed or unavailable fit
uses persistence and remains in the headline scores with an explicit status flag.

Joint Newey–West HAC Wald tests assess whether all oil lags, all gold lags or both
sets of lags are zero in the training ES equation. Nested log squared-error
forecast comparisons use exploratory one-sided Clark–West statistics with HAC
uncertainty and Holm adjustment within each scenario. These tests do not test
QLIKE differences or identify structural economic causality.
The normal-reference Clark–West approximation is not guaranteed exact for this
heteroskedastic system with many extra coefficients; HAC errors do not remove
that limitation. Its p-values are supporting exploratory evidence.

## Main findings

All main rolling fits produce forecasts without fallback. The implementation
reproduces the teammate's nine distinct forecast series to numerical precision.
The independently selected AR(5) coincides with the same-order BIC benchmark.

| Model | Log MSE | Log RMSE | QLIKE |
|---|---:|---:|---:|
| Persistence | 0.526789 | 0.725802 | 0.333163 |
| ES AR(5) | 0.432888 | 0.657942 | 0.228627 |
| ES/CL/GC VAR(5) | 0.435655 | 0.660042 | 0.234206 |
| ES AR(15) | 0.429650 | 0.655477 | 0.227387 |
| ES/CL/GC VAR(15) | 0.432815 | 0.657886 | 0.231686 |
| Differenced ES AR(4) | 0.450189 | 0.670961 | 0.237164 |
| Differenced ES/CL/GC VAR(4) | 0.452427 | 0.672627 | 0.241370 |
| Differenced ES AR(14) | 0.436907 | 0.660990 | 0.231157 |
| Differenced ES/CL/GC VAR(14) | 0.439977 | 0.663308 | 0.235015 |

The principal VAR(5) has approximately 0.64% higher log MSE than AR(5); VAR(15)
has 0.74% higher log MSE than AR(15). QLIKE is also worse for every VAR than
its matched AR. The four one-sided Clark–West p-values are 0.454, 0.249, 0.411
and 0.238, respectively; all Holm-adjusted p-values are about 0.950. We therefore
find no evidence of improved forecast accuracy from oil and gold in these
specifications and this evaluation period. This does not prove that commodity
information has no predictive value under other horizons or model structures.

Training associations and forecast performance differ. In VAR(5), the joint HAC
p-values are 0.0256 for oil, 0.00233 for gold and 0.00113 for both. Thus lagged
commodity variances show conditional training associations, but these do not
translate into an out-of-sample forecasting advantage. Individual significant
coefficients would not overturn the matched forecast comparison.

All initial fitted systems are dynamically stable: the largest root modulus is
0.972 for VAR(5) and 0.987 for VAR(15). Nevertheless, adjusted multivariate
Portmanteau tests at 30 lags reject residual whiteness (p = 6.27e-19 and 0.0382),
and multivariate ARCH tests reject constant residual variance (p < 1e-22).
Differencing does not resolve these problems. ADF tests reject a unit root in
all three training log-variance series, while KPSS statistics exceed the 5%
level-stationarity critical value of 0.463. These conflicting outcomes motivate
caution about persistent levels and changing regimes; they do not themselves
identify a structural break. Robust standard errors do not fix misspecified
dynamics, and no Gaussian forecast intervals or causal shock interpretation
are claimed.

## Robustness and extension

| Level BIC comparison | Targets | Restricted benchmark log MSE | VAR log MSE | VAR improvement |
|---|---:|---:|---:|---:|
| RV5, ES AR vs three-market VAR | 809 | 0.432888 | 0.435655 | -0.64% |
| RK, ES AR vs three-market VAR | 809 | 0.399857 | 0.401440 | -0.40% |
| RV5, suspect-training mask, ES AR vs three-market VAR | 809 | 0.432763 | 0.435571 | -0.65% |
| RV5, matched three-market control vs five-market VAR, including fallbacks | 809 | 0.436220 | 0.446135 | -2.27% |
| Same extension pair, all models available | 700 | 0.448285 | 0.446932 | +0.30% |

Positive improvement means lower VAR loss. RK changes the evaluation proxy as
well as the inputs, so its smaller absolute MSE is not evidence that RK forecasts
RV5 better. The RV5 sensitivity masks design rows exposed to three flagged
historical dates over a conservative 22-row span without rebuilding lags or
removing evaluation targets. It is retrospective, and the observations have not
been certified as errors. Neither sensitivity reverses the principal conclusion.

The five-market extension has 35 missing variance cells on the main date grid.
Its level BIC VAR(5) needs persistence fallbacks on 35 of 809 targets; the level
AIC VAR(10) needs 74, and the differenced AIC VAR(14) needs 109. These counts are
forecasts, not the number of missing source cells. Adding markets increases the
number of required lagged observations. The matched three-market controls share
the five-market lag order and training design-row mask, allowing the incremental
market contribution to be assessed separately from sample and order changes.

Across all targets, the five-market level variants lose approximately 2.27%
(BIC) and 3.43% (AIC) relative to these controls. On the 700 dates where every
extension model actually fits, the BIC and AIC extensions have small descriptive
advantages over the matched three-market controls, about 0.30% and 0.33%.
However, their log MSEs (0.446932 and 0.441366) remain above the corresponding
matched equity-only AR losses (0.445034 and 0.441147). This selected availability
subset cannot replace the all-target evaluation, and Clark–West inference is
withheld for the fallback mixtures.

Yearly results vary: VAR(5) improves on AR(5) in 2024 but loses in the 2023,
2025 and 2026 portions. The four periods contain 121, 259, 258 and 171 targets,
respectively. A retrospective influence check removing the five largest absolute
paired loss differences still leaves the principal VAR(5) raw mean gain negative
(-0.002275). No dates are removed from headline losses. The negative average
finding is therefore not attributable solely to those five influential dates.

The evidence supports a restrained conclusion: cross-market training
associations exist, but the specified VAR does not improve on a credible ES-only
forecast benchmark over the examined period. Remaining provider timing,
contract/quote validation and residual specification issues limit generalisation.
The HAR analysis should be discussed separately and compared only after its
target, dates and information rules have been reconciled with this section.

## Evidence for integration

Tables above use `generated/forecast_metrics.csv`, `forecast_comparisons.csv`,
`corn_gas_all_models_available_metrics.csv`, `joint_predictive_tests.csv`,
`training_diagnostics.csv`, `stationarity.csv`, `yearly_metrics.csv` and
`main_influence_summary.csv`. Supporting figures are in
`generated/training_diagnostics.pdf` and `forecast_figures.pdf`. Large coefficient
tables and residual plots belong in the appendix. See [README.md](README.md)
for run and verification commands.
