# Cross-market information and equity volatility

Group project for Quantitative Techniques for Financial Economics (EBC4097).

**Research question.** Does commodity and Treasury-market information improve forecasts of
S&P 500 futures realised variance beyond the equity market's own history?

## What is in this folder

| Component | Where | What it does |
|---|---|---|
| VAR, leverage-augmented VAR (LVAR) and common-date HAR/LHAR benchmarks | `VAR_QTFE.ipynb` (fully executed) | Plain VAR(5) versus LVAR(5) with three negative-return inputs, commodity extensions, diagnostics, joint tests, impulse responses and robustness checks |
| HAR and leverage HAR (LHAR) with commodity and Treasury extensions | `HAR_QTFE.ipynb` | Colab notebook; see "Running the HAR notebook" below |
| VAR with calendar controls and a Treasury proxy | `Tim_VAR/` | Equity-only AR(4) versus four VAR extensions; Python script plus an independent R implementation |
| Supporting code | `final_model_data.py`, `var_har_notebook.py`, `var_irf.py`, `final_robustness.py`, `har_return_audit.py`, `config/`, `scripts/`, `tests/` | Data validation, model code, impulse responses, interval estimates, notebook runner and verification |
| Data | `datasets/vol_data_futures_yield_final_version.csv` | Final panel: 3,910 dates, 4 January 2011 to 31 August 2026 |
| Saved results | `reports/final_dataset/var/generated/` | Forecasts, metrics, diagnostics and provenance written by `VAR_QTFE.ipynb` |
| Report figures | `var_figures/` | Figures built from the saved results by `scripts/build_var_figures.py` |

## Design shared by all models

- Target: log realised variance (five-minute) of E-mini S&P 500 futures, one day ahead.
- Initial training sample to 12 July 2023 (3,127 observations); expanding re-estimation on the remaining
  **783 forecast targets** (13 July 2023 to 31 August 2026). Loss: mean squared error.
- BIC on the initial training sample selects **five lags** for the VAR/LVAR system (AIC selects ten and is
  reported as a sensitivity check). The calendar-controlled VAR selects four lags by BIC.
- **LVAR** is a leverage-augmented linear VAR-X: the plain VAR plus three equity downside inputs, the magnitude
  of the negative part of the average return over 1, 5 and 22 days. Each LVAR is compared with a plain VAR
  that has the same lags, sample and forecast dates.
- The original HAR/LHAR notebook uses its own 80/20 splits (778 and 774 targets); common-date HAR/LHAR
  benchmarks on the 783 targets are calculated inside `VAR_QTFE.ipynb`.

## Running and verifying

```sh
.venv/bin/python -m pip install -r requirements-var-notebook.txt
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Use the project Python kernel; outputs are saved in the notebook. Verification checks the final data, code
and output hashes, 33,669 shared forecasts across 43 models, 12,528 lag-sensitivity forecasts and 17,226
independent HAR/LHAR forecast matches. All 42 tests pass.

### Running the HAR notebook

`HAR_QTFE.ipynb` was written for Google Colab. To run it, set the Colab secrets `data_path` (the long-format
export `datasets/realized_variance_futures.csv`) and `fredapi_key` (a free FRED API key) and install
`scikit-learn` and `fredapi`. It then reproduces the reported HAR/LHAR results, except that it rebuilds the
panel one row shorter at the start (3,909 versus 3,910 rows), which moves the baseline LHAR MSE from 0.3254
to 0.3253.

The only changes to this notebook are a one-line fix to a display cell (cell 17 called `.summary()` on a
dictionary) and the removal of repository-owner details from its Colab badge and a commented-out URL. Its code
and functions are otherwise untouched and are read independently by `VAR_QTFE.ipynb` for matched references.

### Running the calendar-controlled VAR

From inside `Tim_VAR/`:

```sh
OPENBLAS_NUM_THREADS=1 python run_analysis.py
```

This rewrites `Tim_VAR/results/` and reproduces the shipped results to floating-point precision. The R implementation
(`source("run_VAR.R")` in R, with the working directory set to `Tim_VAR/`) refits the VAR for every forecast, so
it is slow; its results match the Python results to about 1e-13. See `Tim_VAR/README.md` for details.

## Supporting analyses from earlier stages

These use earlier data and samples and are not used in the final report:

- `R/`, `scripts/run_var.R`, `scripts/verify_var.R`, `tests/test_var_pipeline.R`: an earlier R VAR analysis
  (`Rscript --vanilla tests/test_var_pipeline.R` runs its tests).
- `scripts/verify_har.py`, `scripts/audit_har_returns.py`, `har_forecasts.py`: an earlier audit of the HAR notebook
  and a return-control follow-up on the 809-target sample.
- `volare_data.py`, `volare_review.py`, `scripts/prepare_volare.py`, `scripts/audit_volare_es_cl.py`: preparation and
  quality flags for the VOLARE realised-variance export (`datasets/realized_variance_futures.csv`).
- `GARCH_QTFE.ipynb`, `VAR_GPRD_OIL_GAS.ipynb`, `Group_Project_QTFE_Functions.ipynb`: early exploratory and helper notebooks.
