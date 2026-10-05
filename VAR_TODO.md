# VAR research checklist

Prepared: 26 September 2026. Reviewed project revision: `011333c`.

Purpose: build a defensible, reproducible answer to whether information from other
markets improves forecasts of equity volatility. Better data, valid comparisons
and clear economic interpretation take priority over adding more models.

Items marked `[x]` are completed within the scope recorded in the progress notes.
The canonical VAR is now the shared R pipeline, not the legacy notebooks.
Completed coding does not certify provider data or solve remaining model
limitations. Earlier progress notes describe the state at their own dates.

## Start here

1. Review the [VAR report draft](reports/var_final/VAR_REPORT_SECTION.md) and
   integrate it into the group report; main scope is ES/CL/GC, extension C/NG.
2. Confirm provider session/publication timing and contract handling; adjudicate
   flagged quotes where evidence is available. These are still open.
3. Explain the remaining residual dependence and ARCH. Do not call a stable VAR
   well specified solely because its roots pass.
4. Have another group member reproduce the main result using
   [the VAR guide](reports/var_final/README.md).
5. Reconcile the VAR and HAR sections' target, dates and information rules.

**Priority key:** P0 = prerequisite for trustworthy results; P1 = required for the
main analysis; P2 = extension after the main analysis works. Dependencies are
listed at the beginning of each section.

## HAR-aligned notebook — 5 October 2026

The user's latest request is to match the asymmetric HAR methods and results
layout, including corn and gas. [VAR_QTFE.ipynb](VAR_QTFE.ipynb) is the new
notebook entry point for that comparison; the earlier R analysis remains intact.
See [the matching-methods guide](reports/var_har_notebook/README.md).

- [x] Reproduced the current HAR preparation and actual saved R² values.
- [x] Added plain and downside-augmented VAR families with the same ES return
  terms and HAC(22); added corn/no-corn and daily-restriction tables.
- [x] Used one training-selected lag order, identical fit rows and 802 common
  forecast targets; recomputed matching LHAR controls instead of importing
  scores from a different sample.
- [x] Saved the executed notebook with coefficient tables, residual plots,
  diagnostics, forecast metrics and source/code provenance.
- [x] Passed five focused alignment/forecast checks plus the existing 16 Python
  tests. Native VAR and original LHAR calculations independently agree.

This advances C3's replacement pathway; the original stale notebook is preserved
as legacy rather than repaired in place. Common provider-date matching follows
HAR for compatibility, not provider certification. M5, provider/return validation
and final report/group review remain open. Do not mix 802-target and 809-target
losses or describe full-sample R² as forecast accuracy.

## Canonical VAR completion — 4 October 2026

Owner/reviewer: Codex. Scope confirmed by the user: **ES, oil and gold main VAR;
corn and natural gas extension**. Evidence: [recorded research design](reports/var_final/research_design.md),
[run guide](reports/var_final/README.md), [report draft](reports/var_final/VAR_REPORT_SECTION.md),
`R/var_pipeline.R`, `scripts/run_var.R` and `scripts/verify_var.R`.

- [x] Added one local, configured R path; retained original contribution and
  legacy notebooks. No private Drive imports, API keys or notebook state.
- [x] Executed four scenarios in fresh R sessions: main RV5, RK, retrospective
  suspect-training mask and five-market extension, each on the same 809 targets.
- [x] Added fitted roots/size/status at every origin, explicit persistence
  fallbacks, positive variance back-transforms and QLIKE/variance-scale scores.
- [x] Added joint HAC training tests, saved ADF/KPSS critical values and residual
  diagnostics, yearly losses, influential-date checks and appendix figures.
- [x] Added same-order, same-training-row three-market controls for the C/NG
  extension, plus an explicitly secondary 700-date availability comparison.
- [x] Passed focused R tests and full result verification; original main forecasts
  agree to numerical precision. Existing 16 Python tests also pass. The source
  export is unchanged, and input/output SHA-256 hashes and versions are saved.
- [x] Independently audited 128 real-data forecasts using NumPy/SVD and rebuilt
  Clark–West standard errors directly. A full fresh run reproduced all 33 CSV
  result tables exactly; see [the implementation audit](reports/var_final/IMPLEMENTATION_AUDIT.md).

**Finding:** main VAR(5) has 0.64% higher log MSE than AR(5); VAR(15) is 0.74%
worse than AR(15). RK and the suspect mask do not reverse the finding.
The five-market level VAR(5) invokes 35 persistence fallbacks and is 2.27% worse
than its matched three-market control over all targets. On the 700 dates where
all extension models fit, it is about 0.30% better than that control but remains
worse than matched ES AR. These are exploratory findings, not confirmatory
holdout evidence or causal effects.

R1/R2/R4/R5, D1/D7/D10, C1/C2/C4–C8, M4/M6/M7, F1–F5, I2/I3 and S2/S3 are
completed for this recorded VAR design. C8 refers to fresh R execution, not to
repairing legacy notebooks. D2/D3 and R3/D4–D6/D8 retain provider/coverage review
work. M5 remains open as a model limitation: tested alternatives still reject
whiteness. Five-session forecasts, IRF/FEVD and GARCH are outside the agreed
VAR handover scope. S1/S4/S5 still require report/group work.

## Teammate integration — 4 October 2026

### HAR follow-up — 4 October 2026

**Return-control follow-up completed:** see
[the evidence and sensitivity review](reports/har_followup/RETURN_CONTROL_REVIEW.md).

- [x] Gave AR(5)/AR(15) the exact three LHAR return signals. AR(15)'s MSE improves
  about 9.7%; LHAR's additional advantage is about 1.0%, with an exploratory
  block-bootstrap interval spanning zero. This updates the interpretation of
  the earlier 10.6% gain against variance-only AR.
- [x] Audited ES return arithmetic and approximate historical roll dates, and ran
  return-definition, RK/RV5 and suspect-training-window sensitivities on the same
  809 targets. No return series has been certified as roll-adjusted or corrected.
- [x] Saved paired loss intervals, yearly results and influential-date checks.
  All 16 tests pass, including future-data invariance for the matched AR signals
  and preservation of lag/target dates under the sensitivity mask.

I2/I3/F4 and C7 have advanced for this provisional analysis. The final design,
provider session/contract validation and appropriate final inference remain open.

- [x] Reproduced the HAR notebook's in-sample R² values and separately executed
  its previously unsaved forecast function. Recorded its origin/target label bug
  and fresh-session failures without overwriting the notebook.
- [x] Implemented HAR/LHAR and matched commodity extensions on the same 809
  targets as the R comparison, with a common 22-observation regression warm-up.
  This completes **I6's benchmark implementation for the provisional common-row
  design**. Plain HAR improves MSE only slightly; equity-only LHAR improves MSE
  about 10.6% over AR(15). Commodity extensions slightly worsen MSE.
- [x] Added forecast-level future-perturbation, date/window and invalid-input
  checks; all 12 preparation/review/forecast tests pass.

Evidence: [HAR verification](reports/har_verification/HAR_REVIEW.md). These remain
exploratory results; final calendar, equity-return roll treatment, uncertainty,
anomaly robustness and the research scope remain unresolved. The next modelling
control is a return-augmented AR benchmark. C7/F1 are advanced, not globally closed.

### Imported R contribution

Owner/reviewer: Codex, integrating the teammate's 3 October R contribution.
Evidence: [integration review](timadditions/VERIFICATION.md) and
[run instructions](timadditions/README.md). Original R and HTML files are preserved.

- [x] Imported the draft and made a portable R entry point; removed duplicate
  computation, enforced key/log-input validation and fixed the AR(0) case.
- [x] Reproduced all nine draft MSE values and four Clark–West comparisons on
  809 forecast targets. Saved forecasts, dates, losses, diagnostics and versions.
- [x] Completed **M1, M2, M3, F4 and I1 for the R commodity analysis**, with
  the exact scope and limitations recorded in the integration review.

These checked items credit implemented work, not overall model approval. F4
covers log squared-error inference; F3's proposed variance/QLIKE evaluation remains
open. M2 is an investigation, not a finding that stationarity concerns are solved.
Legacy notebook-specific repairs remain open. Sequential forecasts and several
other tasks have advanced, but incomplete tasks retain unchecked boxes.

The contribution uses **log(RV5), ES/CL/GC, data from 2011, an 80/20 chronological
split and next jointly observed dates**. It does not implement square-root RV,
resolve provider timing/anomalies or settle the original interest-rate hypothesis.
The supplied HTML acknowledges important limits and remains a draft. See the
review for residual diagnostic failures and work still outstanding.

## Preparation progress — 29 September 2026

- [x] Added `scripts/prepare_volare.py` and tracked `volare_data.py`: one local
  preparation command creates separate, dated RK and RV5 panels from the original
  export, retaining source values, missing entries and the initial variance date.
- [x] Added automated coverage/availability checks, fixed anomaly flags, source
  and output hashes, a readable data-quality report and a separate human decision
  ledger. No flags have been treated as confirmed errors or deleted.
- [x] Added six focused checks of duplicates, scale/measure selection, missing-date
  preservation, invalid-log handling, sorting/loading and preparation look-ahead.
  Forecast-level leakage tests remain to be written when forecasts are implemented.
- [x] Documented the command, environment and explicit loader in the README and
  data guide. The notebooks and original exports are preserved.

- [x] Completed a preliminary ES/CL evidence review on 29 September 2026:
  four suspected quote problems, one possible contract-switch problem and nine
  provisionally retained crisis records. Evidence and limits are recorded in
  `reports/volare/ES_CL_REVIEW.md` and the source-bound decision ledger.
- [x] Added `scripts/audit_volare_es_cl.py`: catches 37 jointly missing weekdays
  and 10 dates observed for just one asset, distinguishes coverage boundaries,
  and refuses stale review decisions. Nine preparation/audit tests pass.

**Next:** resolve provider session boundaries and contract-switch treatment,
then write the dated-lag and sensitivity policy before notebook integration.
The initial preparation and preliminary ES/CL review are complete; quote-level
adjudication and a verified exchange calendar remain open. D1–D3, D7, D10 and
C1–C2/C7 are advanced, but broader tasks remain open until all criteria are met.

The later legacy transformed CSV has RV5 columns and no date column; do not
interpret the earlier audit below as validation of that newer file. Use the new
dated outputs for further work. See `reports/volare/DATA_QUALITY_REPORT.md`.

## Historical audit — 26 September 2026, revision `011333c`

- [x] Inspected `realized_variance_futures.csv`: 21,808 asset-date records, five
  instruments (`C`, `CL`, `ES`, `GC`, `NG`), and no duplicate asset-date pairs.
- [x] Checked `volatility_model_QTFE_data.csv`: 4,311 dates from 2009-10-01 to
  2026-08-31, with no duplicate dates, missing values or infinite numeric values.
- [x] Reproduced its returns, kernel variances, scaling and logarithms from the
  original CSV to floating-point precision. This validates arithmetic, not the
  accuracy of the underlying market quotes.
- [x] Identified the current VAR as a model of **logged realised variances**. Its
  filename still mentions GPR, but geopolitical risk is no longer an input.
- [x] Reproduced the saved five-variable VAR(5): 4,306 fitted observations and
  130 regression coefficients. Stability check passes on the current full sample.
- [x] Ran exploratory residual checks: adjusted Portmanteau p-values at 10, 20 and
  30 lags were approximately `4.85e-36`, `8.92e-46` and `2.45e-52`. The current
  specification has substantial residual serial dependence under these tests.
- [x] Ran exploratory ADF/KPSS checks on full-sample log variances. ADF rejects a
  unit root for all five; KPSS rejects level stationarity for C, CL, GC and NG
  (reported boundary p-value 0.01; warnings indicate the true value is lower).
  ES KPSS p-value is approximately 0.085. These conflicting results need diagnosis.
- [x] Checked local `statsmodels` 0.15.0: the existing `result_object=True` calls
  are supported. Do not label them broken merely because older versions differ.
- [x] Confirmed `irf.plot()` defaults to `orth=False`, despite the notebook comment
  saying the responses are orthogonalized. Standard FEVD uses a different,
  orthogonalized decomposition.

These full-sample checks are exploratory. They do not validate forecasts or prove
economic causality, and they must be repeated for the final training specification.

## 1. Research design — P0

Dependencies: none. Output: a short `research_design.md` and shared configuration.

- [x] **R1 — Fix the question and hypotheses.** Original route: Treasury
  yield-change volatility and oil volatility predict equity volatility. Add the
  Treasury data and preserve that hypothesis. Alternative route: commodity
  futures volatility predicts S&P 500 futures volatility. Explicitly document
  that revision. Do not substitute gold or corn for an interest-rate signal.
- [x] **R2 — Name the instruments precisely.** ES is E-mini S&P 500 futures;
  CL is WTI futures, replacing the proposal's cash equity index and Brent spot
  price. Explain why the substitutions suit the economic question. Specify the
  role of every additional commodity before including it.
- [ ] **R3 — Verify the provider timing behind the recorded target.** The current
  target is `log(rv5_ES)` at the next jointly observed ES/CL/GC provider date,
  with RK separate. Provider session boundary, timezone, publication and forecast
  issue time remain unverified. Use predictors available by that time. Do not
  call the statistical common-row horizon the next ES session without validation.
- [x] **R4 — Freeze a chronological evaluation design.** The recorded design
  uses initial history through 2023-07-12 and 809 already-inspected evaluation
  targets through 2026-08-31; fixed initial orders, expanding refits, exploratory
  interpretation. This supersedes the earlier proposed split below. One proposed split is
  training through 2018, validation 2019–2021, and final evaluation 2022–2026-08-31.
  Confirm adequate observations after data checks, then record exact dates and
  refit rules. Never randomly shuffle time-series observations. Full-sample plots
  have already been inspected: describe this honestly, and stop tuning on the
  evaluation period once the design is frozen.
- [x] **R5 — Agree a compact model ladder.** The recorded ladder is selected/matched
  ES AR, persistence, ES/CL/GC level/differenced VAR and a C/NG extension with
  matched three-market controls. This supersedes the earlier suggestions below.
  Start with an ES-only AR benchmark and
  ES+CL VAR. Under the original question, compare ES-only, ES+rate and ES+rate+oil.
  Keep the five-market VAR as a motivated extension. Compare models on identical
  evaluation dates and targets; use a common estimation period for the principal
  incremental-information comparison. Document any separate maximum-history runs.

**Done when:** the question, instruments, horizon, information set, model ladder
and split are written down before model selection resumes.

## 2. Data quality and construction — P0

Dependencies: R1–R3. Outputs: data dictionary, provenance record, anomaly ledger,
sample-flow table and reproducible modelling panels.

- [x] **D1 — Preserve and identify the source snapshot.** Keep the original VOLARE
  export unchanged. Record retrieval date if known, URL, selected assets, sample,
  estimator definitions and file hash. If the historical download date is unknown,
  say so rather than inventing it. The existing FRED manifest does not document
  VOLARE. Update `datasets/README.md`, which currently describes only FRED.
- [ ] **D2 — Write a variable dictionary.** Distinguish `rk` (variance),
  `sqrt(rk)` (standard deviation), `10000*rk` (percentage-return variance) and its
  logarithm. Verify annualisation conventions and session coverage against the
  source. `rv5` means variance based on five-minute intraday sampling, not five-day
  volatility. Do not apply a second rolling variance to `rk` by mistake.
- [ ] **D3 — Build an anomaly ledger.** Flag unusual OHLC ranges, nonpositive
  prices/variances, extreme changes and disagreements across `rk`, `rv5` and
  `rv5_ss`. Record asset, date, evidence, decision, reason and reviewer. Statistical
  flags identify candidates for investigation; they do not establish bad data.
- [ ] **D4 — Resolve the specific flags below.** Compare against another credible
  market-data source or underlying quotes where available. Record unresolved cases
  and assess sensitivity. Switching estimator alone is not a universal repair:
  a bad quote can affect several measures.

| Asset/date | Evidence in the original export | Initial status |
|---|---|---|
| CL, 2009-10-21 | Low 40.7675 versus high 81.985; RK/RV5 ≈ 13 | Investigate |
| CL, 2009-11-13 | Low 38.14 versus high 77.665; RK/RV5 ≈ 125 | Investigate |
| ES, 2021-03-29 | Low 1,983.4375 versus high 3,971.125; RK/RV5 ≈ 12 | Investigate |
| GC, 2009-12-29 | Low 546.475; open/close around 1,100 | Investigate |
| GC, 2018-03-26 | RK/RV5 ≈ 717; unusually low intraday quote | Investigate |
| NG, 2009-11-16 | RK/RV5 ≈ 489; low 2.3125 versus high 4.655 | Investigate |

- [ ] **D5 — Separate errors from economic stress.** Preserve genuine crisis
  observations unless there is evidence of error. Predefine how confirmed errors
  and unresolved cases are handled. Do not winsorise the whole dataset using
  full-sample quantiles, delete inconvenient forecast errors, or remove the whole
  pandemic to obtain cleaner results. Document the treatment of predictor values
  separately from the treatment of evaluation targets.
- [ ] **D6 — Audit the calendar before taking lags.** The source has 4,379 distinct
  dates; 4,369 have both ES and CL, but only 4,312 have all five kernel measures.
  Explain holiday/partial-session differences and unexpected gaps. Define the
  intended session grid and keep actual forecast-origin and target dates. Do not
  silently compress a missing trading session into a one-day lag. If using joint
  sessions deliberately, state that estimand and assess the gaps it creates.
- [x] **D7 — Replace blanket missing-value deletion.** The canonical R path uses
  only required main variances; the extension retains its missing cells on the
  main grid, with no filling. Saved exclusions, fit masks and counts are auditable.
  The legacy pivot contains
  prices, returns and variances, then drops a row if any field is missing. Build
  the VAR panel from its chosen variance columns only. A missing return or an
  unused corn observation should not automatically remove an ES/oil observation.
  For comparisons, separately enforce the agreed common sample and report counts
  before/after each exclusion. Do not forward-fill variance to manufacture data.
- [ ] **D8 — Verify futures rolls and measurement windows.** Determine how VOLARE
  constructs its continuous series and whether switches enter intraday measures.
  For return-based benchmarks, avoid treating cross-contract closing-price gaps
  as economic returns: use a justified same-contract return construction or a
  documented adjustment. The log-variance VAR does not use closing returns, so
  these issues need separate assessment rather than an automatic change to `rk`.
  Confirm that forecasts and realised targets cover comparable time intervals.
**D9 — Not applicable to the confirmed commodity question.** Rates were not
  added or tested. If reverting to the original question, obtain the required
  FRED history, calculate arithmetic yield changes in basis points, and construct
  a backward-looking volatility proxy. Document its window, missing-day policy
  and publication lag. Daily-yield volatility and intraday futures variance are
  different measurements; justify their combination and labels. Never log the
  signed yield change itself.
- [x] **D10 — Save one auditable transformation pipeline.** Generate panels from
  raw inputs plus explicit cleaning decisions; include dates, selected estimator,
  units and exclusion reasons. Reproduce the CSV from a fresh run instead of
  maintaining notebook-specific, manually edited copies.

**Done when:** every inclusion/exclusion can be explained, transformations are
reproducible, and the panel's temporal meaning is unambiguous. VOLARE's documented
high-frequency construction is useful, but its futures use second-resolution
mid-quotes without the stock outlier filter. [VOLARE methodology](https://arxiv.org/html/2602.19732v1#S4.SS1).
Kibot documents unadjusted contract rolls; confirm how this passes through to the
export. [Provider guidance](https://www.kibot.com/futures/continuous-futures.html).

## 3. Repair and simplify the code — P0

Dependencies: design and data decisions above. Output: an analysis that runs from
a fresh checkout/session without private Drive files or hidden notebook state.

- [x] **C1 — Use repository paths.** Canonical R entry points use repository paths;
  Colab notebooks are preserved as legacy work. Replace `userdata.get('data_path')` and the
  private Drive module path with project-relative paths. Keep Colab as an optional
  interface. Remove the FRED API-key requirement from the VOLARE-only path; only
  request/access FRED when that source is actually needed.
- [x] **C2 — Create the actual shared module.** The canonical module is
  `R/var_pipeline.R`; the runner and focused tests source it. The legacy code imports
  `group_project_qtfe_functions.py`, but only a notebook with related functions is
  tracked. Move the required functions into a tracked module and import that
  module consistently. Avoid two independently edited definitions.
- [ ] **C3 — Optional legacy-notebook cleanup, outside the canonical path.** Remove or update `var_df['GAS_RET']`
  in the last VAR cell; neither exists in the revised pipeline. Update GPR/oil/gas
  comments and the notebook name after fixing the research scope. Replace
  “lags 1–15” with the actual configured candidate range (currently up to 30).
- [x] **C4 — Make inputs explicit.** List model variables in a configuration rather
  than selecting every column containing `scaled`. Preserve a deliberate order,
  especially for any orthogonalized decomposition. Make plots adapt to the number
  of variables rather than hard-coding five panels.
- [x] **C5 — Record package versions and run instructions.** The canonical VAR's
  validated R/direct package versions are recorded in `requirements-var.R` and
  the complete installed environment in generated `sessionInfo.txt`; see the
  VAR guide. This is a version record, not a complete dependency lockfile.
- [x] **C6 — Correct interpretation labels.** The canonical stationarity output
  does not label test disagreement as a structural break. In legacy helpers, rename the automatic
  “Contradictory / Structural Break” conclusion to “Conflicting tests; investigate”.
  Opposing ADF/KPSS outcomes do not identify a break. Preserve warnings and report
  KPSS boundary p-values as bounds where appropriate.
- [x] **C7 — Add focused correctness checks.** Check unique sorted dates, finite
  positive variance before logs, unit conversions, exact source reconstruction,
  forecast-origin/target alignment and common comparison dates. Add a leakage
  check: altering observations after a forecast origin must not change the forecast
  or fitted preprocessing at that origin. Test these risks rather than duplicating
  every implementation line in a unit test.
- [x] **C8 — Restart and run all.** Executed canonical scripts with `Rscript --vanilla`,
  then independently verified saved outputs. Legacy notebook execution remains
  outside this handover. The original criterion was to execute the notebook in order in a fresh
  environment, with local data and no existing variables. Save outputs only from
  that run. Record warnings and their resolutions. Any date-frequency warning
  needs explicit forecast-date mapping, not arbitrary calendar reindexing.

**Done when:** another group member can reproduce the data checks and fitted model
using the repository instructions and documented data access.

## 4. Specify and diagnose the VAR — P1

Dependencies: completed modelling panel and reproducible code. Outputs: model
specification, training diagnostics and a concise decision log.

- [x] **M1 — Establish the equity-only comparison.** Fit an AR model to the same
  ES log-variance target and include a simple last-observed-variance forecast.
  A one-variable AR should be fitted with an appropriate univariate estimator,
  not forced through a multivariate VAR interface. An AR using the same lag order
  is a useful restricted comparison; also allow a separately training-selected AR
  so the benchmark is not deliberately weakened.
- [x] **M2 — Investigate stationarity on training data.** Combine time plots, ACFs,
  ADF/KPSS, persistence and possible regime changes. Document deterministic terms
  and test lags. Do not automatically difference all log variances, or add a VECM,
  just to obtain convenient p-values. If differencing is justified, reconstruct
  level forecasts consistently. [VAR requirements](https://www.statsmodels.org/stable/vector_ar.html).
- [x] **M3 — Select lags without future information.** Legacy notebook BIC selection uses
  the entire sample. Restrict selection to the training/validation procedure and
  record the maximum lag, intercept/trend choice and whether lag selection repeats
  at refits. Keep candidate ranges small enough to diagnose and explain. Handle
  a selected lag of zero deliberately rather than breaking forecast code.
- [x] **M4 — Track model size and stability.** Record observations, lag order,
  coefficients and `is_stable()` for each fit. With K variables and an intercept,
  there are `K * (1 + K*p)` regression coefficients. Current K=5, p=5 gives 130.
  Log unstable or failed rolling fits and apply a predefined fallback; do not
  silently discard their forecast dates.
- [ ] **M5 — Address remaining dynamics.** Plot residual ACF/cross-correlations for
  all equations, especially ES, and run multivariate whiteness checks with test
  lags exceeding the fitted VAR lag. The present VAR(5) fails these strongly.
  Investigate data artefacts, lag structure and volatility persistence on training
  data; use a modest alternative or HAR benchmark if justified. Do not increase
  lags indefinitely until one p-value passes. [Whiteness test](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VARResults.test_whiteness.html).
- [x] **M6 — Check heteroskedasticity and distributional fit.** Inspected via
  saved residual/squared-ACF, QQ/histogram and ARCH diagnostics; inference uses
  HAC with explicit asymptotic limitations, and no Gaussian intervals are claimed.
  This documents, rather than removes, heteroskedasticity. Inspect squared
  residual dependence, tails and time-varying dispersion. Non-normal residuals
  do not automatically invalidate point forecasts, but they limit conventional
  inference and Gaussian intervals. Choose inference/bootstrap assumptions that
  address the diagnosed dependence and heteroskedasticity; document limitations.
- [x] **M7 — Test incremental predictive relationships jointly.** In the ES
  equation, jointly test all lags of the proposed added market, conditional on the
  included variables. State the null, sample and test method. Use robust inference
  if required by M5/M6. Avoid selecting isolated significant coefficients or
  interpreting “Granger causality” as identified economic causation.

**Done when:** the chosen dynamics are defensible, remaining diagnostic failures
are explained, and claims match the assumptions actually supported.

## 5. Forecast evaluation — P1

Dependencies: frozen design and viable specifications. Outputs:
`forecasts.csv`, `forecast_metrics.csv`, forecast plots and a run log.

- [x] **F1 — Implement sequential forecasts.** At each origin, fit using observations
  available at or before that time and predict the next target. Start with an
  expanding window and a stated refit schedule. It is valid to update on earlier
  evaluation observations after they become available; it is not valid to use
  later observations. Fit scaling, cleaning thresholds and tuning only within
  the allowed information set. Save origin, target, training end, model and status.
- [x] **F2 — Define log-to-variance conversion.** For a log-variance forecast,
  `exp(predicted_log)/10000` does not generally equal conditional mean variance.
  Specify a bias correction estimated from training information, such as an
  appropriately justified residual smearing factor. Do not use test residuals to
  estimate it. Distinguish log-scale forecasts from mean-variance forecasts.
- [x] **F3 — Score the same target on the same dates.** The recorded exploratory
  design retains log-MSE as primary to match the existing contribution, with
  variance MSE, QLIKE and log RMSE/MAE as supporting losses. It is not a claim
  that the choice preceded all evaluation inspection. For positive observed variance v and forecast h, one QLIKE convention
  is `v/h - log(v/h) - 1`. Keep units consistent and do not substitute volatility
  into a variance formula. Report failed forecasts and missing targets explicitly.
  Robustness of proxy-based scoring relies on assumptions; QLIKE does not repair
  erroneous quotes. [Forecast-loss reference](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf).
- [x] **F4 — Quantify uncertainty in forecast improvements.** Save the paired loss
  series and report average improvements with uncertainty. Choose a test suitable
  for nested versus non-nested models and dependent errors. An off-the-shelf
  Diebold–Mariano test is not automatically appropriate for a nested AR/VAR
  comparison; Clark–West is an option under its squared-error assumptions, not a
  generic replacement for QLIKE tests. [Nested-model reference](https://www.nber.org/papers/t0326).
- [x] **F5 — Prevent multiple-comparison fishing.** Principal comparison recorded,
  all results labelled exploratory, within-scenario Holm adjustment reported;
  no unexamined confirmation sample is claimed. For subsequent work, predeclare the principal model
  comparison. Separate the final test from validation and label exploratory
  comparisons. Report null/negative results: evidence that cross-market signals
  do not improve forecasts is still an answer to the research question.
- [ ] **F6 — Optional five-session extension, deferred.** The current one-step
  common-row horizon is documented and tested. Add a five-session horizon only after
  one-step forecasts work. Distinguish variance on session t+5 from the sum/average
  over sessions t+1 through t+5. Account for overlapping forecast errors in any
  inference. In recursive VAR forecasts, never feed in realised future oil/rate
  observations as though they were known at the forecast origin.

**Done when:** every scored forecast was feasible at its stated origin and all
comparisons use the same information rules, targets and dates.

## 6. Economic interpretation and robustness — P1 / P2

Dependencies: main results exist. Output: a small robustness table and clearly
labelled secondary figures, not an uncontrolled search across specifications.

- [x] **I1 — Explain magnitude, not just significance (P1).** Translate forecast
  improvements into a readable change in prediction error. Where reporting a
  log-variance response d, variance changes by `100*(exp(d)-1)%` and standard
  deviation by `100*(exp(d/2)-1)%`. State horizon and shock normalization; avoid
  presenting a single coefficient as the complete dynamic effect.
- [x] **I2 — Run a short robustness set (P1).** RK, retrospective suspect mask
  and C/NG extension executed on the same targets; estimator/sample differences
  explicitly reported. This set was not preregistered. Compare RK with RV5 or
  subsampled RV5 after anomaly review; assess documented anomaly treatments and
  the small versus extended variable set. Keep evaluation dates comparable and
  disclose when changing the variance estimator also changes the evaluation proxy.
  Add a rolling-window or lag sensitivity check if motivated by diagnostics.
- [x] **I3 — Check whether gains are concentrated (P1).** Show performance across
  prespecified periods and a loss-difference time plot. Determine whether one
  crisis or flagged date drives the conclusion. Report sample sizes and avoid
  definitive claims from small subsamples or treating event timing as causation.
- [ ] **I4 — Repair impulse-response interpretation if retained (P2).** The notebook
  calls `irf.plot(impulse='log_rv_scaled_ES')`, which plots responses to an ES shock,
  not the desired oil-to-equity direction. Specify `impulse`, `response`, shock
  size and `orth` explicitly. Reduced-form, orthogonalized and generalized IRFs
  answer different questions. [Plot defaults](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.irf.IRAnalysis.plot.html).
- [ ] **I5 — Justify identification and uncertainty if using IRFs/FEVD (P2).**
  Cholesky results depend on ordering; the current alphabetical pivot order is
  not an economic justification. Generalized IRFs remove that ordering choice
  but do not identify exogenous causal shocks. Provide appropriate confidence
  bands and ordering sensitivity for retained results. The existing GIRF helper
  provides point responses only. Generalized FEVD requires its own implementation
  and normalization; it is not obtained merely by calling standard `fevd()`.
  Avoid interpreting cumulative log-variance responses as cumulative returns.
- [x] **I6 — Add a strong simple benchmark before more complexity (P2).** A HAR
  model using daily, weekly and monthly variance history can assess whether VAR
  gains simply reflect an inadequate equity-only baseline. Keep definitions of
  averaging and log transformation consistent. Do not replace the entire project
  with a large model competition.
- [ ] **I7 — Repair GARCH only if it is included as a benchmark (P2).** Its current
  `x=...` with `mean='Constant'` ignores the regressors; `x_rate` is absent. The
  benchmark must use valid return construction, the same target window, compatible
  variance units and the same forecast dates. An ARX mean is not a GARCH variance
  extension. Treat this as a separate task, not a repair to the VAR itself.

## 7. Submission and handover — P1

Dependencies: preceding required tasks. Outputs: final report, presentation and
a reproducible code/data-access package.

- [ ] **S1 — Keep the report focused.** Follow the syllabus's 6–8 page limit
  excluding references/appendices: question, economic motivation, data,
  methodology, principal findings, interpretation, robustness/limitations,
  conclusion and division of labour. Put large VAR coefficient tables and
  supporting diagnostics in the appendix.
- [x] **S2 — Produce a minimal evidence set.** Include a data/sample table, time
  plot, benchmark-versus-VAR forecast table and compact robustness table. Add an
  IRF only if its interpretation supports the question and is defensible.
- [x] **S3 — Record reproducibility information.** Save configuration, source
  hashes, dependency versions, random seeds where used, run date and code revision.
  Explain how to acquire data without assuming everyone has a private Drive or
  permission to redistribute provider files.
- [ ] **S4 — Have a second group member reproduce the main result.** Use a fresh
  session and follow the README. Independently trace one forecast from raw inputs
  to target and loss. Confirm that report numbers match saved outputs.
- [ ] **S5 — Prepare for individual questions.** Every member should be able to
  explain the volatility measure, VAR lags, stationarity caveats, data cleaning,
  prediction-versus-causation distinction and out-of-sample results. Work backwards
  from the syllabus's 15 October submission/presentation deadline, allowing time
  for this review rather than adding last-minute models.

## Completion standard

The VAR analysis is ready when the research question matches the data; anomalies
and calendars have an auditable treatment; code runs from a fresh session; model
assumptions and remaining limitations are documented; forecast evaluation avoids
future information; comparisons are fair; and each reported claim is supported
by reproducible evidence. Significant cross-market effects are not a requirement.

## Decision log

| Date | Decision | Reason/evidence | Owner |
|---|---|---|---|
| 2026-10-04 | User confirms ES/CL/GC main; C/NG extension; no rates | R1–R2; research_design.md | User |
| 2026-10-04 | Next main common row; provider session/cutoff still unverified | R3, D6, D8; research_design.md | Codex; provider facts pending |
| 2026-10-04 | Preserve main source; retrospective 22-row suspect exposure sensitivity only | D3–D5; config/var_analysis.json | Codex; quote adjudication pending |
| 2026-10-04 | Preserve 3236/809 split, initial fixed orders, expanding refits, primary log-MSE; exploratory | R4–R5, F3; research_design.md | Codex |
| 2026-10-04 | VAR(5) principal; VAR(15)/differences secondary; stability passes, residual diagnostics fail | M2–M6; VAR_REPORT_SECTION.md | Codex |

## Current file map

| File | Current purpose / issue |
|---|---|
| `datasets/realized_variance_futures.csv` | Original VOLARE export; preserve unchanged |
| `config/var_analysis.json` | Recorded main/extension design and sensitivity policy |
| `R/var_pipeline.R` | Canonical shared VAR/AR estimation, forecast and diagnostic functions |
| `scripts/run_var.R`, `scripts/verify_var.R` | Fresh-session analysis and independent result verification |
| `reports/var_final/` | Research design, reproducible guide and report draft; generated outputs local |
| `datasets/volatility_model_QTFE_data.csv` | Derived panel; recreate through a tracked pipeline |
| `timadditions/var_analysis.R` | Reproduced teammate ES/CL/GC log-RV5 analysis; run with `scripts/run_teammate_var.R` |
| `VAR_GPRD_OIL_GAS.ipynb` | Legacy log-variance VAR; stale name, private imports, full-sample estimation |
| `Group_Project_QTFE_Functions.ipynb` | Shared helper definitions; imported `.py` module is not tracked |
| `GARCH_QTFE.ipynb` | Optional benchmark; variance-regressor implementation needs correction |
| `datasets/README.md` | Existing FRED guide; add separate VOLARE documentation |
| `scripts/download_data.R` | FRED acquisition; retain if using rates or FRED comparisons |

Supporting methodology: [VOLARE documentation](https://volare.unime.it/documentation).
For compatibility checks, consult the installed-version documentation for
[ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)
and [KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html).
