# VAR handover

Updated 4 October 2026. The user confirmed ES/oil/gold as the main VAR and
corn/natural gas as an extension. This directory documents the canonical VAR
implementation; the teammate's originals and legacy notebooks are preserved.

## Reproduce

From the repository root, with the saved VOLARE export present:

```sh
Rscript --vanilla tests/test_var_pipeline.R
Rscript --vanilla scripts/run_var.R
Rscript --vanilla scripts/verify_var.R
```

The additional [implementation audit](IMPLEMENTATION_AUDIT.md) records a full
fresh-run reproduction, independently recalculated forecast-test statistics and
128 real-data forecasts rebuilt using a separate NumPy/SVD calculation. Run
`.venv/bin/python scripts/audit_var.py` for that optional independent check; it
uses the NumPy/pandas environment in `requirements-data.txt`.

The validated environment is R 4.6.1 with vars 1.6.1, urca 1.3.4, sandwich 3.1.3,
jsonlite 2.0.0 and digest 0.6.39. Direct versions are also in
`requirements-var.R`; full installed dependencies are saved in the run's
`sessionInfo.txt`. This is a version record, not a complete package lockfile.
Install missing packages with `install.packages(c("vars", "urca", "sandwich",
"jsonlite", "digest"))`. No internet access or API key is required to run once
packages and source data are available.

An optional output directory can be supplied to both run and verification
commands. Generated files are ignored by Git; documentation, configuration,
module, runner and checks are tracked. For provider acquisition/access details,
see `datasets/README.md`. Do not assume permission to redistribute the export.

## Data and model contract

Read [research_design.md](research_design.md) before interpreting the results.
The source export is read directly and never changed. The main panel uses only
ES/CL/GC RV5 availability, starts in 2011 and retains actual dates. Prices and
returns do not decide eligibility. RK and the extension are aligned to that
same panel; missing corn/gas values are left missing. There is no forward fill.

`config/var_analysis.json` records instruments, dates, lag cap, target,
losses and sensitivity policy. `R/var_pipeline.R` provides the shared estimators.
`scripts/run_var.R` selects orders on the initial history, fits at every origin,
records status and calculates comparisons. Intercepts are included; no trends,
returns, rates, IRFs, FEVD or multi-step forecasts enter this specification.

A failed, unstable or unavailable fit uses last observed ES variance for its
forecast. Those dates remain in headline losses and status counts. Native
package forecasts, roots and lag choices are checked independently in
`tests/test_var_pipeline.R`, together with future-data invariance, smearing,
AR(0), missing predictors, rank failure and anomaly masks. The result verifier
checks every scenario's targets, origins, positive predictions, losses,
original forecast reproduction, matched extension training rows and SHA-256
provenance. It also rejects missing stationarity critical values.

## Outputs

All files below are inside `generated/` after the run.

| File | Purpose |
|---|---|
| `main_variance_panel.csv`, `main_absent_dates.csv`, `sample_flow.csv` | Dated main panel, exclusions and scenario coverage |
| `model_specs.csv`, `*_lag_selection.csv` | Initial lag search and fixed model ladder |
| `*_forecasts.csv` | Each origin/target, history size, predicted log/variance, smearing, roots, fit size and failure reason |
| `forecast_metrics.csv`, `forecast_comparisons.csv` | All-target losses and exploratory nested squared-error comparisons |
| `corn_gas_all_models_available_metrics.csv` | Secondary scores on the 700 targets where all extension models fit |
| `main_on_extension_available_dates_metrics.csv` | Main analysis on those same targets; estimation rows still differ |
| `training_diagnostics.csv`, `stationarity.csv`, `joint_predictive_tests.csv` | Stability, residual tests, ADF/KPSS and joint HAC Wald tests |
| `yearly_metrics.csv`, `*_paired_losses.csv` | Yearly scores and dated loss differences |
| `*_influential_dates.csv`, `*_influence_summary.csv` | Largest loss differences and retrospective leave-five-out checks |
| `fit_status_summary.csv` | Forecast status/reason counts; no failed dates hidden |
| `training_diagnostics.pdf`, `forecast_figures.pdf` | Time plots, ACFs, residual plots and forecast/loss plots for the appendix |
| `sessionInfo.txt`, `provenance.json` | Run time, environment, Git revision and input/output hashes |

In the extension, `VAR_base_match_BIC/AIC` use ES/CL/GC at the same lag and on the
same training rows as the five-market VAR. These isolate the added markets from
changes in historical availability and order. Column `AR` in the comparisons
file names the restricted benchmark; for these two comparisons it is itself a
three-market VAR. Four pairs form each exploratory main/robustness test family;
the extension has six. Holm adjustment is within each scenario, not across all
research conducted by the group. Clark–West inference is withheld when either
forecast series uses fallback predictions.

## Remaining research work

The coding/evaluation handover is complete within this specified VAR design.
It does not certify the source: confirm provider measurement windows,
publication timing, missing sessions and contract switches, and adjudicate
flagged quotes if evidence becomes available. The current historical forecasts
assume completed provider-day predictors are available before the next target;
they do not establish implementable clock-time forecasts.

Residual dependence and ARCH remain, even though dynamics are stable. HAC
training tests and exploratory forecast comparisons do not remove those model
limitations. No Gaussian prediction intervals or structural causal claims are
provided. RK changes the realised proxy as well as the inputs; its absolute
loss level is not directly comparable to the RV5 loss level.

Integrate [VAR_REPORT_SECTION.md](VAR_REPORT_SECTION.md) into the group report,
reconcile its target definition with the HAR section, cite the group's approved
data/method sources, and have another member reproduce the numbers. Keep
provider checks and the final report/handover boxes open in `VAR_TODO.md`.
