# Group report reconciliation — 13 October 2026

Reviewed `Group Assignment Report EBC4097.pdf` against the final CSV, the newly
pulled unmodified `HAR_QTFE.ipynb`, `Tim_VAR`, and the saved final-data outputs.
The PDF is a draft, not yet consistent enough for submission. The source PDF and
teammates' code have not been edited. Page references below use the printed page
numbers (one less than the PDF viewer page number).

## Stationarity and lag selection

Testing each log-RV5 series with ADF/KPSS before fitting is appropriate. These
tests answer questions about the observed series; fitted VAR eigenvalues and
residual tests answer different questions about the estimated model. Both checks
are needed. ADF contains its own fitted auxiliary regression, but it does not
require a fitted VAR as input. Rejecting the ADF unit-root null while rejecting
KPSS level stationarity is conflicting evidence, not proof of a structural break.

The LVAR series tests use 3,106 variance-ready observations, 3 February 2011 to
12 July 2023. Its VAR lag table uses the common 3,084 training targets, 8 March
2011 to 12 July 2023. The common warm-up deliberately shortens the estimation
sample. Lagged regressors come from earlier dates; evaluation targets are excluded
from selection. Fitted conditional companion eigenvalues and ES residual
diagnostics are reported separately. HAC standard errors do not cure a unit root,
structural change or model misspecification.

| Implementation | Rule | Main setting | Extra detail |
|---|---|---|---|
| Plain VAR / LVAR | Initial five-market plain VAR; same targets for p=1..20 | BIC p=5 | AIC p=10; fixed 10-lag sensitivity; no seasonal or Treasury inputs |
| Calendar-controlled VAR | Initial six-variable system plus calendar indicators; same targets for p=1..20 | BIC p=4 | AIC p=9; fixed across its systems within each case |
| HAR/LHAR | Predetermined HAR aggregation windows | 1, 5 and 22 observations | Not selected as a VAR lag order; each window mean enters as one regressor |
| LVAR-section ADF | Auxiliary test-regression lag selection | AIC autolag | Separate from the multivariate VAR lag-selection table |
| VAR-section ADF/KPSS | Fixed test settings | ADF 20, KPSS bandwidth 28 | The LVAR section uses ADF autolag and automatic KPSS bandwidth |
| HAC covariance | Covariance truncation bandwidth | 22 | Not a forecast-model lag order |

The principles are consistent (training-only selection and fixed orders within a
comparison); the numerical settings are not identical. BIC can select different
orders for different systems, controls and estimation samples. A direct model
comparison does not require every model family to have the same lag structure,
but must explain these differences and use identical forecast targets. The
1/5/22 choices are standard HAR windows; they are not a claim that information
criteria selected 22 individual lags.

## Corrections needed in the current PDF

| Location | Finding | Required correction |
|---|---|---|
| Data, p.4 | Start date says 5 Jan 2011 | Final input starts 4 Jan 2011; ends 31 Aug 2026; 3,910 complete rows |
| Data, p.4 | Corn described as HAR-only and missing on an additional training date | Corn is complete in the final CSV and enters the all-commodity/full VARs and the selected VAR/LVAR systems |
| Data, p.4 | Close returns described as HAR-only | The LVAR also uses the supplied ES close returns |
| Data, p.4 | Treasury changes described as native-calendar changes with an extra observed-date delay in all models | Final CSV proxies are changes between retained yield observations. The calendar-controlled primary VAR uses ordinary lagged supplied values; the additional delay is a sensitivity, not the baseline. HAR uses the origin's supplied proxy. Remove the blanket example ending on 11 July unless describing the delay sensitivity specifically |
| Data, p.4 | All models said to score 783 targets | The VAR and LVAR common-date comparisons score 783. Pulled original HAR scores 778 and LHAR 774 under separate default 80/20 splits |
| LHAR formula, p.6 | Weekly/monthly controls average daily negative parts | Code takes the negative part after averaging signed returns, then its absolute magnitude. These operations differ when positive and negative daily returns mix |
| HAR table, p.6 | Baseline HAR R2=.7192, MSE=.3592; baseline LHAR R2=.7456, MSE=.3213 | These are older results. Current pulled saved outputs, independently reproduced on the final CSV: HAR R2=.7171, MSE=.3639; LHAR R2=.7446, MSE=.3254. Refresh the entire table from the teammate's current notebook |
| Calendar-controlled VAR, p.7 | Main table and p=4/p=9 rule | These match the supplied current results to displayed precision |
| LVAR, p.8 | Section 3.3 empty | Insert the new LVAR main section, defining the LVAR downside controls, matched plain benchmark and current results |
| Economic interpretation, pp.8 and 11 | AR MSE .356682 and all-commodity increase .66% | Current BIC outputs: .35668956 and .63862% (round .356690 and .64%) |
| Economic interpretation, pp.8-12 | Discussion omits the LVAR downside contribution | Add the within-specification 9.31% MSE reduction from downside controls; distinguish it from incremental commodity value and from the differently controlled baseline |
| Economic interpretation, pp.9 and 11-12 | A change below 1% in log-MSE is treated as a comparable change in VaR | Remove that numerical implication. Log-variance MSE does not map one-for-one into VaR or portfolio utility; no VaR backtest is supplied |
| Economic interpretation, pp.8 and 11 | Evaluation period described as containing no relevant crisis/recession | Support the classification with evidence or remove it. The model outputs alone cannot establish a macroeconomic regime classification |
| Throughout | Predictive associations described as confirmed mechanisms or significant forecast superiority | Use conditional association and descriptive forecast rankings; no identified structural effect or formal selection-adjusted superiority test is established |
| Contents, p.2 | Broken bookmarks | Update the Word contents field and repair heading references |
| Structure, pp.8-13 | Empty sections 4 and 7; duplicate economic interpretation; placeholder appendix links | Complete/consolidate sections, attach referenced appendices, remove highlights/comments and verify reference numbering |

The repeated economic interpretation should be consolidated before assessing the
6-8 page body limit in the syllabus. The PDF currently has 14 physical pages,
including cover, preface, contents, duplicate text and references. Bibliographic
names in the introduction should use proper author-year form rather than first
names (for example, Diebold and Yilmaz, 2012); merge all section-specific reference
lists into one consistent bibliography.

## Verified sample comparison

Both the VAR source copy and the repository final CSV have SHA-256
`ad3b481455b8e8ea4e632e065f7b38cfbb0293ecd8286611c81b5cda7ea5137f`.
The VAR and LVAR analyses have identical test dates and ES outcomes. The VAR begins with 3,127
raw training rows; its main p=4 fit uses 3,123 outcomes after four lag losses.
The LVAR uses 3,084 training targets after its shared HAR/LHAR warm-ups. Both score
13 July 2023 to 31 August 2026, 783 observations.

Original HAR full fits have 3,888 outcomes and LHAR has 3,867. Their first test
targets are 20 and 26 July 2023 respectively, with 778 and 774 scored targets.
The separate reference HAR/LHAR calculations use the common 3,867 fit outcomes
and 783 target dates; label those as common-date benchmarks, not the
unchanged printed results. Do not directly rank AIC/BIC on unequal target samples.

The VAR notebook has now been rerun after the original HAR notebook was
pulled/restored. Its current verifier checks the VAR execution and reads the
unchanged HAR functions for independent common-date forecast matches; it does not
require or claim a fresh local execution of the Colab notebook. All 43 retained
model scores are identical to their pre-removal values. Data, current model code,
HAR-reference and output hashes are checked. The R companion has not been
executed here.

## Report structure and figure choices

Keep **3.2 Vector autoregression (VAR)** for the calendar/Treasury specification
and **3.3 Leverage-augmented VAR (LVAR)** for the return-control extension.
Give a common VAR equation once, then explain the different information sets and
lag choices. Avoid VAR A/VAR B: the descriptive names state what each extension
adds. The plain VAR(5) remains the matched comparator for the downside gain;
comparing the LVAR(5) directly with the calendar-controlled VAR(4) changes
several model features at once. In tables, identify lags and calendar controls
explicitly and label each candidate's matched equity-only benchmark.

The additional daily-only VAR/LVAR variants have been removed from the active
analysis and report. Every remaining VAR/LVAR retains all five selected lags of
each included market. The existing daily-only LHAR comparison remains
unchanged. The general VAR source is Lütkepohl (2005), chapters 2-4:
https://doi.org/10.1007/978-3-540-27752-1.

Recommended main figure: the matched forecast-accuracy chart or the incremental
gain chart, depending on whether a results table is retained. Do not duplicate a
large table and a chart communicating exactly the same numbers in a short body.
Put the lag-selection curves, stationarity table
and residual diagnostics in the appendix. Generalized IRFs are optional appendix
figures; describe their contemporaneous component, conditional downside-control
path and exploratory bands without causal language.

The new LaTeX file contains ready-to-use captions, a figure guide and all source
references. Its chart assets are regenerated with
`.venv/bin/python scripts/build_var_figures.py` from checked final-data outputs.
