# Quant_methods_project
Group project

## Current final-dataset HAR and VAR results — 13 October 2026

[VAR_QTFE.ipynb](VAR_QTFE.ipynb) is the leverage-extension notebook, fully
executed on `datasets/vol_data_futures_yield_final_version.csv`. The main-model
columns and numerical identity checks pass. See [the current final-data summary](reports/final_dataset/README.md).
The original [HAR_QTFE.ipynb](HAR_QTFE.ipynb) and [Tim_VAR](Tim_VAR/README.md)
are preserved. The only changes to the HAR notebook are a one-line fix to a display cell (cell 17 called
`.summary()` on a dictionary) and the removal of repository-owner details from its Colab badge and a commented-out URL;
its code and functions are otherwise untouched and are read independently for matched references.

`HAR_QTFE.ipynb` was written for Google Colab. To run it, set the Colab secrets `data_path` (the long-format
export `datasets/realized_variance_futures.csv`) and `fredapi_key` (a free FRED API key) and install
`scikit-learn` and `fredapi`. Re-running it on the repository data reproduces the reported HAR/LHAR results,
except that it rebuilds the panel one row shorter at the start (3,909 vs 3,910 rows), which moves the
baseline LHAR MSE from 0.3254 to 0.3253.

The VAR, LVAR and common-date HAR/LHAR benchmarks score the same **783 targets**
with the 12 July 2023 cutoff. BIC selects **five VAR lags**. Oil + gold, oil +
natural gas, individual commodities, corn + gold, no-corn and all-four comparisons
remain. All active VAR/LVAR systems retain every selected market lag.
**LVAR** means leverage-augmented linear VAR-X with three ES downside controls.

All **42 tests** pass. Verification checks 33,669 shared forecasts, 12,528 lag
forecasts and 17,226 independent HAR/LHAR matches. There are zero forecast fallbacks.

```sh
.venv/bin/python -m pip install -r requirements-var-notebook.txt
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Use the project Python kernel; outputs are saved. Current local CSVs/plots are
in `reports/final_dataset/var/generated`. The [report reconciliation](reports/final_dataset/GROUP_REPORT_REVIEW.md)
explains how to combine the calendar-controlled **VAR** with the **LVAR** section and keep each
extension's matched equity benchmark clear. Report figures are in `var_figures/`.
Earlier analyses below use separately
documented data/samples and should not be mixed with this run.

## Earlier R VAR analysis — 4 October 2026

The agreed VAR scope is **ES, WTI oil (CL) and gold (GC)**, with **corn and natural
gas as an extension**. This earlier analysis uses one shared R module and
local repository data. See the [VAR guide](reports/var_final/README.md),
[research design](reports/var_final/research_design.md) and
[report draft](reports/var_final/VAR_REPORT_SECTION.md).

```sh
Rscript --vanilla tests/test_var_pipeline.R
Rscript --vanilla scripts/run_var.R
Rscript --vanilla scripts/verify_var.R
```

Direct R dependency versions are recorded in `requirements-var.R`. The runner
reports missing packages; install them with
`install.packages(c("vars", "urca", "sandwich", "jsonlite", "digest"))` in R.
Generated forecasts, diagnostics, figures and provenance stay local in
`reports/var_final/generated/`. No API key is required. The VOLARE source export
must already be present; see the [data-access guide](datasets/README.md).

This implementation replaced the legacy VAR notebooks for the earlier analysis;
the current Python notebook above is the entry point for HAR-aligned comparisons.
The R path reproduces the original main forecast results and adds robust
joint tests, variance-scale losses, RK/anomaly checks and a matched corn/gas
extension. The forecasts are exploratory because the evaluation period has
already been inspected. Provider session timing and contract/quote validation
remain open.

## HAR performance audit

See [the HAR verification](reports/har_verification/HAR_REVIEW.md) for reproduced
notebook fits and a comparison with AR/VAR on the same 809 forecast targets.
Run `.venv/bin/python scripts/verify_har.py` to regenerate the local results.
The audit distinguishes ordinary HAR from LHAR with equity-return terms and
preserves the original notebook. Install `requirements-har.txt` for the validated
Python dependencies; it extends `requirements-data.txt`.

The [return-control follow-up](reports/har_followup/RETURN_CONTROL_REVIEW.md)
adds the same equity-return signals to AR, audits possible roll effects and runs
five sensitivity scenarios with descriptive uncertainty intervals. Reproduce it
with `.venv/bin/python scripts/audit_har_returns.py`.

## Research data

Prepare **dated RK and RV5 variance panels** from the saved VOLARE futures export:

```sh
python scripts/prepare_volare.py
```

On the current machine, use `.venv/bin/python` in place of `python`. For a fresh
Python environment, install `requirements-data.txt` first. No network access or
API key is needed for preparation; the original VOLARE export must be available.

Read [the data-quality report](reports/volare/DATA_QUALITY_REPORT.md) before fitting
models. Preparation preserves missing entries and flags anomalies; it does not
approve the data for estimation. The [VOLARE data guide](datasets/README.md)
explains outputs and how to load explicit RK or RV5 columns.

The [ES/CL evidence review](reports/volare/ES_CL_REVIEW.md) records the preliminary
assessment of quote anomalies, possible contract switching and calendar gaps.
Reproduce its diagnostic tables with `python scripts/audit_volare_es_cl.py`.
Review annotations never automatically change the modelling panels.

The original FRED setup is also retained: daily S&P 500, Treasury yield, Brent and
VIX data for 2017–2025 can be downloaded with:

```sh
Rscript scripts/download_data.R
```

No API key or extra R packages are needed. See [the data guide](datasets/README.md)
for sources, loading examples and modelling considerations. Downloads stay local;
the retrieval script and source metadata can be shared through Git.
