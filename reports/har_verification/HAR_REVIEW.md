# HAR performance verification — 4 October 2026

**Follow-up:** the [return-matched AR comparison](../har_followup/RETURN_CONTROL_REVIEW.md)
shows that AR gains about 9.7% when it receives LHAR's return signals. LHAR's
remaining gain against that stronger benchmark is about 1.0% and uncertain.
The 10.62% figure below remains valid against variance-only AR; it does not isolate
HAR's structure from the additional return information.

**The saved notebook's strong R² is reproducible, but it is in-sample. In a new
common-sample forecast comparison, plain HAR improves MSE by only 0.40% relative
to AR(15). LHAR, which adds negative equity-return terms, improves MSE by 10.62%.**
Adding oil and gold slightly worsens MSE relative to the corresponding equity-only
HAR/LHAR. These are exploratory sample results, not a claim of statistical
significance or a final model selection.

## What the previous commit did

Commit `dc26120` (`added tim changes`) imported the teammate's R analysis and
expanded HTML draft, preserved the originals, provided a portable runner and
verification script, and updated the README/checklist. Its reproduction covered
nine AR/VAR/persistence specifications and four Clark–West comparisons. It did
not modify HAR, repair the original notebooks or resolve the data anomalies.
The HAR notebook was already in the repository from earlier Colab commits.

## What the HAR notebook actually shows

Reexecuting its reviewed preparation and model functions reproduces the saved
R² values: **0.696311** for equity-only HAR, **0.724313** for equity-only LHAR,
and **0.726568** for LHAR with oil, natural gas and gold horizons. The first has
4,292 fitted observations; leverage models have 4,271 because another rolling
return window removes early rows. Their raw AIC/BIC values should not be compared
across those unequal samples. Within the leverage family, the simpler equity-only
LHAR has lower BIC than the commodity extensions shown.

All those regressions fit the full available sample. They do not demonstrate
performance on unseen observations. The final two forecast cells have no execution
count or saved output. Also, their forecasting function implements ordinary HAR
with daily commodity lags: it does not forecast the fitted LHAR specification.
A high in-sample R² for LHAR and a forecast from that HAR function are different
pieces of evidence.

Running the notebook's exact 500-target forecast function now gives:

| Specification | Log RMSE | Log MAE | R² versus expanding historical mean |
|---|---:|---:|---:|
| Equity-only HAR | 0.6548 | 0.5013 | 52.21% |
| HAR + daily CL/C/GC/NG | 0.6569 | 0.5021 | 51.89% |

The actual targets run **2024-09-16 to 2026-08-31**. The notebook labels these
forecasts with origin dates, **2024-09-13 to 2026-08-28**. The audit exports both
origin and corrected target dates without changing the fitted numbers. This is
a date-label bug, not evidence by itself that future outcomes entered estimation.
Beating a historical-mean benchmark by 52% is not the same as beating AR or VAR.
These 500-target scores should not be compared directly with Tim's 809-target scores.

The notebook's QLIKE calculation is mathematically the loss for the positive
forecast `exp(predicted_log_variance)`. That exponential is not generally the
conditional mean variance; the code does not estimate a bias correction. Its
Gaussian prediction intervals use conventional OLS variance assumptions, despite
residual concerns. This audit does not certify those intervals or adopt that
QLIKE implementation as the final variance forecasting design.

## Controlled comparison on the teammate's 809 targets

The new comparison uses the same source snapshot, ES/CL/GC matching, 2011 start,
80/20 split, forecast origins and realised log-RV5 targets as the R analysis.
Every model refits before each target using an expanding history. All models use
the same fitted training target rows after a **22-observation warm-up**. This is
why AR/VAR values differ slightly from Tim's original values, which use each
model's own lag-dependent starting row. The initial raw history is 3,236 rows;
the shared initial regression target sample is 3,214 rows.

Evaluation: **809 observations, 2023-07-13 to 2026-08-31**. Lower is better.

| Model | MSE | RMSE | MAE |
|---|---:|---:|---:|
| AR5 | 0.432935 | 0.657978 | 0.497063 |
| VAR5 | 0.435631 | 0.660023 | 0.498185 |
| AR15 | 0.429689 | 0.655507 | 0.494768 |
| VAR15 | 0.432764 | 0.657848 | 0.498074 |
| HAR | 0.427977 | 0.654199 | 0.494298 |
| HARX | 0.429154 | 0.655098 | 0.494129 |
| LHAR | 0.384075 | 0.619738 | 0.468533 |
| LHARX | 0.385184 | 0.620632 | 0.467804 |
| Naive | 0.526789 | 0.725802 | 0.546477 |

Definitions:

- HAR: equity's latest log variance, mean of the last five log variances and mean
  of the last 22 log variances, with an intercept.
- HARX: HAR plus those three components for each of oil and gold.
- LHAR: HAR plus the negative part of the latest equity return and negative parts
  of five-/22-observation mean equity returns, following the notebook's formula.
- LHARX: LHAR plus the oil/gold variance components.
- AR/VAR: fixed 5-/15-lag models matching the previously selected alternatives.
  For one-step ES predictions, fitting the VAR's ES equation by OLS yields the
  same prediction as fitting the full system. Independent statsmodels VAR checks
  confirmed this at the first, middle and last origins for both lag orders.

The new HAR averages run over the **retained ES/CL/GC observation grid**. The
original notebook computes variance averages on each asset's individual grid
before matching all five assets. Therefore these are deliberately aligned
versions of its model ideas, not exact replicas of its historical window dates.
Neither calendar has yet been validated as the final exchange-session definition.
All averaging here is **mean(log variance)**, not **log(mean variance)**.

LHAR's MSE is 10.26% lower than plain HAR and 10.62% lower than AR(15). It uses
additional equity-return information, so this is not a clean comparison of model
architecture alone. A return-augmented AR benchmark is the next useful control.
HARX's MSE is 0.27% higher than HAR; LHARX's is 0.29% higher than LHAR. MAE improves
slightly with the commodity extensions, so the commodity finding is specific to
squared-error loss and should not be overstated.

## Is the LHAR gain limited to one year?

| Evaluation year | AR(15) MSE | HAR MSE | LHAR MSE |
|---|---:|---:|---:|
| 2023 | 0.260640 | 0.269013 | 0.237193 |
| 2024 | 0.421025 | 0.417738 | 0.393865 |
| 2025 | 0.533883 | 0.530544 | 0.461169 |
| 2026 | 0.405226 | 0.401219 | 0.356864 |

LHAR has lower MSE in each displayed year. The 2023/2026 periods are partial years.
This is descriptive evidence; no annual significance tests or formal regime model
were fitted. An observation-level influence/anomaly sensitivity analysis remains
necessary before ruling out a few influential dates.

## Remaining notebook and research issues

- The notebook needs private Colab settings and a private helper module. Its plot
  cell selects 15 log-variance columns for five axes and will raise an index error.
  Later cells reference undefined `model_lhar_all` and `model_har_all` names.
  Saved outputs are not evidence that the current notebook runs top to bottom.
- The notebook performs stationarity diagnostics and commodity selection on the
  full sample. ADF/KPSS disagreement is labelled as a structural break without
  establishing one. Those selections cannot be described as untouched-test decisions.
- Blanket deletion requires all five markets plus unused prices/returns. The audit
  comparison instead explicitly uses ES/CL/GC, while retaining the teammate's
  common-row forecasting target as a provisional assumption.
- Session availability, quote anomalies and contract-switch effects remain
  unresolved. LHAR specifically uses unadjusted ES close returns, which may contain
  futures roll effects. Its promising result needs a defensible return series.
- The observed test period has already been inspected. Do not tune many variants
  on it and then present the winning score as independent confirmation.
- The original question mentioned interest rates. These models use commodities
  and do not settle the group's final research scope.

## Reproduce and checks

For a fresh Python environment, install `requirements-har.txt` first. The local
provider export must be available; the audit does not download it.

```sh
.venv/bin/python scripts/verify_har.py
.venv/bin/python -m unittest discover -s tests -v
```

The command preserves the notebook and provider data. It exports reconstructed
in-sample fits, the exact notebook 500-target forecast calculations with corrected
date annotations, and the controlled 809-target forecasts/metrics/yearly results.
Outputs are local under `reports/har_verification/`; hashes and versions are in
`provenance.json`. New executable logic is in `har_forecasts.py` and
`scripts/verify_har.py`.

All **12** tests pass. New tests verify window definitions, origin/target alignment,
rejection of invalid inputs, and a fitted-forecast leakage check: changing the
forecast target and every later variance/return leaves that origin's predictions
unchanged. The saved R output also agrees with every common target and origin.
This checks numerical timing in the supplied grid, not when a provider publishes
its daily estimates.

Validated versions: Python 3.13.0, NumPy 2.5.3, pandas 3.0.6,
SciPy 1.18.1, statsmodels 0.15.0.
Notebook SHA-256: `c19ca6e44a5730680c944d20600face6a590ac5336b14c9719191cdc21ebbcf2`.
Source SHA-256: `face904a9aeb062796d8fb2c2d17c7e2a2df6f7ecfdca9e473232ddebecacb8f`.

## Next steps in order

1. Agree and freeze the question, log-variance target, forecast calendar and main
   model comparison. Treat current alternatives as exploratory evidence.
2. Resolve/assess suspect quotes and rolls, particularly the equity return series
   used by LHAR. Document a sensitivity policy before comparing treatments.
3. Add a return-augmented AR benchmark to isolate the contribution of equity
   returns, then compare equity-only LHAR with the matched commodity extension.
4. Quantify uncertainty using an appropriate paired-loss method for each
   comparison; account for the alternatives already examined. Assess influential
   dates, RK/RV5 sensitivity and remaining residual dependence.
5. Consolidate the analysis into one portable workflow and update the report to
   distinguish promising equity forecasting from evidence of commodity benefits.
