# E.D.I.T.H. CFB head-to-head model v1 - locked specification

## Objective
Predict calibrated pregame home-win probability for FBS-vs-FBS games. This is a fresh probability model, not a conversion of v3's spread residual and not a betting-pick model.

## Data boundary
Free sources only. Historical game outcomes, dates, teams, home/away/neutral and pregame venue fields come from reproducible SportsDataverse/ESPN or cfbfastR archives. Play-derived team features, when used, are computed only from plays strictly before the predicted game. No current sportsbook line, price, poll ranking, final-game field, retrospective injury/transfer knowledge or postgame statistic is a model feature.

FBS-vs-FBS only. Exclude games with missing team identity, date, result or location; exclude lower-division opponents because incomplete opponent histories distort strength. Keep all eligible bowls and regular-season games; neutral-site is explicit. Duplicate game IDs collapse deterministically to the last complete source record.

## Time split
Development/training choices use 2014-2023 only. 2024 and 2025 are untouched sequential holdouts and are reported separately before their combined result. Training for 2024 uses eligible 2014-2023 games. Training for 2025 expands through 2024, but no 2024 result may change features, hyperparameters, calibration method or reporting rules; it only supplies ordinary prior-game observations under this already-locked method. A favorable combined 2024-25 result does not survive as a positive claim if either held-out year materially reverses direction versus the closing benchmark.

## Features
1. Dynamic Elo difference, computed sequentially with home advantage applied separately. Initial team Elo 1500; preseason regression is 60% prior season / 40% 1500. K=20. Margin of victory never enters Elo.
2. Prior-game exponentially weighted team form, half-life four games: points scored, points allowed, success rate, EPA/play, explosive-play rate, finishing-drives points per trip, turnover margin and special-teams EPA. Offensive-minus-opponent-defense and defensive-minus-opponent-offense differences are formed. If validated play-by-play coverage cannot support a feature consistently across 2014-2025, drop that entire feature family before any holdout run, record the drop, and do not impute from present-day data.
3. Home indicator, neutral indicator, and rest-day difference capped to [-21,21]. Home-field coefficient is learned; neutral zeroes home indicator.
4. Week number as a capped linear term [1,16] only to let uncertainty contract slightly; no team/conference/poll labels.

All continuous features are standardized using training-fold means/SDs only. Missing prior form at season/team start is the contemporaneous national training mean plus an explicit missing indicator. No missing outcome/identity is imputed.

## Models
Baseline A: locked Elo logistic probability using 400-point base-10 curve and development-era home advantage of 55 Elo points, fixed before holdout.
Baseline B: home win base rate by season context.
Main: L2-regularized logistic regression. Candidate C values are [0.01,0.1,1,10], selected once on rolling-origin development folds ending 2018, 2019, 2020, 2021, 2022 and 2023 by mean log loss; ties choose stronger regularization. Class weights remain equal. No interactions unless explicitly enumerated above.

Calibration: compare uncalibrated, Platt and isotonic on out-of-fold development predictions only; choose once by mean development log loss, with Brier as tie-break. The chosen calibrator is refit only on training-era out-of-fold predictions for each holdout year. No holdout calibration.

## Market benchmark
Primary external benchmark is the closing two-way moneyline de-vigged by proportional normalization of raw implied probabilities. Both sides, exact game identity and a quote observed before kickoff are required. Last eligible quote is the close. If fewer than 70% of model-eligible holdout games have paired closing moneylines in either year, moneyline evidence is declared thin and cannot support a market-beating claim. Closing spread mapped through a training-era empirical win curve is secondary only. If spread becomes the best-covered market comparison, report that change to Garrett before any result is presented and label it a weaker proxy, never the moneyline benchmark.

## Metrics and inference
Report N, exclusions, winner accuracy, log loss, Brier, calibration intercept/slope and reliability buckets. Primary deltas are model minus Elo and model minus closing no-vig moneyline for log loss and Brier; negative favors model. Use 10,000 game-level bootstrap resamples for 95% intervals, seeded 20260902. Report 2024, 2025, then combined. ROI is secondary and only for a predeclared decision rule; v1 has no betting rule and therefore no retrospective ROI claim.

## Verdict
`pipeline_failed` on leakage, identity, coverage or reproducibility failure. `descriptive_failed_close` unless both log loss and Brier beat Elo and do not lose to closing no-vig moneyline in each of 2024 and 2025 separately. A combined improvement cannot override a losing year. `promising_unsettled` requires the above directional test but may still have intervals crossing zero. No profitable/edge/approved language without future prospective CLV and return evidence.

## 2026 generation
Only after the frozen holdout report: train through 2025 and generate the entire available 2026 slate in one timestamped run using pregame facts. Cal-UCLA is marked post-bet generated and excluded from prospective grading. No 2026 price is read or used before the spec hash and holdout report are frozen.
