# Sunday Nov 8 CFB update

Fetched 9:28-9:29 PM CT. All 685 completed FBS-involving event IDs through Week 10 have summaries. The 51 newly completed summaries are here; the other 634 are in prior boxscore folders and Saturday's compressed recovery. Source manifest records request/receive timestamps and uncompressed-byte SHA256. Scoreboard IDs and scores independently match summary headers; all 138 published team records match those final scores.

Week 10 grades use the original Nov 1 sealed predictions and frozen dog-bucket classification, never the Nov 5 or Nov 7 research reruns. No claims about closing lines, ticket returns or injury/weather loss causes. AP 35/62 vs no-AP 34/62 fails the adoption gate; prior gate decisions untouched.

Resume ranking uses the existing 75% Colley win/loss + 25% opponent-adjusted points/yards method with the existing 1.5-point head-to-head near-tie rule. Loader now includes recovered compressed sources and rejects missing total yards instead of using zero. This is a coverage repair, not a ranking-method change. Archived reference/AP-fit columns remain Oct26-era comparisons, not newly fitted rankings.

Week 11 is a separate sealed research-only no-AP forecast: 67 games verified pregame; 3,815 training rows, 562 from 2026 after FBS-versus-FBS and complete-feature filters. All 685 raw summaries contribute current team features. Same StandardScaler and Ridge alpha10 specification as Saturday, with AP loading disabled because it is not an input. Coefficients and scaler saved in protocol. Numerical injury/QB/weather effects and model totals remain null. Neutral status is metadata, not a fitted predictor in this unchanged model. No calibrated probabilities or betting-value claim.

The earlier Nov5 exact-replay mismatch (max 0.043688 points) remains unresolved. Neither old forecasts nor source artifacts are overwritten.

`validate.py` checks seals, captured source hashes, complete scoreboard/summary scores, records, ranking IDs, forecasts and grades. `refresh.py` refuses to overwrite its forecast seal. `grade_week10.py` reproduces the prospective grading. `collect_sources.py` is an acquisition script; do not rerun into this archived snapshot. Data coverage and statistical validity are distinct: passing ingestion checks does not establish model skill.
