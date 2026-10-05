# VAR implementation audit — 4 October 2026

## Assessment

The checked implementation reproduces the intended forecasts, date alignment,
sample masks and losses. No forecasting arithmetic or alignment defect was
identified in this audit. This supports implementation correctness for the
recorded design; it does not certify provider data, establish clock-time
availability or resolve the diagnosed model specification issues.

## Verification completed

| Check | Result |
|---|---|
| Focused R checks | Passed: native level/difference forecasts, companion roots, lag selection, AR(0), smearing, future-data invariance, missing inputs, mask preservation, rank failure and unstable-fit fallback |
| Saved result verifier | Passed: all targets/origins, source ES outcomes, positive forecasts, all fallback values, loss arithmetic, smearing and provenance |
| Clark–West arithmetic | Passed: adjusted differences, direct Bartlett long-run variance, statistic, normal-tail calculation and within-scenario Holm adjustment |
| Separate real-data NumPy/SVD implementation | 128 forecasts checked across all four scenarios, including first/middle/last dates and first fallback cases; largest absolute log-forecast difference 6.40e-14 |
| Full fresh R run in a separate directory | All 33 CSV result tables byte-identical to the saved canonical run |
| Main forecast reproduction | Original teammate's nine distinct forecast series reproduced to numerical precision |

The independent audit also checks the raw-data main date grid, source variance
values, fitted/omitted row counts, parameter counts, roots and smearing factors.
It uses SVD least squares rather than the R module's QR estimation and never
imports that module. CSV numeric inputs use round-trip parsing so parser rounding
does not become an apparent modelling discrepancy.

Reproduce the ordinary checks with:

```sh
Rscript --vanilla tests/test_var_pipeline.R
Rscript --vanilla scripts/verify_var.R
.venv/bin/python scripts/audit_var.py
```

The optional independent Python audit uses the NumPy/pandas versions in
`requirements-data.txt`; it is not required to execute the R forecasting pipeline.
For a separate fresh run, supply the same output directory to `run_var.R`,
`verify_var.R` and `audit_var.py`.

## Findings that answer the question

The main research question is whether **oil and gold variance history together
improves ES variance forecasts beyond ES history**. Lower log MSE is better.

| Comparison | Result |
|---|---|
| VAR(5) versus persistence | 17.30% lower log MSE |
| VAR(5) versus matched ES AR(5) | 0.64% higher log MSE |
| VAR(15) versus matched ES AR(15) | 0.74% higher log MSE |
| QLIKE, each main VAR versus matched AR | Every VAR has higher loss |
| Main nested forecast tests | No improvement detected; unadjusted one-sided p-values 0.238–0.454, Holm-adjusted about 0.950 |
| RK and suspect-training checks | Neither reverses the main matched-AR finding |
| Corn/gas level VAR(5) versus matched three-market control | 2.27% higher all-target log MSE, with 35 persistence fallbacks |

The five-market extension has a small descriptive advantage over the matched
three-market control on the 700 dates where all extension models fit, but not
over its matched ES AR. This is a selected subset and is reported separately.

Training joint tests show associations, including a combined CL/GC HAC Wald
p-value of about 0.00113 for VAR(5). This is unadjusted exploratory training
inference, conditional on the model and its assumptions. It is not evidence
that adding those markets improves forecasts, and it does not identify causality.
The pipeline does not separately attribute out-of-sample gains to oil alone or
gold alone; its principal forecast comparison adds both together.

## Limits that remain

- Stable fitted dynamics do not imply well specified errors. Residual serial
  dependence and ARCH remain in the level and differenced alternatives.
- ADF/KPSS give conflicting training evidence about level stationarity.
- The normal-reference Clark–West calculation is approximate. Its strongest
  theoretical conditions do not automatically cover this heteroskedastic system
  with many extra coefficients. Newey–West uncertainty is useful but does not
  make the test exact or resolve misspecification. P-values remain exploratory.
- Provider sessions, publication cutoff, contract rolls and flagged quotes have
  not been certified. Statistical future-data invariance is distinct from knowing
  when provider-day observations were available in real time.
- The evaluation period has already been examined; this is not a confirmatory,
  untouched holdout. Do not tune until commodities appear to win.
- The historical smearing factor need not track conditional error dispersion
  accurately. QLIKE is a supporting loss, without a separate significance test.

The defensible conclusion is that the implemented VAR forecasts equity variance
better than persistence, but **we do not find incremental forecasting value from
oil and gold in the specified models, target and evaluation period**. This is a
valid empirical answer, with the above limitations, rather than a reason to
report favourable coefficients as forecasting success.

## Method references checked

Model estimation, lag-selection, companion roots and diagnostic definitions
were checked against the [official vars package manual](https://cran.r-project.org/web/packages/vars/vars.pdf).
The nested squared-error adjustment and its normal-approximation limits were
checked against [Clark and West's original working paper](https://www.kansascityfed.org/documents/5368/pdf-RWP05-05.pdf).
These references support the methods; all numerical findings above come from
the local source snapshot and verified saved outputs. See
[VAR_REPORT_SECTION.md](VAR_REPORT_SECTION.md) for the report integration draft.
