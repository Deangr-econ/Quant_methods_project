# Research data

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
