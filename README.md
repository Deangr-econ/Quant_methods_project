# Quant_methods_project
Group project

## Current final-dataset HAR and VAR results — 13 October 2026

Both [HAR_QTFE.ipynb](HAR_QTFE.ipynb) and [VAR_QTFE.ipynb](VAR_QTFE.ipynb)
have been fully executed using `datasets/vol_data_futures_yield_final_version.csv`.
The input passes the main schema, calendar, finite-value and numerical identity
checks. All required main-model and yield-model columns are present.
See [the final-data readiness and results summary](reports/final_dataset/README.md)
for the exact sample, updated scores, supported robustness checks and limitations.

VAR, LVAR, HAR and LHAR now score the same **783 evaluation targets**, with the
existing 12 July 2023 training cutoff. BIC again selects **five VAR lags**.
Oil + gold and oil + natural gas are present in all four families, alongside
individual commodities, corn + gold, no-corn and all-four specifications.
LVAR means leverage-augmented linear VAR-X with three ES downside-return controls.

All **42 tests** pass. Verification recomputes 35,235 shared forecasts,
20,358 HAR commodity/yield forecasts, 12,528 lag-sensitivity forecasts and 17,226
independent HAR/LHAR matches. All scored models have zero forecast fallbacks.

```sh
.venv/bin/python -m pip install -r requirements-var-notebook.txt
.venv/bin/python scripts/execute_har_notebook.py
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Run HAR before VAR. Use the project Python kernel; notebook outputs are saved.
Generated CSVs and plots stay local in `reports/final_dataset/har/generated/` and
`reports/final_dataset/var/generated/`. Earlier outputs are preserved separately.
The following R analyses, HAR audits, data preparation guides and
[older VAR report](reports/var_har_notebook/ASYMMETRIC_VAR_REPORT.tex) document
previous data versions; their numbers are not the final-dataset results.

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
remain open; see [the checklist](VAR_TODO.md).

## Teammate's R analysis

The 3 October contribution and results draft are in [timadditions](timadditions/README.md).
The original files are preserved; a portable version reproduces the draft's
nine-model forecast results using the repository VOLARE data:

```sh
Rscript --vanilla scripts/run_teammate_var.R
Rscript --vanilla scripts/verify_teammate_var.R
```

See the [verification and checklist review](timadditions/VERIFICATION.md) for
validated results and remaining limitations. This is an ES/oil/gold **log-RV5**
analysis; its scope is now recorded above, while provider data treatment and
session timing remain unresolved.

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

## VAR research checklist

See [VAR_TODO.md](VAR_TODO.md) for the prioritised data-quality, code, modelling,
forecast-evaluation and reporting checklist, including findings from the current
VOLARE data and VAR notebook review.

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
