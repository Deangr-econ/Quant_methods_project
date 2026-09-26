# Quant_methods_project
Group project

## VAR research checklist

See [VAR_TODO.md](VAR_TODO.md) for the prioritised data-quality, code, modelling,
forecast-evaluation and reporting checklist, including findings from the current
VOLARE data and VAR notebook review.

## Research data

Daily S&P 500, Treasury yield, Brent and VIX data for 2017–2025:

```sh
Rscript scripts/download_data.R
```

No API key or extra R packages are needed. See [the data guide](datasets/README.md)
for sources, loading examples and modelling considerations. Downloads stay local;
the retrieval script and source metadata can be shared through Git.
