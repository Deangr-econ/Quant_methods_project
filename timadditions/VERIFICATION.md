# Reproduction and checklist review — 4 October 2026

The adapted teammate analysis completed in a fresh `Rscript --vanilla` process
using the repository VOLARE export. All nine reported MSE values and all four
Clark–West one-sided/Holm p-values match the supplied HTML to its printed precision.
This verifies numerical reproduction, not final research validity.

## Sample and target

- Target: natural log of unscaled RV5 variance for ES; predictors ES, CL and GC.
- Training: **3,236 observations, 2011-01-03 to 2023-07-12**.
- Evaluation: **809 observations, 2023-07-13 to 2026-08-31**.
- Common sample: 4,045 observations after removing **7 incomplete dates**
  from the source-date union on/after 2011-01-01. This is the supplied matching
  rule, not a verified exchange-session calendar.
- Forecasts use expanding histories and predict the next retained common row.

| Model | MSE | RMSE | MAE |
|---|---:|---:|---:|
| AR | 0.4328876 | 0.6579420 | 0.4970283 |
| VAR | 0.4356551 | 0.6600417 | 0.4981932 |
| AR15 | 0.4296496 | 0.6554766 | 0.4947571 |
| VAR15 | 0.4328146 | 0.6578864 | 0.4980830 |
| AR_D4 | 0.4501892 | 0.6709614 | 0.5083633 |
| VAR_D4 | 0.4524269 | 0.6726269 | 0.5079093 |
| AR_D14 | 0.4369072 | 0.6609896 | 0.5006208 |
| VAR_D14 | 0.4399775 | 0.6633080 | 0.5031430 |
| Naive | 0.5267887 | 0.7258021 | 0.5464770 |

The level VAR(5) has approximately 0.64% higher MSE than AR(5). None of the four
matched VAR comparisons demonstrates an improvement under the supplied
Clark–West test. This does not establish equivalence or significant AR superiority.
The draft's qualitative result is numerically reproducible.

## Diagnostic findings reproduced

| Initial VAR | Maximum root modulus | Adjusted Portmanteau p, lag 30 | Multivariate ARCH p, lag 5 |
|---|---:|---:|---:|
| Levels, 5 lags | 0.9722156 | < 2.2e-16 | < 2.2e-16 |
| Levels, 15 lags | 0.9869872 | 0.03819 | < 2.2e-16 |
| Differences, 4 lags | 0.6852643 | < 2.2e-16 | < 2.2e-16 |
| Differences, 14 lags | 0.9163259 | 0.0003571 | < 2.2e-16 |

These are rounded printed R outputs. All four initial fits satisfy the root
criterion, but residual serial correlation and ARCH effects remain. Stability
of the coefficients does not establish stationarity of the observed process.
Training time plots, annual means, ACFs, ADF/KPSS tests and KPSS bandwidth sensitivity
are saved in `reports/teammate_var/console_output.txt` and `diagnostic_plots.pdf`.
No claim is made that every expanding-window fit has passed those diagnostics.

## Checklist credit

The following completed tasks apply specifically to the imported **R commodity
analysis**. They do not repair the legacy Python VAR notebook or approve the
unresolved research scope, session calendar or data treatment.

| Item | Status | Evidence / remaining limitation |
|---|---|---|
| M1: equity-only benchmark | Complete | Separately BIC-selected AR, matched longer/differenced ARs and persistence; common targets. |
| M2: stationarity investigation | Complete | Training-only plots/ACFs, ADF/KPSS and bandwidth checks; differences are sensitivity models, with forecasts reconstructed to log levels. Stationarity uncertainty remains explicitly documented. |
| M3: training-only lag selection | Complete for this analysis | Candidate maximum 20, intercept, initial-training selection held fixed; AR(0) handled and tested. Fixed alternatives checked against training selections. |
| F4: uncertainty in forecast comparisons | Complete for log squared-error comparisons | Paired losses saved; matched nested comparisons use one-sided CW with HAC errors and Holm adjustment. This does not supply variance/QLIKE inference or cure model misspecification. |
| I1: magnitude interpretation | Complete | Percentage changes in forecast MSE are reported as changes in prediction loss, not returns or volatility levels. |
| C1/C4/C5/C8: portable, explicit, reproducible code | Partial project-wide | R entry point runs fresh with recorded versions and explicit series; old notebooks and shared module issues remain. No automated environment lockfile. |
| C7/F1: forecast correctness and sequential evaluation | Substantial progress | Actual origin/target/training-end dates saved; first forecast reproduced; finite forecasts, loss arithmetic and AR(0) verified. Full fitted-model future-perturbation test and provider timing remain open. |
| M4–M6: model adequacy | Partial | Initial diagnostics reproduced; no rolling stability/fallback system, full AR diagnostics or residual-dynamics repair. |
| F3/F5/I2/I3 | Partial | Common log targets, alternative lags/differences, Holm correction and descriptive yearly losses. No variance-scale score, untouched validation design, RK/anomaly robustness or flagged-date influence study. |
| R1–R5/D4–D8 | Open | Commodity scope and 2011 sample are reproduced assumptions, not a finalized group design; dates, availability, quotes and rolls still need resolution. |
| S1–S4: report and handover | Partial | Expanded draft and reproduced tables now available. No complete report, literature verification or second human reproduction performed. |

## Validation performed

- Full fresh-session analysis completed; all 809 targets have nine finite forecasts.
- First recursive forecasts agree with the separate first-origin computation.
- Verification script checks dated origins against the input sample, the observed
  target, persistence values, all computed losses, draft MSE/CW numbers and yearly counts.
- Nine existing Python preparation/audit tests still pass.
- Imported R/HTML originals match their recorded SHA-256 checksums. Existing raw
  data, preparation panels and notebooks were not modified.

Validated R environment: `validated_sessionInfo.txt`. Run configuration and local
input/output tables are under `reports/teammate_var/`; regenerate using the README.
The checked working-file hashes are:

- `datasets/realized_variance_futures.csv`: `face904a9aeb062796d8fb2c2d17c7e2a2df6f7ecfdca9e473232ddebecacb8f`
- `timadditions/var_analysis.R`: `d2553a32615b88be4957da37d462865862247efa01704aea28c9be806e132ac3`
- `scripts/run_teammate_var.R`: `69dd519992ebe6af415240bdf7568d7dfa16a4ec97af48645b53cad31263d9a0`
- `scripts/verify_teammate_var.R`: `f0e71612e665a39af9048d30e7cb060e5f4c9d8df28a14f41c322730517002ab`
