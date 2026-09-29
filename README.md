# Quant_methods_project
Group project

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

The original FRED setup is also retained: daily S&P 500, Treasury yield, Brent and
VIX data for 2017–2025 can be downloaded with:

```sh
Rscript scripts/download_data.R
```

No API key or extra R packages are needed. See [the data guide](datasets/README.md)
for sources, loading examples and modelling considerations. Downloads stay local;
the retrieval script and source metadata can be shared through Git.
