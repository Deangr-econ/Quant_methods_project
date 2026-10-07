# Project analysis checklist

Reviewed 7 October 2026. This review covers the data, code, results and preparation
for explaining the analysis. The group is writing the final report and slides
elsewhere; their progress is outside this checklist.

## Assignment requirements

Source: `context/quant techniques syllabus.pdf`, final-assignment section.

- Submission: **15 October 2026, 23:00**, via the course page.
- Report: **6–8 pages**, excluding references and appendices; submit relevant code.
- Explain the research question, economic motivation, data construction,
  methodology, results, economic magnitudes, robustness/limitations, conclusions
  and division of labour.
- Presentation and discussion: **15 minutes total**.
- Each member receives **one or two individual questions about any part of the
  group analysis**. Understanding only one's own model is insufficient.
- Correct, appropriate analysis and economic reasoning are the main priorities.
  The syllabus does not require adding more model families, using R, selecting a
  particular lag order or obtaining positive forecasting results.

## Where the analysis stands

| Component | Status on 7 October |
|---|---|
| Local Volare export and preparation | Implemented; provider timing, calendar and contract-roll limitations remain |
| VAR/AR and downside specifications | Implemented, including oil, corn, gold and gas comparisons |
| Training-only lag comparison | Implemented for orders 1–20; BIC chooses 5 and AIC 10 for the initial five-market plain VAR |
| Expanding-window forecasts | Implemented, with the existing matched comparison scoring 802 common targets |
| Generalized VAR IRFs and bands | Implemented; five dedicated IRF tests pass |
| Match with the latest HAR notebook | Needs updating: HAR now joins 10-year yield data and has changed preparation/forecast code |
| Fresh saved-notebook verification | Needs repeating after reconciliation; current saved VAR execution counts are out of order |
| Full Python suite | **24 pass, 2 errors**; both errors concern matching the changed HAR reference |
| GARCH contribution, if retained | Needs an implementation and comparability review; oil regressor issue identified below |

The VAR calculations are largely built. The existing tests still check agreement
with native VAR fits/forecasts, forecast timing, future-data invariance, daily
restrictions and IRF calculations. Two broken HAR-reference checks do not prove
that those VAR calculations are wrong, but we cannot currently certify that the
notebook matches the latest HAR or that the saved outputs are a fresh full run.

Earlier completion statements in `VAR_NEXT_STEPS.md` and
`reports/var_har_notebook/README.md` describe the **5 October** state. Their
26-passing-test and exact-HAR-alignment statements are historical.

## Priority 1 — restore a fair, reproducible comparison

- [ ] Freeze the final research-question wording and distinguish the commodity
  core from any separate bond-yield extension. The previously agreed VAR scope
  remains ES/oil/gold with corn/gas comparisons; this audit does not add yields
  to VAR.
- [ ] Specify one common forecasting target, origin/target dates, initial cutoff,
  evaluation dates and information set for direct HAR/VAR comparisons. Models
  using a different sample must have separately labelled results.
- [ ] Resolve the new HAR yield join before claiming identical preparation. Save
  the permitted 10-year yield input locally with source, retrieval date and units
  if the group retains it; avoid a comparison that depends on a live download.
- [ ] Record that the new yield variable is a **squared daily yield change**,
  rather than a squared yield level or intraday realized variance.
- [ ] Reconcile percentage versus decimal return units. Constant rescaling alone
  does not change equivalent unconstrained OLS predictions, but it changes
  coefficient magnitudes and breaks literal coefficient-equality checks.
- [ ] Audit the new HAR forecast date labels: its current function records the
  predictor/origin index while its outcome is the next retained observation.
  Keep origins and target dates explicit, and use common scored outcomes rather
  than independently computing an 80/20 split for each model.
- [ ] Repair the HAR-reference loader and the meaningful alignment tests. One
  current error is an unavailable `dgs10_raw` preparation input; the other is
  parsing the new notebook shell command `!pip install fredapi` as Python.
- [ ] Recalculate the matched comparison after resolving these choices. Do not
  compare the latest HAR's standalone MSE with the older VAR table as if their
  evaluation samples were identical.
- [ ] Execute the final notebook from a fresh kernel, run the full tests and
  saved-output verifier, and refresh provenance after the final changes.

## Priority 2 — finish the data and model checks that matter

- [ ] Document provider session dates, RV5 measurement intervals and when each
  market's measurement is available. Explain the complete-case calendar: “next
  observation” can skip an otherwise observed ES trading date.
- [ ] Review flagged post-2011 prices and contract transitions before assigning
  economic meaning to downside returns. Keep raw data unchanged and do not
  invent observations with zero filling or forward filling.
- [ ] Choose a small, prespecified robustness check for these concerns on a
  clearly documented sample; compare alternatives on the same scored targets.
- [ ] If the group wants a lag robustness result, compare VAR(5) with VAR(10)
  using the agreed forecasting protocol. Treat this as a sensitivity check:
  BIC's preferred training fit does not prove the best out-of-sample forecast.
  An independently selected equity-only AR lag is another useful benchmark
  check. Avoid searching repeatedly for a specification that wins on the already
  inspected test period.
- [ ] Carry mixed stationarity evidence, residual dependence, heavy tails and
  data limitations into the interpretation. Stable conditional roots and HAC
  errors do not establish a perfectly specified or causal model.
- [ ] If GARCH remains in the project, audit its target, dates and regressor
  implementation before including it in a shared forecast ranking. In
  `GARCH_QTFE.ipynb`, `x=x_oil_clean` with `mean="Constant"` is currently
  labelled as a variance regressor, but that `arch_model` setup ignores `x`.
  Changing to a mean model that permits `x` would add a **mean** regressor; it
  would not implement the claimed GARCH variance extension.

GARCH API/source references:
[arch_model documentation](https://arch.readthedocs.io/en/stable/univariate/introduction.html)
and [official implementation](https://arch.readthedocs.io/en/stable/_modules/arch/univariate/mean.html).
The local project environment does not currently have `arch` installed, so this
is a code/API review, not an independently reproduced GARCH execution.

## Priority 3 — make the result easy to defend

- [ ] Export one final, dated comparison table with target definition, sample,
  training/evaluation dates, benchmark and loss units attached.
- [ ] Select a compact IRF figure and explain its shock, response units, horizon
  and exploratory pointwise bands. Generalized IRFs describe fitted dynamic
  associations; they do not identify causal commodity effects.
- [ ] State clearly whether commodity information improves forecasting beyond
  equity history **and matching downside controls**. Do not infer forecasting
  value from an in-sample coefficient or a positive IRF alone.
- [ ] Keep the older three-market/809-target R results distinct from the current
  five-market-calendar/802-target comparison. Refresh the VAR results material
  handed to the report authors; the 4 October `VAR_REPORT_SECTION.md` predates
  the later comparison and IRFs.
- [ ] Do not call tiny descriptive differences statistically significant or
  economically important without supporting evidence. A formal forecast-gain
  claim would need an appropriate comparison test; descriptive conclusions can
  instead acknowledge the uncertainty.
- [ ] Have another member reproduce the final code using the documented local
  inputs and dependencies, without private Drive paths or embedded credentials.

Existing matched-result takeaway, pending the latest reconciliation: equity
downside information helps substantially. Adding all four commodities to the
downside VAR raises forecast MSE by about **0.35%** relative to the matching
equity-only downside benchmark. Gas alone lowers MSE by about **0.40%**. These
small exploratory differences do not establish a reliable forecasting gain.
The weak incremental commodity result is a valid answer to the research
question; improving the project's quality does not require making VAR win.

## Priority 4 — prepare for individual questions

- [ ] Explain one VAR forecast from historical inputs, through fitting, to the
  next-observation prediction and its forecast error.
- [ ] Explain AR versus VAR, the downside controls, restricted versus full VAR,
  variance versus volatility, AIC/BIC, expanding windows and IRFs in plain words.
- [ ] Explain why good historical fit can coexist with little forecast gain,
  and what the data limitations prevent us from concluding.
- [ ] Learn the main HAR mechanism and result, plus GARCH if retained, so any
  member can explain the full group analysis.

Recommended next task: **Priority 1**, before further model additions.

## Verification commands after reconciliation

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
```

Do not rebuild the notebook merely to view its outputs: the builder clears
displayed results. Preserve user edits when reconciling sources and notebooks.
