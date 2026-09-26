# VAR research checklist

Prepared: 26 September 2026. Reviewed project revision: `011333c`.

Purpose: build a defensible, reproducible answer to whether information from other
markets improves forecasts of equity volatility. Better data, valid comparisons
and clear economic interpretation take priority over adding more models.

This is an implementation checklist, not a record of completed model repairs.
Only the audit items marked `[x]` have been completed. Add an owner and completion
date beside each task as the group works through it; retain evidence in the
specified output. Proposed decisions below still need to be recorded by the group.

## Start here

1. Resolve the research scope: keep interest rates and add their data, or explicitly
   revise the question to commodity signals. The current file cannot test rates.
2. Investigate the flagged observations and establish the trading calendar.
3. Make the analysis run from repository files in a fresh session.
4. Build an equity-only benchmark and a small VAR; diagnose both on training data.
5. Evaluate genuinely forward-looking forecasts before expanding the model.

**Priority key:** P0 = prerequisite for trustworthy results; P1 = required for the
main analysis; P2 = extension after the main analysis works. Dependencies are
listed at the beginning of each section.

## Completed audit: what we know now

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

- [ ] **R1 — Fix the question and hypotheses.** Original route: Treasury
  yield-change volatility and oil volatility predict equity volatility. Add the
  Treasury data and preserve that hypothesis. Alternative route: commodity
  futures volatility predicts S&P 500 futures volatility. Explicitly document
  that revision. Do not substitute gold or corn for an interest-rate signal.
- [ ] **R2 — Name the instruments precisely.** ES is E-mini S&P 500 futures;
  CL is WTI futures, replacing the proposal's cash equity index and Brent spot
  price. Explain why the substitutions suit the economic question. Specify the
  role of every additional commodity before including it.
- [ ] **R3 — Define the outcome and timing.** Recommended first target: next-session
  ES realised variance, modelled as `log(10000 * rk_ES)`. State the session boundary,
  timezone and forecast issue time. Use predictors available by that time. Clarify
  whether “next session” means the next ES session or next jointly active session.
- [ ] **R4 — Freeze a chronological evaluation design.** One proposed split is
  training through 2018, validation 2019–2021, and final evaluation 2022–2026-08-31.
  Confirm adequate observations after data checks, then record exact dates and
  refit rules. Never randomly shuffle time-series observations. Full-sample plots
  have already been inspected: describe this honestly, and stop tuning on the
  evaluation period once the design is frozen.
- [ ] **R5 — Agree a compact model ladder.** Start with an ES-only AR benchmark and
  ES+CL VAR. Under the original question, compare ES-only, ES+rate and ES+rate+oil.
  Keep the five-market VAR as a motivated extension. Compare models on identical
  evaluation dates and targets; use a common estimation period for the principal
  incremental-information comparison. Document any separate maximum-history runs.

**Done when:** the question, instruments, horizon, information set, model ladder
and split are written down before model selection resumes.

## 2. Data quality and construction — P0

Dependencies: R1–R3. Outputs: data dictionary, provenance record, anomaly ledger,
sample-flow table and reproducible modelling panels.

- [ ] **D1 — Preserve and identify the source snapshot.** Keep the original VOLARE
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
- [ ] **D7 — Replace blanket missing-value deletion.** The current pivot contains
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
- [ ] **D9 — Add rates if retaining the original question.** Obtain the required
  FRED history, calculate arithmetic yield changes in basis points, and construct
  a backward-looking volatility proxy. Document its window, missing-day policy
  and publication lag. Daily-yield volatility and intraday futures variance are
  different measurements; justify their combination and labels. Never log the
  signed yield change itself.
- [ ] **D10 — Save one auditable transformation pipeline.** Generate panels from
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

- [ ] **C1 — Use repository paths.** Replace `userdata.get('data_path')` and the
  private Drive module path with project-relative paths. Keep Colab as an optional
  interface. Remove the FRED API-key requirement from the VOLARE-only path; only
  request/access FRED when that source is actually needed.
- [ ] **C2 — Create the actual shared module.** The code imports
  `group_project_qtfe_functions.py`, but only a notebook with related functions is
  tracked. Move the required functions into a tracked module and import that
  module consistently. Avoid two independently edited definitions.
- [ ] **C3 — Fix stale references and names.** Remove or update `var_df['GAS_RET']`
  in the last VAR cell; neither exists in the revised pipeline. Update GPR/oil/gas
  comments and the notebook name after fixing the research scope. Replace
  “lags 1–15” with the actual configured candidate range (currently up to 30).
- [ ] **C4 — Make inputs explicit.** List model variables in a configuration rather
  than selecting every column containing `scaled`. Preserve a deliberate order,
  especially for any orthogonalized decomposition. Make plots adapt to the number
  of variables rather than hard-coding five panels.
- [ ] **C5 — Record package versions and run instructions.** Pin the environment
  actually validated, including Python, pandas, NumPy, statsmodels and plotting
  packages. Pin `arch` if keeping the benchmark. The local 0.15.0 stationarity API
  works; ensure Colab matches or implement a tested compatibility wrapper.
- [ ] **C6 — Correct interpretation labels.** Rename the helper's automatic
  “Contradictory / Structural Break” conclusion to “Conflicting tests; investigate”.
  Opposing ADF/KPSS outcomes do not identify a break. Preserve warnings and report
  KPSS boundary p-values as bounds where appropriate.
- [ ] **C7 — Add focused correctness checks.** Check unique sorted dates, finite
  positive variance before logs, unit conversions, exact source reconstruction,
  forecast-origin/target alignment and common comparison dates. Add a leakage
  check: altering observations after a forecast origin must not change the forecast
  or fitted preprocessing at that origin. Test these risks rather than duplicating
  every implementation line in a unit test.
- [ ] **C8 — Restart and run all.** Execute the notebook in order in a fresh
  environment, with local data and no existing variables. Save outputs only from
  that run. Record warnings and their resolutions. Any date-frequency warning
  needs explicit forecast-date mapping, not arbitrary calendar reindexing.

**Done when:** another group member can reproduce the data checks and fitted model
using the repository instructions and documented data access.

## 4. Specify and diagnose the VAR — P1

Dependencies: completed modelling panel and reproducible code. Outputs: model
specification, training diagnostics and a concise decision log.

- [ ] **M1 — Establish the equity-only comparison.** Fit an AR model to the same
  ES log-variance target and include a simple last-observed-variance forecast.
  A one-variable AR should be fitted with an appropriate univariate estimator,
  not forced through a multivariate VAR interface. An AR using the same lag order
  is a useful restricted comparison; also allow a separately training-selected AR
  so the benchmark is not deliberately weakened.
- [ ] **M2 — Investigate stationarity on training data.** Combine time plots, ACFs,
  ADF/KPSS, persistence and possible regime changes. Document deterministic terms
  and test lags. Do not automatically difference all log variances, or add a VECM,
  just to obtain convenient p-values. If differencing is justified, reconstruct
  level forecasts consistently. [VAR requirements](https://www.statsmodels.org/stable/vector_ar.html).
- [ ] **M3 — Select lags without future information.** Current BIC selection uses
  the entire sample. Restrict selection to the training/validation procedure and
  record the maximum lag, intercept/trend choice and whether lag selection repeats
  at refits. Keep candidate ranges small enough to diagnose and explain. Handle
  a selected lag of zero deliberately rather than breaking forecast code.
- [ ] **M4 — Track model size and stability.** Record observations, lag order,
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
- [ ] **M6 — Check heteroskedasticity and distributional fit.** Inspect squared
  residual dependence, tails and time-varying dispersion. Non-normal residuals
  do not automatically invalidate point forecasts, but they limit conventional
  inference and Gaussian intervals. Choose inference/bootstrap assumptions that
  address the diagnosed dependence and heteroskedasticity; document limitations.
- [ ] **M7 — Test incremental predictive relationships jointly.** In the ES
  equation, jointly test all lags of the proposed added market, conditional on the
  included variables. State the null, sample and test method. Use robust inference
  if required by M5/M6. Avoid selecting isolated significant coefficients or
  interpreting “Granger causality” as identified economic causation.

**Done when:** the chosen dynamics are defensible, remaining diagnostic failures
are explained, and claims match the assumptions actually supported.

## 5. Forecast evaluation — P1

Dependencies: frozen design and viable specifications. Outputs:
`forecasts.csv`, `forecast_metrics.csv`, forecast plots and a run log.

- [ ] **F1 — Implement sequential forecasts.** At each origin, fit using observations
  available at or before that time and predict the next target. Start with an
  expanding window and a stated refit schedule. It is valid to update on earlier
  evaluation observations after they become available; it is not valid to use
  later observations. Fit scaling, cleaning thresholds and tuning only within
  the allowed information set. Save origin, target, training end, model and status.
- [ ] **F2 — Define log-to-variance conversion.** For a log-variance forecast,
  `exp(predicted_log)/10000` does not generally equal conditional mean variance.
  Specify a bias correction estimated from training information, such as an
  appropriately justified residual smearing factor. Do not use test residuals to
  estimate it. Distinguish log-scale forecasts from mean-variance forecasts.
- [ ] **F3 — Score the same target on the same dates.** Use a predeclared primary
  variance loss such as QLIKE, with variance MSE and log-scale RMSE as supporting
  measures. For positive observed variance v and forecast h, one QLIKE convention
  is `v/h - log(v/h) - 1`. Keep units consistent and do not substitute volatility
  into a variance formula. Report failed forecasts and missing targets explicitly.
  Robustness of proxy-based scoring relies on assumptions; QLIKE does not repair
  erroneous quotes. [Forecast-loss reference](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf).
- [ ] **F4 — Quantify uncertainty in forecast improvements.** Save the paired loss
  series and report average improvements with uncertainty. Choose a test suitable
  for nested versus non-nested models and dependent errors. An off-the-shelf
  Diebold–Mariano test is not automatically appropriate for a nested AR/VAR
  comparison; Clark–West is an option under its squared-error assumptions, not a
  generic replacement for QLIKE tests. [Nested-model reference](https://www.nber.org/papers/t0326).
- [ ] **F5 — Prevent multiple-comparison fishing.** Predeclare the principal model
  comparison. Separate the final test from validation and label exploratory
  comparisons. Report null/negative results: evidence that cross-market signals
  do not improve forecasts is still an answer to the research question.
- [ ] **F6 — Match the horizon exactly.** Add a five-session horizon only after
  one-step forecasts work. Distinguish variance on session t+5 from the sum/average
  over sessions t+1 through t+5. Account for overlapping forecast errors in any
  inference. In recursive VAR forecasts, never feed in realised future oil/rate
  observations as though they were known at the forecast origin.

**Done when:** every scored forecast was feasible at its stated origin and all
comparisons use the same information rules, targets and dates.

## 6. Economic interpretation and robustness — P1 / P2

Dependencies: main results exist. Output: a small robustness table and clearly
labelled secondary figures, not an uncontrolled search across specifications.

- [ ] **I1 — Explain magnitude, not just significance (P1).** Translate forecast
  improvements into a readable change in prediction error. Where reporting a
  log-variance response d, variance changes by `100*(exp(d)-1)%` and standard
  deviation by `100*(exp(d/2)-1)%`. State horizon and shock normalization; avoid
  presenting a single coefficient as the complete dynamic effect.
- [ ] **I2 — Run a short planned robustness set (P1).** Compare RK with RV5 or
  subsampled RV5 after anomaly review; assess documented anomaly treatments and
  the small versus extended variable set. Keep evaluation dates comparable and
  disclose when changing the variance estimator also changes the evaluation proxy.
  Add a rolling-window or lag sensitivity check if motivated by diagnostics.
- [ ] **I3 — Check whether gains are concentrated (P1).** Show performance across
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
- [ ] **I6 — Add a strong simple benchmark before more complexity (P2).** A HAR
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
- [ ] **S2 — Produce a minimal evidence set.** Include a data/sample table, time
  plot, benchmark-versus-VAR forecast table and compact robustness table. Add an
  IRF only if its interpretation supports the question and is defensible.
- [ ] **S3 — Record reproducibility information.** Save configuration, source
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
| Pending | Research scope and final instruments | R1–R2 | |
| Pending | Target, session calendar and information cutoff | R3, D6, D8 | |
| Pending | Anomaly policy and unresolved observations | D3–D5 | |
| Pending | Split, model ladder and primary metric | R4–R5, F3 | |
| Pending | Final specification and limitations | M2–M6 | |

## Current file map

| File | Current purpose / issue |
|---|---|
| `datasets/realized_variance_futures.csv` | Original VOLARE export; preserve unchanged |
| `datasets/volatility_model_QTFE_data.csv` | Derived panel; recreate through a tracked pipeline |
| `VAR_GPRD_OIL_GAS.ipynb` | Current log-variance VAR; stale name, private imports, full-sample estimation |
| `Group_Project_QTFE_Functions.ipynb` | Shared helper definitions; imported `.py` module is not tracked |
| `GARCH_QTFE.ipynb` | Optional benchmark; variance-regressor implementation needs correction |
| `datasets/README.md` | Existing FRED guide; add separate VOLARE documentation |
| `scripts/download_data.R` | FRED acquisition; retain if using rates or FRED comparisons |

Supporting methodology: [VOLARE documentation](https://volare.unime.it/documentation).
For compatibility checks, consult the installed-version documentation for
[ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)
and [KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html).
