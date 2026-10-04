# Teammate contribution, received 4 October 2026

This folder integrates the R script dated 3 October and the accompanying expanded
methodology/results draft. The draft remains provisional. The attached message's
requests about literature, report writing and journal rankings are context, not
tasks performed during this code integration.

## Files and execution

- `originals/Group Assignment as per 03.10.R`: exact supplied R file, preserved.
- `Empirical_Methodology_and_Results.html`: exact supplied report draft, preserved.
- `import_manifest.json`: SHA-256 checksums for those originals.
- `var_analysis.R`: portable working version of the R analysis.

From the project root:

```sh
Rscript --vanilla scripts/run_teammate_var.R
Rscript --vanilla scripts/verify_teammate_var.R
```

The runner also works from another directory when given its absolute path. An
optional final argument chooses a different output directory. Default outputs go
to `reports/teammate_var/` and are regenerated on rerun. That folder is ignored by
Git; source code, the originals and this review are tracked. No downloads, API
keys, private Drive files or interactive R workspace are required. The local
`datasets/realized_variance_futures.csv` must be present.

Required R packages: `urca`, `vars`, `sandwich`. If missing, install these explicitly
with `install.packages(c("urca", "vars", "sandwich"))` before running. The validated
versions are recorded in `validated_sessionInfo.txt`; this is a version record,
not an automated environment lockfile. Base R CSV import removes the `rio`
requirement. The Python preparation and existing notebooks remain separate.

Outputs include all forecast dates/origins/training endpoints, nine-model metrics,
paired raw and Clark–West adjusted losses, comparison p-values, annual metrics,
sample dates, incomplete-date exclusions, diagnostic plots, printed diagnostic
output, session versions and run configuration/input hashes. Model estimation
errors stop the run. Successful forecasts are marked `ok`; this indicates execution,
not verified exchange timing or model adequacy. Rolling stability/fallback logging
is still outstanding.

## Integration changes

1. Replaced the author-specific Windows working directory and `data/` path with
   the repository input path.
2. Made duplicate-key, missing-date and positive/finite-variance checks stop on
   invalid inputs instead of merely printing a result.
3. Removed one duplicated AR(15)/VAR(15) forecasting loop and repeated metrics.
4. Reused the supplied AR helper for the main forecasts, including its AR(0)
   intercept-only branch. Updated selected-order labels to reflect actual orders.
5. Added checks that fixed alternative lags match their claimed training choices
   and that the main AR/VAR pair has matching orders for the nested comparison.
   A changed dataset can deliberately stop these checks; reassess the design
   rather than relabelling an unmatched model comparison.
6. Added an execution wrapper and saved outputs, plus independent checks against
   the draft's rounded MSE and Clark–West values and the dated source sample.

The estimators, 2011 start, complete-case ES/CL/GC sample, 80/20 split, expanding
window, log transformation and forecast-loss definitions retain the teammate's
design. Reproduction of its numbers does not validate those design choices.

## Important interpretation and remaining work

**The code models `log(rv5)`, not `sqrt(rv5)`.** Realised volatility is the square
root of realised variance, but the implemented target and all reported losses
are in log variance units. The HTML describes this correctly. Align the eventual
data section with the actual code; no square-root conversion was introduced.
The Python panels use `log(10000 * rv5)`, which differs by the constant
`log(10000)`. Do not mix column units or interpret R's logs as scaled logs.

The contribution studies **ES equity futures, CL oil and GC gold**. This is useful
progress on a commodity forecasting question; it does not answer the original
interest-rate question. Acceptance of the revised scope remains a group decision.

The code deliberately forecasts the next jointly observed row after complete-case
matching. This is explicitly described in the HTML, but matching dates does not
verify aligned trading sessions or availability at the forecast origin. The
September anomaly ledger is not applied here. Starting in 2011 removes early
observations without resolving later quote/roll issues; gold requires review too.

Training-only lag selection, AR/persistence benchmarks and expanding estimation
are implemented. Initial stationarity, stability, serial-correlation and ARCH
diagnostics are present. Residual problems remain limitations, not completed
repairs. The selected lag orders are fixed during forecasting.

The reported test sample has already been inspected. The alternative specifications
and yearly comparisons are exploratory; Holm correction does not create an
untouched test sample. There is no variance back-transformation, QLIKE evaluation,
RK comparison, formal session validation or fitted-model leakage perturbation
test. The verification checks actual dates and first-forecast consistency; it is
not a substitute for that broader leakage test.

See `VERIFICATION.md` for the local reproduction and the scoped checklist credit.
