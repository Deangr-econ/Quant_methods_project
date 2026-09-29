# ES and CL evidence review

Reviewed 29 September 2026 by Codex. This is a preliminary evidence assessment,
not group approval or certification of the provider data. Original source SHA-256:
`face904a9aeb062796d8fb2c2d17c7e2a2df6f7ecfdca9e473232ddebecacb8f`.

**Result: 14 flagged records reviewed; four suspected quote problems, one possible
contract-switch problem, and nine crisis-period observations provisionally
retained. No values have been corrected, removed or imputed.** Public sources
corroborate market context and some schedules, not the exact underlying quotes.

## 1. Four suspected quote problems

These values come from the local export. Prices and variance ratios are rounded
for display; the generated evidence CSV retains full precision.

| Date | Instrument | Open | Close | Low | High | RK / RV5 |
|---|---|---:|---:|---:|---:|---:|
| 2009-10-21 | CL | 78.685 | 80.915 | 40.7675 | 81.985 | 12.97 |
| 2009-11-13 | CL | 76.955 | 76.5225 | 38.1400 | 77.665 | 124.71 |
| 2009-12-09 | CL | 73.005 | 70.630 | 35.3575 | 73.870 | 8.50 |
| 2021-03-29 | ES | 3946.125 | 3964.375 | 1983.4375 | 3971.125 | 12.31 |

Near-half-price lows alongside relatively ordinary open/close levels are
suspicious. RK also differs substantially from RV5; RV5_SS is much closer to
RV5 in these four cases. The December CL record matters even though its ratio
does not cross the screening threshold of 10: the price-range screen catches it.

One possible explanation is a bad bid or ask entering a midpoint, but the daily
file cannot establish that mechanism. The VOLARE paper describes one-second
futures midquotes without outlier filtering. That makes quote-level investigation
relevant; it does not prove these four observations are errors. [S1](https://arxiv.org/html/2602.19732v1)

**Decision:** mark as `suspected_quote_error_unresolved`. Keep the original values
and do not replace RK with RV5 selectively: a quieter estimate is not ground truth.
Resolution requires the underlying bid/ask sequence or a provider correction,
with the same contract and session definition.

## 2. Possible contract switch: CL, 16 April 2020

The export records an open of 20.015 and close of 26.515, with RK = 0.084153
and RV5 = 0.086670 (rounded). Here the estimators agree closely, despite a large
change in price level.

Kibot describes unadjusted continuous futures and a fixed CL rollover rule three
trading days before expiration. Current documentation does not establish the
historical switch timestamp used in this export. [S2](https://www.kibot.com/futures/rollover-rules.html)

CFTC staff report that May WTI became non-active at 18:00 Eastern on 16 April,
the start of the 17 April trade date (footnote 38, printed page 9; PDF page 11).
This is an exchange active-month convention, not proof of Kibot's switch. It
nevertheless gives a specific time and contract transition to investigate. [S3](https://www.cftc.gov/media/5296/InterimStaffReportNYMEX_WTICrudeOil/download)

**Inference, not confirmation:** if VOLARE's daily interval contains a switch
between differently priced contracts, the artificial return could affect both
RK and RV5. Agreement between estimators would then fail to detect the problem.
The daily aggregates do not identify the contract or switching time.

**Decision:** `possible_roll_contamination_unresolved`. Do not subtract a guessed
roll return from a daily variance. Ask for contract identifiers, timestamps and
the estimator's treatment of transitions; extend the check to other roll dates.

## 3. Nine crisis-period observations retained provisionally

CL dates: **2020-03-09, 2020-03-18, 2020-03-19, 2020-04-21, 2020-04-22,
2020-04-23, 2020-04-27, 2020-04-28 and 2020-04-29**.

These dates have extreme unadjusted close changes, but local RK/RV5 ratios range
from about 0.85 to 1.20. April 21 also triggers the low-price screen. Unlike the
four cases above, the estimators broadly agree and the extreme observations
occur amid the documented oil-market crisis.

CFTC documents the exceptional conditions through April 21, including the May
contract's negative settlement on April 20. Its report does not validate later
April observations. [S3](https://www.cftc.gov/media/5296/InterimStaffReportNYMEX_WTICrudeOil/download)
EIA's April 27 discussion documents storage constraints and continuing risks for
the June contract. This is context, not verification of every listed daily
high, low or variance. [S4](https://www.eia.gov/todayinenergy/detail.php?id=43495)

**Decision:** `retain_crisis_move_provisional`. Extremeness alone is insufficient
reason to delete economically important stress periods. Exact quote/session and
roll checks remain relevant. The absence of negative prices in a continuous
series is not itself an error: the contract selected matters.

## 4. Calendar review

The audit examines every weekday from the first ES/CL source date to the last,
plus any observed weekend dates. This is a diagnostic grid, **not a chosen trading
calendar**. All findings below refer to this source snapshot.

| Finding | Dates/count | Interpretation and evidence strength |
|---|---|---|
| ES starts later than CL | 2009-09-28 and 2009-09-29 absent for ES | Coverage boundary; ES starts September 30. Not an internal gap. |
| ES absent, CL present | 2011-12-26 and 2012-01-02 | Observed Christmas/New Year dates. Possible evening-session/date-label mismatch; historical intraday coverage remains unresolved. |
| CL absent, ES present | 2010-04-02, 2012-04-06, 2015-04-03, 2021-04-02, 2023-04-07, 2026-04-03 | All are Good Fridays. Product schedules can differ; exact hours checked directly for 2023 below, not certified for every year. |
| Both absent on a weekday | 37 dates | Every date matches Christmas, New Year or Good Friday, including observed dates. Calendar-date matching alone does not verify exchange closure. |
| Weekend observations | 0 | Describes the export, not all exchange trading activity. |

The CME schedule explicitly shows equities reopening Thursday evening for the
7 April 2023 trade date and closing Friday at 08:15 Central; energy is closed
after Thursday. This supports a legitimate ES/CL availability difference.
The document's generic URL currently contains the **2023** schedule; do not assume
it applies to 2026. [S5](https://www.cmegroup.com/files/good-friday.pdf)

An unchanged settlement price is not evidence that no intraday trading took
place. Do not fabricate zero variance from repeated settlement values. Nor can
the source date alone establish whether late-evening trading belongs to that
calendar day or the next exchange trade date.

**Decision:** preserve missing entries. The 10 dates with only one asset and
37 weekdays with neither are enumerated in `es_cl_calendar_gaps.csv`. The code
leaves `calendar_verified=False`, including on holiday candidates. A generic
weekday calendar must not be used automatically to create model lags.

## 5. What this means for the VAR

1. **Keep separate RK and RV5 specifications.** Use the same instruments, target
   dates and forecast design for estimator comparisons. Switching estimators
   cannot by itself settle the quote or rollover questions.
2. **Resolve dates before lagging.** Establish the provider interval, timezone,
   overnight coverage and availability cutoff. Then explicitly choose next ES
   session or next jointly observed session as the target. These are different
   forecasting questions, especially around the gaps above.
3. **Predefine sensitivity runs.** Once the calendar and split are fixed, compare
   unchanged estimates with a clearly labelled treatment of the four suspect
   quote records and the possible roll record. These are alternative assumptions,
   not a retrospectively improved dataset. Preserve dates if a value is masked;
   exclude affected lag windows rather than joining across a missing session.
4. **Separate predictor and target treatment.** A suspect oil predictor and a
   suspect ES evaluation target have different consequences. Report affected
   training rows and forecast targets; compare models on identical targets within
   each sensitivity run. Do not use future values to fill missing predictors or
   choose exclusions based on which treatment wins the forecast comparison.
5. **Start with ES-only AR and ES+CL VAR after those choices.** This tests the oil
   contribution. It cannot answer the original interest-rate hypothesis; rates
   still require data or an explicit revision of the research question.

The full sample has been inspected for data quality, including potential future
evaluation years. Record this honestly. Freeze handling rules before comparing
forecast performance; do not describe the evaluation sample as wholly untouched.

## 6. Questions needed to close the unresolved cases

Prepared for provider/documentation follow-up; **no message has been sent**.

- What exact timestamps and timezone define a daily futures observation? How are
  evening trading, daylight saving, partial sessions and exchange trade dates handled?
- How are zero, missing, crossed or otherwise invalid bid/ask quotes treated before
  calculating midpoints? Can the four near-half-price lows be checked or corrected?
- Which contract(s) and switch timestamp underlie CL on 16 April 2020? Are returns
  across contract transitions included in daily RK/RV5? Can roll markers be supplied?
- Why is CL observed but ES absent on 26 December 2011 and 2 January 2012? Which
  hours enter the CL estimates? Can the six Good Friday differences be confirmed?
- When are daily estimates available, and are historical estimates revised?

## Reproduce and maintain the audit

```sh
.venv/bin/python scripts/audit_volare_es_cl.py
.venv/bin/python -m unittest discover -s tests -v
```

The command reads the original export and `datasets/volare_review_decisions.csv`.
It checks source hashes, unique decision keys and matching screening flags before
joining annotations. New flags without a decision remain `unreviewed`. It writes
local evidence/calendar CSVs and `es_cl_audit_summary.json` with hashes and counts.
It does not edit the ledger, original data, prepared panels or notebooks.

The ledger records **Codex preliminary review**, not a human sign-off. Resolve
entries with new evidence and preserve the reason for any changed decision. A new
source snapshot requires reassessment; the audit refuses stale source hashes.
GC, NG and corn flags remain outside this ES/CL review.

Sources S1–S5 above were accessed on 29 September 2026. Their roles are limited
as stated; none supplies an independent reconstruction of the flagged variances.
