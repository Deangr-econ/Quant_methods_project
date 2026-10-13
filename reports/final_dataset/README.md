# Final-dataset HAR and VAR results — 13 October 2026

**Later same-day update:** the teammate's Colab HAR notebook has since been
pulled/restored. Its unchanged default-split results are distinct from the saved
common-date run described below. For the current report draft, use
[Jake's new LaTeX section](../../latex_report/jakes%20section.tex) and
[the group-report reconciliation](GROUP_REPORT_REVIEW.md). The saved VAR metrics
and their input/model/output hashes remain verified; the earlier whole-HAR
notebook hash and local-execution claim no longer describe the current HAR file.

Both [HAR_QTFE.ipynb](../../HAR_QTFE.ipynb) and
[VAR_QTFE.ipynb](../../VAR_QTFE.ipynb) have been executed in fresh project Python
kernels using only `datasets/vol_data_futures_yield_final_version.csv` as data.
Their saved outputs are the current results. Earlier results remain in their
original directories and are not interchangeable with this run.

## Data readiness and required columns

The supplied CSV contains 3,910 rows and 24 columns, from 4 January 2011 to
31 August 2026. Dates are unique and increasing; numeric values are finite and
complete; all close prices and RV5 values are positive. The supplied log-RV5
columns agree with natural logs of RV5. After the first row, supplied returns
agree with close-to-close log returns, and the yield proxies agree with absolute
and squared yield changes, to floating-point precision.

| Input | Purpose and units |
|---|---|
| `date` | Authoritative retained observation calendar |
| `rv5_ES`, `rv5_CL`, `rv5_C`, `rv5_GC`, `rv5_NG` | Positive realised variances; target is ES natural-log RV5 |
| `close_price_*`, `ret_*` for the five symbols | Validate supplied returns; returns are percentage log returns |
| `dgs10` | Ten-year yield in percent |
| `abs_dyield_10`, `rv_yield_10` | Absolute changes in basis points and squared changes in basis points squared |
| `log_rv5_*` | Supplied logs validated against RV5; can also be derived |

**No additional columns are required for the main models or the yield HAR
models.** The source CSV was preserved unchanged. No older-file values, external
yield joins, imputation or quote corrections were introduced. Variance-window
features are constructed on the final wide calendar, matching the current HAR
notebook. Return controls convert percentage returns to decimal units.

The first supplied return and yield change cannot be independently reconstructed
without the preceding source observation, which is outside this file. They are
preserved; the first return is outside the active downside windows after warm-up.
Large close returns are recorded in
[large_return_flags.csv](var/generated/large_return_flags.csv) as review
candidates, rather than automatically removed or classified as errors.

Optional checks need `open_price_*` for open-to-close returns, `rk_*` for the RK
variance proxy, and open/high/low prices for a full OHLC audit. These are absent.
Earlier source-specific review masks were not reused on this new dataset.
Section 10 therefore reports the supported 5/10-lag sensitivity and paired-loss
bootstrap intervals, with unavailable checks explicitly listed. Numerical
consistency does not independently establish the provider's session timing,
contract handling or completeness against an exchange calendar.

## Common sample and specifications

| Sample | Dates | Rows |
|---|---|---:|
| Supplied input | 4 Jan 2011–31 Aug 2026 | 3,910 |
| Prepared panel after variance warm-up | 3 Feb 2011–31 Aug 2026 | 3,889 |
| Common regression targets | 8 Mar 2011–31 Aug 2026 | 3,867 |
| Initial training targets | 8 Mar 2011–12 Jul 2023 | 3,084 |
| Evaluation targets | 13 Jul 2023–31 Aug 2026 | 783 |

The previous cutoff, 12 July 2023, is retained. Expanding fits use only outcomes
available through each forecast origin. Every scored commodity model uses the
same origins and next-retained-row targets. HAR yield comparisons also score
these 783 targets, using the CSV's embedded yield observations.

BIC on the initial-training five-market plain VAR selects lag 5 from candidates
1–20; AIC selects lag 10. The selected order is fixed across main VAR/LVAR
comparisons. HAC(22) is used for regression inference. HAR uses the latest,
5-observation and 22-observation means of log RV5; VAR uses individual lags.

LVAR is a **leverage-augmented linear VAR-X**: three predetermined ES downside
controls enter every equation. LHAR uses the same controls in the ES equation.
Each control is the magnitude of the negative part of the decimal ES return
averaged over 1, 5 or 22 retained observations, taking the negative part after
averaging. They are not regime-switching models.

All four families include the same ten selected asset sets: equity-only baseline;
oil, gold, corn and natural gas individually; oil + gold; oil + natural gas;
corn + gold; oil + natural gas + gold; and all four commodities. The two daily
restrictions are additional comparisons. These are selected combinations, not
every possible pair and triple.

## Updated forecast results

Log-variance losses on the common 783 evaluation targets; lower is better.

| Model | MSE | RMSE |
|---|---:|---:|
| VAR baseline | 0.368531 | 0.607068 |
| VAR oil + gold | 0.371324 | 0.609364 |
| HAR baseline | 0.363135 | 0.602607 |
| HAR oil + gold | 0.363805 | 0.603163 |
| LVAR baseline | 0.334215 | 0.578113 |
| LVAR oil + gold | 0.336611 | 0.580182 |
| LHAR baseline | 0.323196 | 0.568504 |
| LHAR oil + gold | 0.323604 | 0.568862 |

Downside controls reduce equity-only VAR MSE by 9.31%. Oil + gold increases
LVAR MSE by 0.72% relative to its equity-only baseline; the descriptive bootstrap
interval includes zero. Natural gas reduces LVAR MSE by 0.46%, but its interval
also includes zero. Baseline LHAR reduces MSE by 3.30% relative to baseline LVAR.
The lowest observed core MSE is LHAR oil + natural gas (0.322761), only about
0.13% below baseline LHAR. These rankings are exploratory because the evaluation
period has already been inspected. They do not establish a new model-selection
rule or a causal commodity effect.

See [all shared forecast metrics](var/generated/shared_forecast_metrics.csv),
[matched asset comparisons](var/generated/matched_asset_forecast_metrics.csv),
[paired-loss intervals](var/generated/robustness_intervals.csv), and
[HAR commodity and yield results](har/generated/).

Training diagnostics and stationarity tests are rerun on the new data. Remaining
residual dependence means successful execution and stable dynamics should not
be described as perfect model specification. The generalized IRFs use only the
initial training period and have exploratory pointwise simulation bands.

## Execution and verification

```sh
.venv/bin/python -m pip install -r requirements-var-notebook.txt
.venv/bin/python scripts/execute_har_notebook.py
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Run HAR before VAR because the final VAR verification compares against the
executed HAR outputs and records its notebook hash. The notebook builder is
optional: it regenerates VAR source cells and clears saved outputs, so execution
is required afterwards. Both notebooks use the project `.venv` Python kernel.

All 42 tests pass. Saved-output verification checks both complete executions,
input/code/output hashes, sample alignment, forecast timing and recomputed losses:

- 35,235 shared forecasts across 45 scored models, including persistence;
- 20,358 HAR commodity/yield forecasts across 26 models;
- 17,226 independent HAR/LHAR forecast matches;
- 12,528 lag-sensitivity forecasts and 15 paired-loss interval rows;
- five saved VAR figures and 2,000 accepted training-only IRF simulation draws.

There were zero forecast fallbacks. Generated files remain local under
`reports/final_dataset/har/generated` and `reports/final_dataset/var/generated`.
Audit details and hashes are saved in both provenance files; source SHA-256 is
`ad3b481455b8e8ea4e632e065f7b38cfbb0293ecd8286611c81b5cda7ea5137f`.
Pre-update notebook/code copies are retained locally under
`reports/var_har_notebook/generated/pre_final_dataset_20261013/`.
