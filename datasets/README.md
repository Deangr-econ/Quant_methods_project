# Research data

## VOLARE: current preparation pipeline

The original `realized_variance_futures.csv` is the input. The older
`volatility_model_QTFE_data.csv` currently contains RV5 columns without dates;
keep it for reference but do not use it for dated forecast evaluation. The current
`VAR_QTFE.ipynb` uses RV5; the older `VAR_GPRD_OIL_GAS.ipynb` constructs RK.
The pipeline below makes the estimator explicit.

Run from the project root:

```sh
python scripts/prepare_volare.py
```

On the current machine: `.venv/bin/python scripts/prepare_volare.py`. A fresh
environment needs `python -m pip install -r requirements-data.txt`. This stage was
validated with Python 3.13 and uses only pandas and NumPy beyond the standard
library. The source export must already be present; the command does not download
or replace it. To validate the preparation logic:

```sh
python -m unittest discover -s tests -v
```

The new outputs are:

| File | Meaning |
|---|---|
| `processed/volare/volare_rk.csv` | Date plus raw, scaled and logged RK variance for ES, CL, GC, NG, C |
| `processed/volare/volare_rv5.csv` | Equivalent RV5 panel on the same date grid |
| `../reports/volare/DATA_QUALITY_REPORT.md` | Coverage, flag counts, limitations and next steps |
| `../reports/volare/quality_flags.csv` | Automatically flagged observations and reasons; not cleaning decisions |
| `../reports/volare/availability.csv` | Observed/missing status on the source-date union |
| `../reports/volare/provenance.json` | Source/code/output hashes and preparation settings |
| `volare_review_decisions.csv` | Separate human review ledger; never overwritten by preparation |

All dates and source values are retained. Blank entries identify missing values
or undefined logs. The script does not fill gaps, clip extremes, delete rows,
choose an exchange calendar, estimate a model, or select a training period. The
union of observed dates is **not** an official trading calendar: a session missing
from every source series cannot be detected from this union alone.

Rerunning regenerates prepared files and automated reports. Record approved
decisions separately with date, symbol, evidence and reviewer. These decisions
are **not yet applied automatically**; a reviewed cleaning policy is the next
stage. Original provider data and the existing notebooks are left intact.

### ES/CL review and calendar audit

Read [the evidence review](../reports/volare/ES_CL_REVIEW.md), then run
`python scripts/audit_volare_es_cl.py` to reproduce the ES/CL flag evidence,
weekday calendar audit and gap list under `reports/volare/`. This additional
diagnostic catches weekdays absent from both series. Holiday labels are only
candidates, not official closure or session validation.

The decision ledger now contains 14 preliminary Codex assessments: four suspected
quote problems, one possible roll problem and nine provisionally retained crisis
observations. It includes a source SHA-256 for each assessment; the audit rejects
stale source hashes, duplicate decisions and changed screening flags. These
annotations do not clean the data or constitute group approval. The reproducible
counts and code/input/output hashes are in `es_cl_audit_summary.json`.

### Explicit loading for the VAR

Run from the project root (also works after cloning the repository into Colab):

```python
from volare_data import load_var_panel

rk_panel = load_var_panel(measure="rk", symbols=("ES", "CL"))
rv5_panel = load_var_panel(measure="rv5", symbols=("ES", "CL"))

print(rk_panel.head())
print(rk_panel.isna().sum())
```

The returned index is `date`; columns are explicitly named
`log_rk_scaled_ES`, `log_rk_scaled_CL` or the corresponding RV5 names. Missing rows
remain visible. **Do not immediately call `.dropna()` and assume remaining rows
are consecutive trading sessions.** First resolve gaps and the forecast calendar.
The loader does not select lags or use future observations.

### Variable dictionary

| Field pattern | Definition |
|---|---|
| `date` | Provider's observation date; publication time/session boundaries still need confirmation |
| `rk_ES` / `rv5_ES` | Provider's daily variance estimate in decimal-return squared units |
| `rk_scaled_ES` / `rv5_scaled_ES` | Variance multiplied by 10,000, for percentage-return squared units |
| `log_rk_scaled_ES` / `log_rv5_scaled_ES` | Natural log of the positive scaled variance |

The same naming applies to CL (WTI futures), GC (gold), NG (natural gas) and C
(corn). ES is E-mini S&P 500 futures. There are no interest-rate observations in
these panels. No additional annualisation is applied. RV5 uses five-minute
sampling; it is not a five-day measure. This pipeline intentionally does not
construct modelling returns from unadjusted continuous futures closes.

The [report](../reports/volare/DATA_QUALITY_REPORT.md) describes transparent fixed
screening thresholds. They flag potential problems, including genuine crisis
moves and contract switches, without deciding which observations are wrong.
The VOLARE retrieval date is unknown and is recorded as such; preparation time
is recorded separately. [Provider methodology](https://volare.unime.it/documentation).

## FRED DGS10: separate latest-HAR calendar audit

The current VAR notebook uses `raw/fred_dgs10_2011_2026.csv` solely to audit the
latest HAR's bond-data join. It does not add a bond regressor to VAR or remove
bond-missing dates from the shared commodity forecasts. Obtain the public,
key-free snapshot from the project root:

```sh
.venv/bin/python scripts/fetch_fred_dgs10.py
```

Install `requirements-var-notebook.txt` first in a fresh environment. The script
downloads DGS10 from 2011 through the last date of the local Volare export, and
records retrieval time, URL, units, missingness and SHA-256 in
`fred_dgs10_manifest.json`. Model execution uses the saved file offline and
checks its hash. Re-running retrieval deliberately replaces that snapshot and
manifest, so preserve the old pair when comparing vintages.

[DGS10](https://fred.stlouisfed.org/series/DGS10) is the daily 10-year
constant-maturity Treasury yield in percent per annum. Missing yields remain
missing. HAR's squared daily change in basis points is a proxy, not intraday
RV5. The original yield join/difference policy removes 232 observations from
the commodity panel in the 7 October audit. See
`reports/var_har_notebook/HAR_VAR_RECONCILIATION.md` for the separate calendars.

## FRED: original daily-market dataset

Use local CSV files for the analysis and the download script to obtain them. This
keeps the sample consistent across model runs and works with both R and Python.
No FRED account, API key or additional R packages are needed. The script uses
public CSV exports; the separate FRED API requires an API key.

## Obtain the files

From the project root, run:

```sh
Rscript scripts/download_data.R
```

The script downloads the fixed **2017-01-01 through 2025-12-31** sample. It reuses
existing raw files on subsequent runs and rebuilds the combined file offline when
all six raw files are present. It does not automatically replace the saved data.
Archive the raw files and manifest together before deliberately obtaining a new
snapshot. FRED observations can be revised, so downloads on different dates need
not be identical.

- `raw/`: six original, unmodified provider CSV exports.
- `processed/market_levels_2017_2025.csv`: one date-aligned file with readable column names.
- `manifest.csv`: source links, retrieval times, file checksums, coverage, missing counts and ranges.

The raw and processed data are excluded from Git. Public access does not imply
unrestricted redistribution, particularly for S&P/Cboe data; consult each source's
terms before publishing data. Share this script, source links and metadata with
the group. Preserve the original local snapshot for reproducibility.

## Data dictionary and direct access

| Column | FRED series | Units | Intended use |
|---|---|---|---|
| `sp500` | [SP500](https://fred.stlouisfed.org/series/SP500) | Price index, daily close; excludes dividends | Equity returns and volatility outcome |
| `treasury_10y_pct` | [DGS10](https://fred.stlouisfed.org/series/DGS10) | Yield in percent | Main interest-rate signal |
| `treasury_2y_pct` | [DGS2](https://fred.stlouisfed.org/series/DGS2) | Yield in percent | Alternative maturity |
| `treasury_5y_pct` | [DGS5](https://fred.stlouisfed.org/series/DGS5) | Yield in percent | Alternative maturity |
| `brent_usd_per_barrel` | [DCOILBRENTEU](https://fred.stlouisfed.org/series/DCOILBRENTEU) | Spot price, USD/barrel | Energy signal |
| `vix` | [VIXCLS](https://fred.stlouisfed.org/series/VIXCLS) | Option-implied volatility index | Optional predictor/benchmark |

For manual access, open the source link, select the date range, and choose
**Download → CSV**. The exact download URLs used are also recorded in the manifest.

## Open in R or Python

Run from the project root. R (no extra packages):

```r
market <- read.csv("datasets/processed/market_levels_2017_2025.csv")
market$date <- as.Date(market$date)
head(market)
```

Python (pandas, already used in the existing notebook):

```python
import pandas as pd
market = pd.read_csv(
    "datasets/processed/market_levels_2017_2025.csv", parse_dates=["date"]
)
market.head()
```

## Before modelling

- This file contains **levels**, not returns, volatility or lagged predictors.
- The outer join retains dates from any series. Missing values are blank. No
  forward filling, interpolation, winsorising or complete-case deletion is applied.
- Calculate S&P returns on its trading calendar before merging predictors. Dropping
  all incomplete panel rows before calculating returns can inadvertently produce
  multi-day returns labelled as daily returns. Investigate gaps in each source.
- For equity/oil, use log price changes. For yields, use arithmetic changes:
  `100 * (yield_today - yield_previous)` gives basis points because yields are stored
  in percent. Yield-change volatility is not bond-return volatility.
- Dates identify observations, not their release times. In particular, EIA oil data
  may be published after the observation date. Establish source availability and
  lag predictors accordingly before claiming a real-time forecast. Downloaded
  historical data are not a point-in-time vintage database.
- FRED supplies a moving ten-year window for SP500. The script checks coverage and
  stops if the requested sample is no longer available. Keep the saved snapshot.
- Daily-return volatility is a proxy, not intraday realised volatility. VIX is
  implied volatility and should not replace the realised outcome.

Source documentation: [FRED downloads](https://fredhelp.stlouisfed.org/fred/data/downloading/using-the-download-data-link/)
and [FRED API keys](https://fred.stlouisfed.org/docs/api/api_key.html).
