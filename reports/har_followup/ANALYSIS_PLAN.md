# HAR follow-up plan — 4 October 2026

Recorded before computing the follow-up comparisons. Earlier HAR results and the
evaluation period have already been inspected; this is an exploratory audit, not
a newly untouched holdout or formal preregistration.

Keep the 2011 ES/CL/GC common grid, 809 targets and shared 22-row warm-up. Compare
AR(5), AR(15), HAR, LHAR and LHAR with oil/gold. Give each AR the identical three
negative-return terms used by LHAR; do not search for new lag orders or signals.

Run these fixed scenarios, retaining the source export:

1. RV5 with existing ES close-to-close percentage log returns.
2. RV5 with ES open-to-close log returns on every date: changes the information
   window, and is not a proven roll correction.
3. RV5 with open-to-close returns only in candidate ES roll neighbourhoods
   (approximate scheduled day and one observed ES date on either side).
4. RK with the original close-to-close returns, on the same dates. This changes
   both training variance measures and the evaluated target proxy.
5. RV5 with original returns but omit training design rows exposed to the known
   unresolved GC 2018-03-26, CL 2020-04-16 and ES 2021-03-29 records. Use a
   conservative common 22-row feature window plus the next ES return where
   relevant. Do not join across omitted design rows or alter the forecast grid.
   These dates predate the test period. This is retrospective sensitivity, not
   an assertion that these records were errors or were identifiable in real time.

For baseline paired squared losses, calculate descriptive circular block-bootstrap
95% percentile intervals (2,000 resamples, seed 20261004; lengths 5, 20, 60).
Resample paired forecast losses together, without selecting favourable dates.
Pairs: AR15+returns vs AR15; HAR vs AR15; LHAR vs HAR; LHAR vs AR15+returns;
LHAR+commodities vs LHAR. Positive gain favours the first named model.
These intervals are conditional on this forecast experiment. They do not refit
models, correct earlier selection or provide a formal nested-model test.

Save yearly metrics and individual contributions. Inspect, without changing the
main scores, how much the five largest absolute paired contributions matter.
Keep model choice provisional until return/session construction is resolved.
