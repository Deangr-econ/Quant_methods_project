# Equity-return controls and HAR sensitivity — 4 October 2026

**Most of the previously observed LHAR advantage is also available to AR once AR
receives the same equity-return signals.** AR(15) improves MSE by **9.73%** when
those signals are added. LHAR then improves MSE by **0.98%** against this stronger
benchmark. That smaller difference has an exploratory uncertainty interval spanning
zero. The earlier 10.62% improvement against variance-only AR was numerically
correct, but did not isolate the HAR structure from its additional information.

## What was implemented

The [analysis plan](ANALYSIS_PLAN.md) fixed five scenarios, model comparisons and
uncertainty settings before this follow-up run. The earlier results/test sample
had already been inspected; this is not a preregistered confirmatory experiment.
Original data, notebooks and the review decision ledger are unchanged.

AR(5) and AR(15) now each have a comparison version with **exactly the same three
negative-return features as LHAR**: the negative part of the latest ES return,
and negative parts of five-/22-observation mean ES returns. These are not averages
of individually truncated negative returns. Lag orders were not retuned.

All comparisons retain the same 809 targets from 2023-07-13 to 2026-08-31, the
common 22-observation warm-up and expanding estimation. Models use only outcomes
available through the forecast origin. The uncertainty analysis uses paired
squared errors, and all scores below are for log realised variance.

## Main comparison

Lower scores indicate better forecasts.

| Model | MSE | MAE |
|---|---:|---:|
| AR(15) | 0.429689 | 0.494768 |
| AR(15) + return signals | 0.387884 | 0.469960 |
| HAR | 0.427977 | 0.494298 |
| LHAR | 0.384075 | 0.468533 |
| LHAR + oil/gold | 0.385184 | 0.467804 |

Oil/gold still do not improve squared-error performance when added to LHAR,
although MAE improves slightly. We should report the distinction rather than
claiming every loss measure favours the equity-only model.

LHAR has fewer coefficients: 7 including the
intercept versus 19 for AR(15) plus the three return signals. Simplicity is a
reasonable consideration; the present results do not establish that LHAR is
statistically superior to the matched AR.

## Return audit: what is established and what is still uncertain

Every ES open/close in the source is positive and finite. The code verifies the
exact identity (in percentage log-return units):

`close-to-close return = open-to-close return + opening gap`

This validates arithmetic, not the underlying quotes or the meaning of a trading
day. A gap can include genuine market repricing, a contract-price difference,
provider session conventions, or more than one of these.

Kibot documents unadjusted continuous futures, with ES roll rules changing from
seven inclusive trading days before expiry through March 2022 to five from June
2022. Its inclusive convention normally places the newer switch on Monday of
expiry week. This audit uses that historical distinction, rather than applying
the current rule to all years. [Provider rollover documentation](https://www.kibot.com/futures/rollover-rules.html)
The expiry reference is the quarterly third Friday. [Provider expiry documentation](https://www.kibot.com/futures/futures-expirations.html)

The generated schedule is deliberately labelled **approximate**: it counts
weekdays and does not certify holiday-adjusted historical exchange schedules or
VOLARE's exact switch timestamps. The sensitivity neighbourhood includes the
nearest observed ES row and one observation on either side. It is not a cleaned
or back-adjusted return series.

From 2011 onward there are 62 candidate roll dates in the source. Mean absolute
opening gap is about **0.291%** on candidates versus **0.071%** on other ES dates.
This difference is descriptive: newer candidates fall on Mondays, so weekend
repricing is a confounder. For example, the export's 2026-03-16 close-to-close
return is 1.606%, comprising 0.152% open-to-close and a 1.454% opening gap.
That is a case to verify using actual contract identifiers; the gap must not be
labelled entirely artificial on this evidence.

Return windows still average retained ES/CL/GC common observations. Individual
close-to-close returns refer to successive available ES observations. Holiday
matching can therefore omit some individual ES returns from those averages.
This convention is retained for comparison, not certified as a final calendar.

## Five sensitivity scenarios

Each gain compares models **within the same scenario**. Positive numbers favour
the added signals or LHAR; negative commodity gains mean higher MSE.

| Scenario | Add return signals to AR(15) | LHAR vs AR(15) + returns | Add oil/gold to LHAR |
|---|---:|---:|---:|
| Baseline RV5 / close-to-close | 9.73% | 0.98% | -0.29% |
| RV5 / open-to-close throughout | 10.38% | 1.05% | -0.30% |
| RV5 / open-to-close near candidate rolls | 9.95% | 1.00% | -0.29% |
| RK / close-to-close | 10.35% | 0.56% | -0.13% |
| RV5 / suspect training windows omitted | 9.78% | 0.99% | -0.29% |

The open-to-close alternatives remove the measured gap component, including
potentially useful genuine overnight/weekend information. They may still contain
an intraday switch. They are sensitivity checks, **not confirmed corrections**,
and their slightly better scores are not grounds to select a new primary return
series on this already-inspected period.

The RK scenario changes the variance proxy for predictors **and** evaluation
outcomes. Its raw MSE cannot be used to claim superiority to RV5. Within-scenario
rankings and gains are the relevant comparison here.

The suspect-observation scenario conservatively excludes **68 pre-test regression
rows** whose outcomes or 22-observation input windows could be exposed to GC on
2018-03-26, CL on 2020-04-16 and ES on 2021-03-29, including the following ES return.
These are unresolved cases, not confirmed errors. Features are constructed on the
original grid before masking; no lag jumps across deleted source rows. Initial
fitted targets decline from 3,214 to 3,146, while all 809 evaluation targets remain.
This is retrospective sensitivity, not a claim that the flags were known in real
time. Other possible quote/roll problems are not ruled out.

## How uncertain are the differences?

The following are **descriptive 95% circular block-bootstrap percentile intervals**
for percentage MSE gains, using 2,000 paired resamples of length 20 and seed
20261004. The same exercise with lengths 5 and 60 produces the same qualitative
pattern: return signals help, while the small HAR-versus-AR and commodity
advantages/disadvantages are not clearly separated from zero.

| Candidate vs benchmark | Observed gain | Descriptive interval |
|---|---:|---:|
| AR(15) + return signals vs AR(15) | 9.73% | [6.35%, 14.13%] |
| HAR vs AR(15) | 0.40% | [-1.22%, 2.02%] |
| LHAR vs HAR | 10.26% | [6.71%, 14.93%] |
| LHAR vs AR(15) + return signals | 0.98% | [-0.91%, 2.80%] |
| LHAR + oil/gold vs LHAR | -0.29% | [-1.44%, 0.90%] |

Resampling paired consecutive losses preserves local dependence within blocks;
wrapping blocks is the circular-bootstrap convention. [Time-series bootstrap documentation](https://arch.readthedocs.io/en/latest/bootstrap/timeseries-bootstraps.html)
The intervals condition on the fitted forecast experiment: models are not refitted
inside resamples. They rely on losses being sufficiently stable for block
resampling and do not correct prior specification choices, multiplicity, data
issues or structural changes. They are not Clark–West tests and should not be
reported as definitive nested-model hypothesis tests or proof of equality.

The main implication is cautious: LHAR's remaining advantage over a return-matched
AR is uncertain. The equity-return contribution appears much more substantial.

## Are a few observations responsible?

Removing the five largest absolute paired loss contributions **only as a
post-hoc influence diagnostic** reduces AR's return-signal gain from 9.73% to
7.36%. LHAR's gain against plain HAR falls from 10.26% to 7.84%. Thus those gains
are not entirely due to the five most influential contributions.

By contrast, LHAR's advantage against the return-matched AR falls from 0.98% to
0.31%. LHAR also loses to that benchmark in the partial 2023 period, while winning
in 2024, 2025 and partial 2026. This tempers the earlier observation that LHAR beat
variance-only AR in every year. Full scores retain every forecast observation.
The saved influence table supplies exact dates for further session/quote review.

## Reproduce and validation

```sh
.venv/bin/python scripts/audit_har_returns.py
.venv/bin/python -m unittest discover -s tests -v
```

Use the environment in `requirements-har.txt`. Code is in `har_return_audit.py`
and the runner above; core forecasting remains in `har_forecasts.py`. Generated
CSVs and `provenance.json` are local and ignored by Git. They include complete
returns, approximate roll schedules, forecast origins/targets, metrics, yearly
results, paired losses, resampling intervals and excluded training rows.

**16 tests pass**, including matched return features, future-perturbation forecasts,
return identities, historical roll-rule counting, joint resampling and preservation
of target/lag dates when suspect training rows are masked. The baseline reproduces
the preceding HAR audit's forecasts. Provider validation is still outstanding.

## What to do next

1. Obtain/confirm the ES contract identifiers, exact switch timestamps, and daily
   interval definitions; establish a defensible return series and forecast cutoff.
2. Freeze the main comparison. A useful compact design is equity-only HAR/LHAR,
   an AR benchmark with matching return signals, and a matched commodity extension.
   Confirm the research question with the group; interest rates are still absent.
3. Keep this uncertainty and sensitivity work explicitly exploratory. Final report
   wording should separate equity forecasting gains from commodity contribution,
   and avoid claiming a decisive LHAR win against the stronger AR benchmark.
