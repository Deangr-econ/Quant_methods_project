# Matched HAR–VAR comparison — 7 October 2026

Open `VAR_QTFE.ipynb`: section 1 contains the calendar audit; section 9 contains
the common-date forecast results and independent latest-HAR check.

## What is now comparable

The main question is whether commodity variance adds forecast information beyond
ES history and matching downside returns. Every model in the shared table uses:

- RV5 from 2011 for ES, oil (CL), corn (C), gold (GC) and gas (NG).
- The frozen all-five commodity complete-case calendar, without bond matching.
- The next retained observation's **log ES realized variance** as the target.
- 3,165 initially known target outcomes, through 12 July 2023.
- **802 identical evaluation targets**, 13 July 2023–31 August 2026.
- Expanding refits using only outcomes known through each forecast origin.
- The latest HAR's decimal-unit ES downside controls over 1/5/22 retained rows.

The latest `fit_har_x` function is extracted without running the notebook's
installation/download cells. Its commodity specifications are rerun on the
frozen inputs. Its default model-specific 80/20 split is overridden to reproduce
the fixed cutoff; its returned origin labels are explicitly mapped to target
dates. The independent check matches all **4,010 forecasts** for five LHAR
specifications, with maximum prediction discrepancy below **8.4e-14**.

VAR and HAR still represent variance history differently: individual lags versus
daily/weekly/monthly averages. Their common inputs do not make them the same
model. The bond-augmented HAR results are a separate extension, not part of this
direct commodity comparison. `HAR_QTFE.ipynb` itself is unchanged.

## Why the earlier standalone scores cannot be mixed

The latest HAR preparation joins DGS10 before removing incomplete rows. With
the retrieved snapshot, this removes **232** dates from the commodity panel.
It changes lag histories and the meaning of “next retained observation,” not
merely the number of observations scored.

| Calendar | Prepared rows | Common target rows | Training at fixed cutoff | Evaluation at fixed cutoff |
|---|---:|---:|---:|---:|
| Commodity core, used for matched forecasts | 3,989 | 3,967 | 3,165 | 802 |
| Latest HAR yield join, separate audit | 3,757 | 3,735 | 2,978 | 757 |

The second row uses our fixed cutoff for illustration. The original HAR's
default 80/20 split is recomputed from each model's usable rows, so its standalone
evaluation size and starting date can differ again. Its saved standalone MSE
must not be ranked against our 802-target VAR MSE.

DGS10 is a daily 10-year constant-maturity Treasury yield in percent, sourced
from the Federal Reserve via [FRED](https://fred.stlouisfed.org/series/DGS10).
The original HAR's proxy is `(100 × yield difference)²`, in basis points squared;
it is not squared yield levels or intraday realized variance. The audit reproduces
its diff-before-dropna behaviour without filling missing yields. Provider timing
and the economic interpretation of differences spanning missing dates still
need review if the bond extension is retained for forecasting.

The local input is `datasets/raw/fred_dgs10_2011_2026.csv`; retrieval URL, date,
units and SHA-256 are in `datasets/fred_dgs10_manifest.json`. Retrieve once using
`scripts/fetch_fred_dgs10.py`; model execution thereafter is offline. This is a
retrieved historical snapshot, not historical real-time vintages.

## Verified common-date results

Lower MSE means smaller squared forecast errors in log variance.

| Model | Log-variance MSE | Evaluation targets |
|---|---:|---:|
| Equity-only AR(5) | 0.409476 | 802 |
| Equity-only AR(5) + downside | 0.371498 | 802 |
| All-four-commodity VAR(5) + downside | 0.372801 | 802 |
| Gas-only VAR(5) + downside | 0.370016 | 802 |
| Equity-only asymmetric HAR | 0.362110 | 802 |
| All-four-commodity asymmetric HAR | 0.363237 | 802 |

The finding is unchanged by the reconciliation. Downside information reduces the
equity AR's MSE by about 9.27%. Adding all four commodities to that downside
benchmark raises MSE by about 0.35%. Gas alone lowers it by about 0.40%, a small
exploratory difference. Equity-only asymmetric HAR performs best among the
specifications in this shared table. These comparisons do not establish
statistically significant gains or economic causality.

## Validation

- **30 Python tests pass**, including native VAR/IRF checks, current HAR feature
  and HAC parity, missing-yield/date behaviour, decimal/percentage prediction
  equivalence, explicit origin/target chronology and future-data invariance.
- Fresh Jupyter execution: **13 code cells**, **four reviewed figures**, no errors.
- Saved-output verifier checks source/code/snapshot/output hashes, IRF metadata,
  all **16,040 forecast records** across 20 models and the 4,010 independent HAR
  forecast matches. Every scored model has zero fallbacks in this run.
- Snapshot inputs and generated CSVs remain local; the notebook embeds its
  displayed tables and figures. A local backup preserves the pre-change notebook.

Open data-quality, specification and economic-interpretation tasks remain in
`PROJECT_CHECKLIST.md`. Passing these checks establishes this implementation and
comparison protocol; it does not resolve provider timing, roll effects, residual
dependence or prior inspection of the evaluation period.
