# HAR-aligned VAR notebook — 5 October 2026

Open `VAR_QTFE.ipynb` at the repository root. All code cells have been executed
in order in a fresh project Python Jupyter kernel; results and figures are saved
inside the notebook. The user's current request is to match the asymmetric HAR
methods, assets and presentation, including corn and natural gas.

## What matches HAR

- RV5, 2011 start, ES/CL/C/GC/NG, percentage close-to-close returns and the exact
  current HAR complete-case preparation.
- Per-asset 5/22-observation variance averages constructed before matching;
  downside-return windows constructed after matching, as in the current HAR.
- The three ES downside controls: negative parts of the latest return and
  five-/22-observation mean returns. This is not the mean of daily negative parts.
- OLS with the same HAC(22) covariance and no small-sample correction for
  regression inference.
- HAR's main plain/asymmetric comparison layout, corn/no-corn matrix, ES
  coefficient summary, residual-time/density/Q–Q/ACF grid and result tables.

The reference section reproduces the current HAR outputs: baseline HAR R²
0.694835, baseline LHAR 0.724021 and no-corn full-horizon LHAR 0.726598.
The later matched tables give every model the same 3,967 target rows.

## What is deliberately different between model families

VAR uses individual lags; HAR uses d/w/m averages. The shared initial-training
five-market VAR BIC selects order 5 from candidates 1–20, fixed for all VAR
comparisons. The downside-augmented system adds the three predetermined ES
return controls to each equation. Those controls are not endogenous market
variables. Its roots describe the conditional VAR dynamics only.

Daily-only commodity versions are restricted systems with commodity coefficients
after lag one fixed to zero; ES retains all five lags. This is the analogue of
HAR's daily-only commodity comparison, not an assertion that their regressors
are identical. The baseline VAR is the univariate AR analogue. R²/AIC/BIC and
likelihood in the fit tables refer to the ES equation; system size is separate.

Original HAR fits use 3,988 rows while LHAR uses 3,967. To make direct comparisons
fair, all new VAR and matched-LHAR descriptive fits use the latter sample. Do
not compare the original unequal-sample AIC/BIC as if they used the same outcomes.

## Shared-date forecasting result

Initial fitted history: 3,165 target rows through 12 July 2023. Evaluation:
802 targets from 13 July 2023 through 31 August 2026. All 19 fitted specifications
and persistence score the same target and origin dates. Orders are training-only;
fits expand using outcomes available through each origin. No future commodity
values or returns enter forecasts. All forecasts in this run have zero fallbacks.

| Model | Log MSE | Log RMSE |
|---|---:|---:|
| Persistence | 0.500185 | 0.707238 |
| Equity-only AR(5) | 0.409476 | 0.639903 |
| Five-market VAR(5) | 0.412453 | 0.642225 |
| Equity AR(5) + downside controls | 0.371498 | 0.609507 |
| Five-market VAR(5) + downside controls | 0.372801 | 0.610574 |
| No-corn VAR(5) + downside controls | 0.371957 | 0.609883 |
| Equity-only asymmetric HAR | 0.362110 | 0.601756 |
| All-four-commodity asymmetric HAR | 0.363237 | 0.602692 |

All-four-commodity VAR MSE is 0.73% higher than equity-only AR. With matching
downside controls, adding all four commodities raises MSE by 0.35%. Adding corn
to the no-corn downside system raises MSE by 0.23%. The all-four downside VAR has
2.63% higher MSE than all-four LHAR on these shared dates. Natural-gas-only
variants have small descriptive improvements over their matching equity-only
controls; report the full table instead of claiming every commodity variant loses.
No new significance test is attached to these exploratory point differences.

The downside controls explain a substantial gain compared with variance-only
models. This does not isolate VAR versus HAR architecture: their variance-memory
features differ even when assets and return controls match.

## Sample and interpretation limits

The prepared HAR calendar has 3,989 dates after 63 dates are excluded, including
the initial per-asset rolling warm-up. The common regressions use another 21
origin rows for downside warm-up and omit the final origin without a next target.
The all-five matching removes seven evaluation targets relative to the older
809-target ES/CL/GC analysis. Different retained dates also change return-window
and lag histories. These scores must not be compared with old absolute losses
as evidence that a new model is better on the same data.

The notebook follows the current HAR calendar for compatibility, without
certifying exchange sessions, measurement intervals or publication timing.
All-market complete cases can introduce sample selection. Raw data and the
original HAR notebook are unchanged; source/code hashes are saved. ES returns
remain unadjusted for contract switches and may contain roll effects. Flagged
quotes are not certified as errors or corrected. Full-sample fits and the
already-examined evaluation period remain exploratory.

Ljung–Box is an unadjusted univariate residual screening test, not a calibrated
multivariate VAR whiteness test; ARCH and tail plots also require cautious
interpretation. HAC errors do not fix residual misspecification. Variance-scale
QLIKE uses historical residual smearing, with its conditional-mean limitations;
there are no Gaussian prediction intervals.

## Training-only IRF curves and the 2011/split audit

Section 8 now shows four commodity-to-ES generalized responses from the initial
five-market downside VAR(5), using 3,165 training outcomes only. Innovations are
one residual SD of commodity log variance, with contemporaneously correlated
innovations; downside controls have the same fixed path in both scenarios.
These conditional responses are ordering invariant, not identified causal effects.
The horizon counts retained common observations. Plot/table percentages
back-transform the log-model path, not a separately estimated arithmetic
conditional-variance mean. The saved table also supplies volatility percentages.

Exploratory 95% pointwise bands jointly simulate OLS coefficients and innovation
covariance using Bartlett HAC(22), including their cross covariance. Seed 20261005;
all 2,000 draws were stable/positive-definite in this run. Conditional point root:
0.978582. This asymptotic construction requires weak dependence and stationarity;
bands do not fix residual misspecification or demonstrate causal significance.

At horizon five, implied ES variance responses are oil +8.31%, corn +3.71%, gold
+8.55% and gas +5.24%. They generally fade; at horizon 20 corn's band includes zero.
Large correlated responses, especially horizon zero, need not imply incremental
forecast value beyond equity history. Shock SDs differ across markets.
Method: [Pesaran–Shin (1998)](https://www.sciencedirect.com/science/article/pii/S0165176597002140).

The raw availability audit finds 25 incomplete all-five dates in 2009–2010 and
42 from 2011 onward, with **no gold-only RV5 dates** in this export. Retaining the
2011 start is reasonable for compatibility/early-sample exclusion but does not
eliminate calendar mismatches or later quote/roll concerns. Missing-market dates
and coverage counts are saved, without imputing RV5 or modifying the raw file.

The frozen initial cutoff gives 79.78% training / 20.22% evaluation, approximately
80/20. Expanding refits are already implemented: first fit 3,165 known target
outcomes; last fit 3,966. Keep the shared cutoff rather than recomputing exactly
80% and changing evaluation dates. A rolling-window sensitivity remains optional.
The focused plan is `VAR_NEXT_STEPS.md` at the repository root.

## Reproduce

Use the environment recorded in `requirements-var-notebook.txt`. The source
export must exist locally; no API key, internet download or private Drive helper
is required. Select the project's `.venv` Python kernel in Jupyter and run all.

For the checked command-line execution:

```sh
.venv/bin/python -m unittest tests.test_var_har_notebook tests.test_var_irf -v
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
```

The executor starts a fresh local Jupyter kernel and saves rich outputs in the
notebook. An execution error raises and never records successful validation.
Some restricted environments require permission for Jupyter's local ports.

`var_har_notebook.py` is the shared module; design settings are in
`config/var_har_notebook.json`. `scripts/build_var_notebook.py` recreates the
template and clears displayed outputs; **do not run it to view results**. Run the
executor afterwards if deliberately rebuilding. Future content edits should be
kept in the generator as well as the delivered notebook.

Ten focused notebook/IRF checks pass, alongside the existing 16 Python checks (26 total).
They verify exact reviewed HAR preparation, identical LHAR coefficients/HAC
covariance, standard VAR fits/forecasts, downside-window definitions, target
chronology, future-data invariance, daily restrictions and common sample sizes.
IRF tests also verify native lag/MA matrices, shock impact and market-order
invariance, the joint-HAC coefficient block against statsmodels, uncertainty
in residual covariance, seed reproducibility and initial-training isolation.

Generated CSVs and provenance remain local in `generated/`. They include the
HAR reference, common-sample fit tables, lag selection, exclusions, stationarity,
joint training tests, diagnostics, every dated forecast and accuracy/gain tables.
The notebook embeds the reviewed tables and figures for sharing without those
CSV files. Follow provider licence rules for redistributing derived information.
