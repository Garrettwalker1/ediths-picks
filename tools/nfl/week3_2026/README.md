# NFL 2026 Week 3 prediction cycle

- `game_predictions_raw.json`: v3.2b raw Week 3 home-margin outputs. Coefficients are fit on completed 2010-2025 games. Week 1-2 2026 data only updates shifted pregame form/features. Target-week outcomes and book values are excluded from model inputs.
- Published spreads round to the nearest half-point; raw values here remain unchanged.
- `power_ratings/`: timestamped public rankings plus the validation-first Elo candidate experiment. The candidate was not adopted because its locked-test bootstrap interval crossed zero.
- Weather is blank until reliable forecasts enter range. The archived Week 2 nflverse injury file contains 251 rows across all 32 teams. `../week2_2026/injury-news-layer.json` adds dated ESPN developments that the static pregame report misses. Week 2 labels are not silently carried into Week 3; unresolved players remain explicitly unresolved until current practice/team reports land.

## Week 3 result grade (September 29)

The historical v3.2b frozen model is quarantined because of point-in-time feature leaks. `grade/week3_grade.json` measures its immutable raw margins against the last timestamped pre-kickoff FanDuel Illinois home-team spread from the existing immutable ledger. The compact Monday DOM capture is read by its own schema. Book home margin is the negative of the team spread; final scores are archived from the [ESPN Week 3 scoreboard](https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week=3) in `grade/espn_week3_scoreboard_20260929.json`. Rebuild with `python3 tools/nfl/week3_2026/grade/build_grade.py tools/nfl/week3_2026/grade/espn_week3_scoreboard_20260929.json` on a clean baseline only, then check the diff. This is measurement, not a validated edge. No new model outputs were generated.
