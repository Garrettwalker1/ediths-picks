# NFL Week 5 board (Oct 6)

- `build_week5.py games_nflverse_20261006.csv out.json` scores Week 5 with the predeclared margin-Elo v1 and totals ridge from `tools/model_nfl_v3_2/point_in_time`. It aborts unless the refit matches the locked Week 4 coefficients. Only completed scores through Week 4 are inputs; FanDuel lines are never inputs.
- `game_predictions_raw.json`: raw output, kept as produced.
- `fanduel_il_nfl_capture_20261006T1155Z.json`: Illinois capture (6:55 AM CT) shown as the comparison book line.
- `publish_week5.py` patches the board and score projections. No injury, QB or weather input. Weather forecasts are not pulled yet.
