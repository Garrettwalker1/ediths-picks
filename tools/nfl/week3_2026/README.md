# NFL 2026 Week 3 prediction cycle

- `game_predictions_raw.json`: v3.2b raw Week 3 home-margin outputs. Coefficients are fit on completed 2010-2025 games. Week 1-2 2026 data only updates shifted pregame form/features. Target-week outcomes and book values are excluded from model inputs.
- Published spreads round to the nearest half-point; raw values here remain unchanged.
- `power_ratings/`: timestamped public rankings plus the validation-first Elo candidate experiment. The candidate was not adopted because its locked-test bootstrap interval crossed zero.
- Weather is blank until reliable forecasts enter range. The archived Week 2 nflverse injury file contains 251 rows across all 32 teams. `../week2_2026/injury-news-layer.json` adds dated ESPN developments that the static pregame report misses. Week 2 labels are not silently carried into Week 3; unresolved players remain explicitly unresolved until current practice/team reports land.
