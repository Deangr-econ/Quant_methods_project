# VAR analysis on the replacement group dataset

This package uses `vol_data_futures_yield_final_version (1).csv`, supplied on 13 October 2026. `data/group_data.csv` is an unchanged byte-for-byte copy with a simpler filename. It supersedes the earlier VAR results for this report section.

## Report files

- `reports/VAR_main_report.docx`: main methodology and results section, within 1.5 pages at the supplied formatting. It occupies two physical pages, with only a short final paragraph on the second page.
- `reports/VAR_appendix.docx`: two pages with model specifications, stability and residual checks, the AIC/BIC graphs, forecast sensitivity and conventional Granger tests.
- `reports/Data_appendix.docx`: two pages on the sample, variable construction, descriptive statistics, stationarity and seasonality.
- Plain-text companions make it easy to merge the prose and tables into the group paper. Figures are also supplied separately as PNG and SVG.

Main text uses 12-point Times New Roman; appendices use 11-point body text. Tables and notes use smaller supporting text. Documents use Letter pages and 1-inch margins. Changing the page setup in the group document can change pagination. Cross-reference and table numbers can be renumbered during integration.

## Common specification

The primary sample has 3,910 observations from 4 January 2011 to 31 August 2026. The initial training cutoff remains 12 July 2023, leaving 3,127 initial training rows and 783 test targets. Model-specific lag losses affect the training regressions only.

The supplied file has no training/test flag. Do not silently replace the fixed cutoff with a new 80/20 split: `floor(0.8 * 3910)` is 3,128, which would move the first test date to 14 July 2023. Colleagues should use an explicit common cutoff if forecasts are to use identical targets.

The target and commodity predictors are the supplied natural logs of futures RV5. The Treasury proxy is `rv_yield_10`, already in basis points squared. The baseline applies ordinary model lags to that supplied column. Forecasts assume that all previous-date observations have become available. Month and weekday indicators enter each equation; their coefficients are estimated only on the available history.

Forecasting uses an expanding estimation sample, one step ahead on retained dates. BIC and AIC are selected from orders 1–20 on the initial full six-variable system, with a common estimation sample across candidate orders. They select four and nine lags respectively. Each specification uses the same order as its equity-only AR comparator.

Models: equity-only AR; equity with oil and gold; equity with natural gas and Treasury variation; equity with all four commodities; and the full six-variable VAR. Persistence uses the previous retained equity log-RV5 observation. Errors are evaluated in log-RV5 units.

The appendix includes two simple sensitivity checks: first differences (forecasts converted back to log-RV5 levels) and an extra retained-observation Treasury delay. Both use the same 783 test dates. For the timing check, its AR comparator uses the same shortened initial history.

## Changes from the earlier data preparation

This is an analysis of the colleagues' supplied panel, without rebuilding or replacing its Treasury proxy. It includes corn. Although the row count matches the earlier panel, the dates are not identical: the new file contains 4 January 2011 and excludes 13 May 2011, relative to the previous VAR panel.

The supplied Treasury proxy is not already availability-delayed. For every change verifiable within the file (3,909 consecutive row pairs), it equals the squared change in the retained yield observations. An audit against the earlier original Treasury file found six dates where that differs from using consecutive observations on the native Treasury calendar. Therefore the data appendix explicitly describes changes between retained dates, including gaps, rather than claiming each value is always a native one-day yield change. No date is removed or value replaced in the primary analysis.

## Run the R implementation

Open R/RStudio and set the working directory to this extracted package folder.

```r
install.packages(c("vars", "urca"))  # only if needed
source("run_VAR.R")
```

The R implementation uses `vars::VAR`, `vars::VARselect`, and `urca` tests. It refits the VAR systems for every expanding forecast and writes outputs into `results_R/`. It also compares its principal MSE results with the included reference results and stops if the discrepancy exceeds 1e-7. It does not overwrite the supplied source data or reference results.

## Reproducibility status

The calculations used for the delivered report were executed in Python using NumPy/SciPy OLS, with the actual executable script included as `run_analysis.py`. An unrestricted OLS VAR is estimated equation by equation; its one-step equity forecast is identical to the equity equation using the same regressors. The initial multivariate fits are also used for lag criteria and stability checks.

The expanding forecast calculations were checked against direct QR least-squares fits at the first and last forecast of each model/check. The maximum difference is recorded in `results/metadata.json`. Data identities, sample boundaries and forecast metric arithmetic were also checked. Report pages were rendered and visually reviewed; layout counts are in `results/layout_validation.json`.

R is unavailable in the execution environment, so `run_VAR.R` is a companion implementation that was **not executed here**. The shipped numeric results come from the executed Python script, not from an unobserved R run. Keep both scripts with the submission if the code used to conduct the analysis is requested.

To rerun the executed calculation, use a Python environment with NumPy, SciPy and pandas:

```bash
OPENBLAS_NUM_THREADS=1 python run_analysis.py
```

`rebuild_reports.py` additionally needs matplotlib and python-docx and regenerates the figures and Word files from the result CSVs. It does not check pagination; render and review Word documents again after changing content or layout.

## Interpreting the checks

Methods are restricted to the course's AR/VAR framework, OLS, information criteria, standard stationarity tests, residual checks and joint F-tests. No bootstrap, robust Granger procedure or formal nested forecast-comparison test is presented.

ADF uses an intercept, no trend and 20 lagged differences. KPSS tests level stationarity with a Bartlett bandwidth of 28. All preliminary tests and seasonal averages use only the initial training sample. Monthly figures use arithmetic means of unlogged RV5 divided by the series' overall initial-training mean; they are descriptive.

Stationarity evidence is mixed and residual serial correlation remains. Conventional Granger F-test p-values are therefore labelled as nominal and interpreted cautiously. Small MSE differences are reported descriptively; the report does not claim statistically significant forecast superiority or structural causality.

The methodology follows topics in the supplied EBC4097 VAR tutorial (seasonal controls, equation-by-equation OLS, information criteria, residual diagnostics and Granger tests) and Unit Roots slides (ADF, KPSS and potentially conflicting results).
