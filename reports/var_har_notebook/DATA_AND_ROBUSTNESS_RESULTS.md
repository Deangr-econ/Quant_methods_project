# VAR data checks and robustness — 7 October 2026

Open **section 10 of `VAR_QTFE.ipynb`** for the flag review, lag table/figure,
sample counts, scenario gains and uncertainty bands. Section 9 remains the main
shared-date forecast comparison. The research model is now explicitly
**ES/oil/gold**, with corn/gas extensions, on the same five-market calendar.

**Finding:** additional lag history improves the observed forecasts, but the
incremental commodity contribution remains small and uncertain. The downside
return contribution survives the data sensitivities. This strengthens a cautious
answer to the research question rather than making a commodity VAR the winner.

## Lag sensitivity

All rows below include identical downside controls and score the same 802 RV5
targets. Lower MSE is better.

| Markets | Order 5 MSE | Order 10 MSE | Reduction from 5 to 10 |
|---|---:|---:|---:|
| ES only (AR benchmark) | 0.371498 | 0.365892 | 1.51% |
| ES/oil/gold, main VAR | 0.374172 | 0.368497 | 1.52% |
| ES plus all four commodities | 0.372801 | 0.365944 | 1.84% |
| ES/gas | 0.370016 | 0.363780 | 1.69% |

All eight tested AR/VAR lag comparisons have lower MSE at order 10; none uses a
fallback. This is observed forecast performance, not proof of an optimal order.
BIC chose five on the initial plain five-market training system; AIC chose ten.
Keep five as the preselected main specification and report ten as the fixed
sensitivity, without selecting a new primary model on the inspected test period.

Complexity rises: the ES/oil/gold downside system estimates 57 coefficients at
order five versus 102 at order ten; the five-market counterpart rises from 145
to 270. Shared lag orders are also imposed on the equity-only benchmark, rather
than independently optimizing its memory.

Commodities still need comparison against the **same-order** equity-only model.
At order five, oil/gold raises MSE by 0.72%; all four raise it by 0.35%; gas alone
reduces it by 0.40%. At order ten, oil/gold still raises MSE by about 0.71%; the
all-four model is almost tied with equity-only AR (slightly worse); gas gives a
small improvement of about 0.58%. Equity-only LHAR's MSE is 0.362110, still lower
than the tested VAR variants, but its advantage over the stronger AR(10) downside
benchmark narrows to about 1.03%. No formal significance claim is made for that
order-ten comparison.

## What was found in the data

The fixed screens identify **20 post-2011 asset-date flags**. Nine CL crisis
observations are provisionally retained in the existing ledger. The other eleven
are unresolved review candidates; the export alone cannot establish errors.

- **Gold, 26 March 2018:** RK/RV5 is about 716.82, with a low well below ordinary
  open/close levels. RV5 and subsampled RV5 are much closer. This suggests a
  quote/estimator concern without proving which daily estimate is correct.
- **ES, 29 March 2021:** the low is approximately half the usual price level;
  RK/RV5 is 12.31. Close-to-close return is ordinary. This is a conservative
  sensitivity case, not a certified close-return error.
- **Corn, 15 July 2013:** the −26.31% close return is mostly the measured opening
  gap (−26.20%). A possible contract transition remains unconfirmed.
- **Gas:** some large moves include a gap, while others occur within the
  recorded open/close interval. For example, 24 October 2024 has a +23.55%
  open-to-close return; changing the ES return convention cannot validate it.
- **Oil, 16 April 2020:** a previously reviewed possible roll-contamination case.
  The remaining flagged oil-crisis observations are not deleted just because
  they are extreme.

The [VOLARE methodology paper](https://arxiv.org/html/2602.19732v1) describes its
futures midpoint processing without outlier filtering. [Kibot](https://www.kibot.com/futures/rollover-rules.html)
documents unadjusted continuous series. Neither supplies the actual bid/ask
sequence or contract identifiers needed to reconstruct these flagged records.
Exact session/date labelling, measurement availability and export-specific
roll handling remain unconfirmed. Sources accessed 7 October 2026.

## Fixed data scenarios at order five

Every scenario keeps the same 802 forecast targets. Exclusions affect training
rows **after** features are built, so they do not join observations across gaps.
A source-grid 22-row window, retained-grid lags/return windows and directly
flagged outcomes are covered. An ES close can affect the following ES return.

Positive gains below favour the added information; negative gains mean worse MSE.

| Scenario | Initial training rows | Gain from downside signals | Add oil/gold | Add all four | Add gas |
|---|---:|---:|---:|---:|---:|
| Unchanged RV5 | 3,165 | +9.27% | −0.72% | −0.35% | +0.40% |
| Reviewed suspect windows omitted | 3,095 | +9.35% | −0.78% | −0.42% | +0.41% |
| Broader non-crisis flag windows omitted | 3,026 | +9.32% | −0.75% | −0.55% | +0.33% |
| Open-to-close ES downside returns | 3,165 | +9.78% | −0.66% | −0.37% | +0.29% |
| RK predictors and outcomes | 3,165 | +9.85% | −0.22% | +0.38% | +0.61% |

Downside information remains useful across these alternatives. Oil/gold does not
improve its matching downside benchmark in any scenario. The tiny all-four gain
changes sign under RK, showing proxy sensitivity rather than establishing that
RK is better: **RK and RV5 raw MSEs score different outcomes**. Open-to-close
returns discard real opening-gap information too and are not roll-adjusted data.
The broad flag scenario may omit valid stress observations and is not a preferred
cleaning policy. Keep all of them as labelled alternatives to the unchanged main run.

A further retrospective diagnostic omits 77 broadly exposed evaluation windows,
leaving **725 shared targets**. Gas's point improvement falls from +0.40% to
+0.12%; oil/gold and all-four commodity gains remain negative. This is not a
new holdout or a reason to remove those observations from primary results.

## How much confidence to put in the small gains

Baseline order-five descriptive 95% circular-block percentile intervals, with
2,000 paired resamples, block length 20 and seed 20261007:

| Comparison | Observed MSE gain | Descriptive interval |
|---|---:|---:|
| Downside AR versus plain AR | +9.27% | [+5.99%, +13.60%] |
| Add oil/gold to downside AR | −0.72% | [−2.02%, +0.66%] |
| Add all four commodities | −0.35% | [−2.09%, +1.46%] |
| Add gas | +0.40% | [−1.22%, +2.01%] |
| Equity LHAR versus downside AR(5) | +2.53% | [+0.86%, +4.20%] |

The commodity intervals span zero; their small point gains/losses are uncertain.
Block lengths 5 and 60 are also saved. These intervals condition on the existing
forecast experiment: no model refits, centred nested-model test or correction
for prior specification choices is performed. The LHAR interval compares with
AR(5), not the stronger AR(10); it does not establish superiority to every VAR.
Persistent/nonstationary losses or breaks would also limit block inference.

## Implementation and validation

The frozen plan is `DATA_AND_ROBUSTNESS_PLAN.md`; settings are in
`config/var_robustness.json`; calculations are in `var_robustness.py`.
Generated `robustness_*.csv` files contain every forecast, exclusion, flag,
sample count, loss, lag comparison and resampling result. They remain local.
Original provider data, review ledger and teammate HAR notebook are unchanged.

**38 tests pass.** Native VAR(10), training-mask chronology/future invariance,
source-grid issues absent from the retained panel, following ES returns and
unaltered source inputs are tested. Fresh notebook execution saves 14 code cells
and five figures. Verification checks all **18,446 main forecasts** across
23 models, **4,812 independent latest-HAR matches**, and **50,526 sensitivity
forecasts**, including raw-proxy identities, exact eligible training counts,
same origin/target dates, metrics, hashes and the 725-target diagnostic subset.
All baseline, sensitivity and lag forecasts have **zero fallbacks** in this run.

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python scripts/execute_var_notebook.py
.venv/bin/python scripts/verify_var_notebook.py
```

## Report-ready interpretation

On shared dates, equity downside information materially improves variance
forecasts, while oil/gold and the broader commodity set show little consistent
incremental forecast value. Longer VAR memory improves observed accuracy, but
does not establish a reliably useful commodity contribution. The data
sensitivities preserve this overall conclusion, with small proxy-dependent
differences. IRFs describe fitted dynamic associations and cannot substitute for
these forecast comparisons. Remaining provider/roll uncertainty, mixed
stationarity evidence, heavy-tailed/dependent residuals and prior test-period
inspection qualify the results; passed software checks do not validate every quote.
