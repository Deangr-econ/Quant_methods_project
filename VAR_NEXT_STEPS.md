# VAR: next steps and decisions

**7 October update:** the HAR reconciliation is complete. All 30 tests and
fresh saved-notebook verification pass. Latest HAR commodity forecasts match on
the frozen 802-target comparison; its newer bond join is audited separately.
Downside controls now use decimal return units, with equivalent predictions.
See `reports/var_har_notebook/HAR_VAR_RECONCILIATION.md` and
`PROJECT_CHECKLIST.md`. The detailed tables and IRF simulation bands below
describe the historical 5 October run.

Updated 5 October 2026. Current entry point: `VAR_QTFE.ipynb`, aligned with
the current asymmetric HAR. Earlier ES/oil/gold R results remain a separate
analysis with a different calendar. This focused list supplements `VAR_TODO.md`.

## 1. Data and sample — establish the basis before interpreting results

- [x] Confirm that the current notebook already starts on 1 January 2011.
- [x] Audit raw RV5 availability for ES, oil (CL), corn (C), gold (GC) and gas (NG).
- [x] Record why starting in 2011 does not eliminate calendar mismatches.
- [x] Retain the current HAR-matched sample for comparable model results.
- [ ] Confirm the export's session dates, measurement intervals and publication
  timing from provider information; distinguish missing records from non-trading.
- [ ] Review remaining flagged prices/contract switches, including post-2011
  observations, before interpreting close-to-close downside returns economically.
- [ ] Agree the final common-calendar wording with the group and carry it into
  the data section. Explain that the forecast is for the next retained common
  observation, which can skip an otherwise observed ES date.

**Decision:** keep the 2011 start for HAR consistency and to exclude the previously
flagged early sample. Do not present it as a complete cleaning solution or as a
way to improve model scores. Preserve the source; do not fill absent RV5 with
zeros or carry values forward to invent trading observations.

| Raw period | Union of provider dates | All five RV5 observed | Incomplete | Gold alone observed |
|---|---:|---:|---:|---:|
| 2009–2010 | 327 | 302 | 25 | 0 |
| 2011 onward | 4,052 | 4,010 | 42 | 0 |

The gold-only pattern described in conversation is not reproduced in this export.
Some early dates lack ES; many later mismatches involve corn. Availability alone
does not establish an exchange closure or a provider error. The prepared panel
has 3,989 dates, after 42 incomplete dates and 21 rolling-warm-up dates are
excluded. Regression preparation then yields 3,967 common target rows.
The notebook saves the coverage counts and date-by-market missingness audit.

## 2. IRFs — show the response, then explain its limits

- [x] Fit the initial-training five-market downside VAR(5), through 12 July 2023.
- [x] Add four commodity-to-ES generalized IRF curves over horizons 0–20.
- [x] State the shock, response, units, time steps and treatment of downside controls.
- [x] Add reproducible exploratory uncertainty bands and accepted/rejected draw counts.
- [x] Check lag/MA calculations against native VAR, ordering invariance, HAC
  covariance against statsmodels, reproducibility and future-data invariance.
- [x] Execute all notebook cells in a fresh kernel, inspect the IRF figure and
  independently verify saved hashes, IRF records and all 16,040 forecast records.
- [ ] Walk through one graph together: shock, zero line, curve, shading and decay.
- [ ] Choose a compact figure/table for the report and write its interpretation
  alongside the forecasting results. Keep technical band details in the appendix.

**Plain explanation:** an IRF asks what the fitted system predicts after an
unexpected innovation, rather than a usual movement already predicted by its
history. It traces the associated response now and at later observations.

Here the innovation is one residual standard deviation of commodity **log
variance**. It is not a 1% commodity price increase. The outcome is ES variance;
volatility is its square root. A curve at +8% means an 8% increase in the implied
variance path relative to baseline, not an 8% equity return. Horizons count
retained common observations. Horizon zero is contemporaneous, before lag effects.

Generalized responses account for correlated innovations and do not depend on
whether gold is listed before oil. That does not identify a causal commodity
shock. Downside controls follow the same fixed path in both scenarios, so this
is a conditional VAR-X response, not a simulation of future-return feedback.
The percentage back-transformation describes the log-model path; it is not an
independently estimated arithmetic conditional-variance mean.

| Innovation | ES variance response at h=1 | At h=5 | At h=20 | Exploratory h=20 band |
|---|---:|---:|---:|---:|
| Oil | +11.53% | +8.31% | +2.55% | +1.44% to +3.82% |
| Corn | +4.76% | +3.71% | +0.70% | −0.47% to +2.15% |
| Gold | +10.70% | +8.55% | +1.72% | +0.36% to +3.43% |
| Natural gas | +4.13% | +5.24% | +2.91% | +1.74% to +4.08% |

Different markets have different one-standard-deviation innovation sizes. Do not
rank effects as if the absolute shocks were identical. All 2,000 seeded parameter
simulations were admissible in this run; the initial conditional root is 0.978582.
Bands use joint Bartlett HAC(22) coefficient/residual-covariance uncertainty and
are pointwise, asymptotic and exploratory. They rely on weak dependence and
stationarity assumptions; persistent dynamics, unresolved breaks and residual
misspecification limit strong significance claims. They are not prediction bands.

**Connection to the research question:** IRFs describe fitted dynamic associations.
Forecast comparisons test whether commodities add useful information beyond ES
history and downside returns. A positive correlated IRF does not imply a forecast
improvement. Our all-four downside VAR has slightly higher forecast MSE than its
equity-only downside benchmark (+0.35%). NG alone gives a small descriptive
improvement (about 0.40%); neither comparison establishes a significant gain.

Method: [Pesaran and Shin (1998)](https://www.sciencedirect.com/science/article/pii/S0165176597002140).
See also the [statsmodels VAR guide](https://www.statsmodels.org/stable/vector_ar.html)
for MA representations and the ordering dependence of Cholesky IRFs.

## 3. Training/testing — preserve fair sequential forecasts

- [x] Verify the current split and expanding-window chronology.
- [x] Confirm that lag selection uses only the initial training sample.
- [x] Use identical 802 evaluation targets for VAR, downside VAR, LHAR and persistence.
- [x] Keep the fixed 12 July 2023 initial cutoff; document approximate 80/20.
- [ ] Confirm Tim's and Dean's final report comparisons use this same target,
  cutoff, evaluation dates, return units and information availability. Different
  samples need separate tables, not a direct comparison of raw MSE values.
- [ ] Optional after the main write-up: a prespecified rolling-window sensitivity
  if older regimes or breaks are central to the research question.

**Why:** fitting all observations and reporting R² shows historical fit. To test
forecasting, estimate on older observations and predict newer ones. A random
80/20 split would mix past and future; our split is chronological.

An expanding window works like this:

1. Estimate using 3,165 known target outcomes, ending 12 July 2023.
2. Predict the next common observation, 13 July 2023.
3. Once that outcome is observed, add it to the history and estimate again.
4. Repeat, scoring all 802 forecasts through 31 August 2026. The last forecast
   uses 3,966 known outcomes, ending at its 28 August 2026 origin.

Adding yesterday's outcome to predict tomorrow is legitimate updating. Including
tomorrow's outcome before predicting it would be leakage. Initial lag order 5
stays fixed. Training grows; the set of evaluation targets does not change.

The fitted split is **79.78% training / 20.22% evaluation**, reflecting the frozen
cutoff inherited from the earlier calendar. Exactly 80/20 is not necessary.
Chronological evaluation is necessary for our forecasting claim; keep expanding
refits because they are already implemented and allow fair comparison. Expanding
windows use more data but may adapt slowly to new regimes. Rolling windows can
adapt faster but discard observations and introduce a window-length choice.
The already-inspected test period is exploratory, not an untouched final holdout.

## 4. Learn the code/results — after the decisions above

- [ ] Walk through data preparation and one origin/target pair.
- [ ] Explain the log-RV5 target, five lags, full system versus ES equation and
  the three downside controls. Distinguish variance from volatility.
- [ ] Trace one forecast from inputs to prediction, smearing and forecast loss.
- [ ] Read R², HAC coefficient tests, lag criteria, roots and residual diagnostics.
- [ ] Compare original Tim VAR, matched downside VAR and Dean's LHAR without
  confusing sample changes with model improvements.
- [ ] Practise explaining the main finding: downside equity information helps;
  additional commodity information gives limited incremental forecast value.

## Finish the handover

- [ ] Integrate sample rules, IRF interpretation and forecast findings into the report.
- [ ] Have another group member run the saved notebook from a fresh environment.
- [ ] Keep provider/return limitations explicit; do not equate passed code checks
  with validated data provenance or a perfectly specified model.

Verification: the full 26-test Python suite passes, including five new IRF tests.
The delivered notebook has 13 executed code cells and four figures; its saved
results pass independent verification. Repeat execution/verification after any
rebuild. No commit or push is part of this task.
