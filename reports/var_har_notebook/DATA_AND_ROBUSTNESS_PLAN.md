# Data and VAR robustness plan — 7 October 2026

This plan is fixed before computing the new sensitivity results. The evaluation
period and earlier model results have already been inspected; this is an
exploratory analysis, not preregistration or an untouched final holdout.
Settings are in `config/var_robustness.json` and will be hashed with the outputs.

## Fixed comparisons

Keep the frozen five-market commodity calendar, initial 12 July 2023 cutoff,
22-row common warm-up and all 802 evaluation targets. Retain the main RV5,
close-to-close return, training-BIC-selected VAR(5) specification.

Add the previously requested **ES/oil/gold** VAR and its downside version,
plus a matching LHAR, to the shared comparison. Corn/gas versions remain
extensions. All models still use the same five-market comparison calendar, so
market inclusion changes regressors rather than target availability.

Compare AR/VAR(5) with AR/VAR(10), with and without downside controls, using
identical training and forecast dates. Hold the chosen orders fixed throughout
expanding refits. Do not select the final main order by searching the inspected
evaluation period. Report instability/fallbacks and parameter counts.

## Five data scenarios at order five

1. **Baseline RV5:** unchanged source RV5 and close-to-close returns.
2. **Reviewed suspect training windows:** omit regression training rows exposed
   to the three previously discussed GC/CL/ES records, without deleting source
   dates or rebuilding the lag grid. These are unresolved cases, not errors:
   GC 26 March 2018, CL 16 April 2020, ES 29 March 2021.
3. **Broader flag training windows:** apply the same training-row exclusion to
   every post-2011 screening flag except the nine CL observations provisionally
   retained as crisis moves in the existing decision ledger. This deliberately
   broad alternative includes uncertain corn/gas moves. It does not certify
   them as errors or remove stress periods from the main results.
4. **Open-to-close ES returns:** replace the downside-input return by
   `100*log(close/open)` before recomputing its 1/5/22 windows. This removes
   measured opening gaps, including real overnight information, and may still
   include intraday contract changes. It is an alternative, not adjusted prices.
5. **RK proxy:** recompute both variance predictors and outcomes from RK on
   the same dates. Compare gains relative to benchmarks **within this scenario**;
   raw RK and RV5 MSEs measure different outcomes and cannot rank the proxies.

Build every feature on the original source/retained grids first. The conservative
22-observation exposure rule covers source-grid HAR averages, retained-grid
VAR lags, ES downside-return averages and directly flagged system outcomes.
A flagged ES close can affect the following observed ES return as well.
No filling, winsorising, deletion of raw observations, or guessed roll adjustment.

Every scenario still forecasts/scored all 802 targets. Training exclusions are
applied only after restricting outcomes to those known at the forecast origin.
Provide an additional **retrospective evaluation subset** excluding broadly
flagged input/target windows, scoring all models on that same subset. Its scores
are a diagnostic rather than the primary result or a new clean holdout.

## Uncertainty and interpretation

For baseline paired forecast gains, use circular block percentile intervals
with lengths 5/20/60, 2,000 resamples and seed 20261007. Models are not refitted
inside resamples. These describe fixed paired losses under a dependence/stability
assumption; they are not null-centred nested-model tests, model-selection-adjusted
intervals or proof of equality. Report small gains cautiously.

## Provider evidence and remaining limits

The [VOLARE methodology paper](https://arxiv.org/html/2602.19732v1), section 4.1,
describes second-resolution futures bid/ask data and midpoint prices without
outlier filtering. It states that trading sessions and holidays differ by
contract. This does not verify the exact interval, timezone/date labelling,
publication cutoff or contract switching of our daily export.

[Kibot rollover documentation](https://www.kibot.com/futures/rollover-rules.html)
describes unadjusted continuous series and product-specific switch rules. It
cannot reconstruct an individual flagged quote or the exact contracts from our
daily aggregate CSV. Large moves are therefore review candidates, not confirmed
roll jumps. No provider or teammate message is sent as part of this work.

Save a complete post-2011 flag table with opening-gap/open-to-close decomposition,
estimator ratios and review status. Keep unresolved provider facts explicit in
the data section even if the forecasting conclusions are robust.

Sources accessed 7 October 2026. Nothing in these sources is an instruction to
modify the project; they supply evidence for the data review.
