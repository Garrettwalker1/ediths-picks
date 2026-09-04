# E.D.I.T.H. model v3 - training run (2026-09-04)

Research-only training on the harvested 2020-2025 corpus. No picks, no market-edge claim.
Book/market lines never enter model inputs (the v1 TD prototype's implied-total feature is removed in v3).

## Data

- nflverse weekly player stats 2020-2025 REG (stats_player release), NFL, positions QB/RB/WR/TE: 34,919 player-games.
- nflverse play-by-play 2020-2025 REG for red-zone (<=20) and goal-line (<=5) opportunity shares.
- nflverse schedules for home/away. All features strictly shifted (pregame, point-in-time).
- Source URLs: https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_<season>.csv, .../download/pbp/play_by_play_<season>.parquet, .../download/schedules/games.csv
- CFB corpus (ESPN extracts in tools/espn/) is published and ready, but CFB props are not modeled in this run (no CFB props market is captured); college game-line modeling is a separate follow-up.

## Protocol

- Splits: train 2020-2023, validation 2024 (single pass for model/alpha selection), locked test 2025 REG (untouched until freeze).
- Yards models (passing/rushing/receiving): Ridge vs HistGradientBoosting per target; features = shifted player form (r6), team QB-play rolling, opponent defensive ratings (yards/TDs allowed rolling), home flag. Baseline = player r6 rolling mean.
- Anytime TD: stage 1 Poisson team TD expectation (lagged team TDs, lagged opponent TDs allowed, home); stage 2 within-team softmax allocation (usage, RZ/GL shares, TD rate, position). Baselines: naive opportunity-share allocation of the same team lambda; position base rates.
- Significance: paired game-cluster bootstrap, 500 reps, 95% CI on model-minus-baseline deltas (negative favors model).

## Locked-test (2025 REG) results - honest summary

Yards, full skill-position universe: passing -1.88 yds MAE vs baseline (CI [-3.30,-0.56]); receiving -0.17 (CI [-0.29,-0.04]); rushing HGB +0.14 WORSE (CI [0.06,0.23]).
Yards, props universe (locked test; pass att_r6>=10 n=582, rush carries_r6>=3 n=1423, rec targets_r6>=3 n=2279):
- passing: model 69.97 vs baseline 72.28 MAE, delta -2.31 (CI [-3.78,-0.91]) - settled
- rushing: model 22.08 vs 22.51, delta -0.42 (CI [-0.76,-0.07]) - settled, small
- receiving: model 23.36 vs 24.14, delta -0.77 (CI [-1.01,-0.55]) - settled
Anytime TD (locked test n=5,798, 1,076 TD events): model brier 0.1360 / logloss 0.4308 / AUC 0.731 vs naive 0.1373 / 0.4392 / 0.724; deltas brier -0.00135 (CI [-0.0025,-0.0003]) and logloss -0.0085 (CI [-0.0138,-0.0039]) - settled on both. Calibration slope 1.13.

## Verdict (house rules)

v3 beats its non-market baselines with settled 95% intervals on all three props-universe yards targets and on anytime TD. Improvements are small (1-3%). This is still measurement, not a betting model: it has not beaten timestamped FanDuel prices, and no claim of edge is made. Frozen 2026-09-04 before any Week 1 use. Raw single-game player stats remain very noisy (passing-yards R2 = 0.21); rushing on the all-position universe was worse than baseline and that null result stands as reported.
