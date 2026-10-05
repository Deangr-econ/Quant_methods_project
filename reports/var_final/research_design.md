# Recorded VAR research design

Recorded 4 October 2026, following the user's scope confirmation. This freezes
the current exploratory analysis; it is not a preregistration and does not turn
an already examined evaluation period into an untouched holdout.

## Question and motivation

Do oil and gold futures' realised variances improve forecasts of ES realised
variance beyond ES's own history? Cross-market volatility may contain information
about shared conditions or transmission between markets. The empirical question
is whether that information improves prediction after controlling for equity
variance persistence, rather than whether individual coefficients are significant.

The original Treasury/Brent proposal is revised explicitly. ES denotes E-mini
S&P 500 futures, CL denotes WTI crude oil futures and GC denotes gold futures.
They support a futures-market commodity information question; gold is not an
interest-rate proxy and CL is not Brent spot. Corn (C) and natural gas (NG) test
whether a broader commodity information set adds value. There is no bond
variable in this VAR.

## Source and target

The saved VOLARE file is `datasets/realized_variance_futures.csv`. Its SHA-256 is
`face904a9aeb062796d8fb2c2d17c7e2a2df6f7ecfdca9e473232ddebecacb8f`.
The historical acquisition date is unknown; the run time is not a retrieval
date. Provider access, estimator explanations and preliminary anomaly review
are recorded in `datasets/README.md` and `reports/volare/`.

RV5 is the realised **variance** based on five-minute sampling; it is not a
five-day rolling variance. The main equations use `log(rv5)` directly, in the
export's decimal-return variance units, without annualisation. `sqrt(rv5)` is
realised volatility, but it is not this model's dependent variable.
`10000 * rv5` expresses squared percentage-return units;
`log(10000 * rv5) = log(rv5) + log(10000)`. The direct logarithm preserves the
teammate's convention. Variance-scale predictions are in original export units.
RK is a separate realised-kernel variance proxy, used in a robustness scenario.
Do not infer provider session coverage or annualisation from those labels alone.

The statistical horizon is the next **jointly observed ES/CL/GC provider-date
row**, not necessarily the next ES trading day or 24 hours. The completed
provider-day values through the origin are assumed available. Session boundaries,
timezone and publication cutoff have not been verified. The main grid excludes
dates missing a required main variance; the exclusion file makes this explicit.
Corn/gas availability never removes a main target. No missing variance is filled.

## Split and estimation

| Component | Rule |
|---|---|
| Sample | From 2011-01-03 to 2026-08-31 on the common main grid |
| Initial history | 3,236 rows, through 2023-07-12 |
| Evaluation | 809 targets, 2023-07-13 through 2026-08-31 |
| Refits | Expanding history at every origin; earlier observed evaluation values may enter subsequent fits |
| Lag search | Initial history only, maximum 20; common warm-up rows within each search |
| Deterministic terms | Intercept, no trend |
| Orders | Level VAR BIC 5/AIC 15; differenced VAR BIC 4/AIC 14; independently BIC-selected ES AR 5 |
| Comparisons | Same-order ES AR restrictions, selected AR, persistence and four VAR variants |
| Extension | Five-market level VAR BIC 5/AIC 10; same-order three-market controls on identical full-input training masks |

Primary comparison: level ES/CL/GC VAR(5) versus ES AR(5), evaluated by log-MSE.
The AIC and differenced alternatives are secondary. This retains the existing
contribution's loss convention rather than selecting a favourable new metric
after seeing results. Log RMSE/MAE, original-unit variance MSE and QLIKE are
supporting losses. No further tuning on this evaluation period is warranted;
new design decisions must be labelled exploratory or assessed on new data.

For a successful fit, variance forecasts use
`exp(predicted_log) * mean(exp(training_ES_residuals))`. The smearing factor is
re-estimated using only the origin's training residuals. It corrects average
retransformation bias under appropriate residual-distribution assumptions; a
single historical factor need not estimate the conditional mean accurately
under changing heteroskedasticity. It does not create prediction intervals.
Persistence uses the last observed variance directly. QLIKE is
`actual/forecast - log(actual/forecast) - 1`; both quantities are variances.

An unstable system (largest companion eigenvalue modulus at least one), failed
fit or missing required origin predictor invokes persistence and is flagged.
All 809 targets remain in headline scores. Matched AR and VAR fits share
historical design-row eligibility, while the independently selected AR can use
all available ES history. Extension controls share order and training rows with
the five-market fit but need only the three main markets at prediction time.

## Robustness and inference

Run RK on the same main date grid, an RV5 suspect-training sensitivity, and the
corn/gas extension. The suspect sensitivity masks training outcomes/design rows
exposed to 2018-03-26, 2020-04-16 or 2021-03-29 within 22 main rows, including the
flagged row. Lags are formed before exclusions. Original quotes and test targets
remain unchanged; main-selected orders are held fixed. This is a retrospective
stress test, not a claim that those observations are confirmed errors or that
the anomaly policy was available in real time.

Training ES equations receive joint HAC Wald tests of all CL lags, all GC lags
and both sets together. These describe conditional predictive associations;
they do not identify economic causality. Residual serial dependence and ARCH
are reported rather than treated as resolved by differencing or robust errors.
Squared-error nested comparisons use exploratory one-sided Clark–West statistics
with Newey–West uncertainty and within-scenario Holm adjustment. They do not test
QLIKE gains. Inference is withheld for fallback mixtures. Yearly results,
cumulative loss differences and retrospective influential-date checks support
interpretation; they are not used to delete unfavourable evaluation targets.
