# NFL 2026 Week 3 prediction cycle

- `game_predictions_raw.json`: v3.2b raw Week 3 home-margin outputs. Coefficients are fit on completed 2010-2025 games. Week 1-2 2026 data only updates shifted pregame form/features. Target-week outcomes and book values are excluded from model inputs.
- Published spreads round to the nearest half-point; raw values here remain unchanged.
- `power_ratings/`: timestamped public rankings plus the validation-first Elo candidate experiment. The candidate was not adopted because its locked-test bootstrap interval crossed zero.
- Weather is blank until reliable forecasts enter range. Week 3 official injury reports were not yet present in the free nflverse feed at this run; known dated reports are tracked separately and no unverified status was filled.
