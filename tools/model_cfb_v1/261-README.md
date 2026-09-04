# E.D.I.T.H. CFB game-line model v1 (2026-09-04)

SEPARATE from the NFL model (user steering 9/4). Research-only: no picks, no market-edge claim.
Book/market lines never enter inputs. Frozen 2026-09-04 before any 2026-season use.

## Data

- ESPN corpus in this repo: tools/espn/games (scores), tools/espn/team_defense (per team-game yards/points allowed), tools/espn/player_games (QB play), FBS only, 2020-2025 REG+bowls as indexed: 10,936 team-games, 5,409 assembled games (train 2,933 / validation 825 / locked test 813).
- 2020 is the COVID-shortened season (571 games); noted, not adjusted.
- Neutral-site games are not flagged in the ESPN index; home field is modeled as a constant. Known limitation.

## Protocol

- Features per team: prior-season ratings blended into current-season shifted rolling r4 (weight gp/(gp+2)): points for/against, total/pass/rush yards for/against, turnovers forced, QB comp%/yds/TD/INT. Game features are home-minus-away differentials plus experience differential. All inputs point-in-time.
- Splits: train 2020-2023, validation 2024 (model selection: ridge vs HGB), locked test 2025.
- Baselines: constant (home +2.5; train-mean total) and rolling points-differential.
- Significance: paired game-cluster bootstrap, 500 reps; negative delta favors model.

## Locked-test 2025 results (813 games) - honest summary

MARGIN (spread direction): model MAE 13.54 / RMSE 17.13.
- vs constant home+2.5 (16.54): delta -3.00, CI [-3.50,-2.54] - settled improvement
- vs rolling-diff baseline (14.40): delta -0.85, CI [-1.16,-0.53] - settled improvement
- Winner accuracy 70.4% vs 60.1% always-home baseline.

TOTAL: model MAE 13.31. WORSE than the train-mean constant (13.20): delta +0.10, CI [+0.05,+0.16] - settled null. Beats the rolling baseline (14.95), which is itself poor. Plain conclusion: v1 does not predict totals better than a league average; use the constant or rebuild totals with richer features.

## Verdict (house rules)

v1 margin model beats both non-market baselines with settled 95% intervals. v1 totals model does not beat a constant and is a null. Neither has been tested against timestamped book lines - measurement only, no picks. FBS-only scope.
