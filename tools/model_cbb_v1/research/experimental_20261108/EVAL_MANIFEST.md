WARNING: Subsequent code review found leakage and side-mapping defects. Read REVIEW.md. Original assertions below are not verified.

# CBB v1 - reproducible evaluation manifest (EXPERIMENTAL, not production)
As-of: 2026-11-08 08:10 CT. Status: plumbing validation ONLY - not predictive validation.

## Data provenance (read-only pulls, no repo writes)
- Source repo: https://github.com/Garrettwalker1/ediths-picks (public), path tools/model_cbb_v1/data/
- Durable collection commit: bff1dde (2026-11-08 ~06:42 CT)
- backfill_progress.json as-of 2026-11-08T12:42:04Z: done_days 20241101-20241103; last_batch 20241104-20241110; range plan 2024-11-01 to 2026-04-15
- last_harvest.json: finals_total 713, summaries_fetched 100 (last batch), failures 0, summaries_missing 300
- Underlying upstream: ESPN public endpoints (scoreboard + summary), documented in tools/model_cbb_v1/README.md

## Actual coverage used (11/8 run)
- 413 durable summary files pulled via pull_repo.py (GitHub contents API + raw URLs)
- 409 parsed into team-game rows; 4 excluded as collector-flagged incomplete: 401921153, 401722003, 401720999, 401706980
- 818 team-game rows: 314 in season 2025 (Nov 4-10 2024 window ONLY - not a full season), 504 in season 2027 (Nov 3-7 2026, current to date)
- No non-D1 filtering applied yet (current 362-team list is NOT historical membership truth; season-specific membership check is a known open requirement before any fit claim)
- No odds/closing lines used anywhere; no injury data; no rankings/roster/talent inputs yet

## Code (attached, experimental)
- build_features.py: ESPN summary JSON -> per-team per-game rows. Possessions = FGA - OReb + TO + 0.475*FTA (box-score approximation); four factors; pace; off/def efficiency per 100 poss.
- train_model.py: ridge margin model on rolling point-in-time differentials (off_eff, def_eff, eFG, TO%, OR%, FTr, pace + home indicator); prior-season shrinkage at 8 game-equivalents; features snapshotted BEFORE updating with each game (no same-game leak); baselines: zero-margin and train-home-mean.
- pull_repo.py: read-only durable fetch (skips existing local files).

## Reproduce
1. pull_repo.py summaries <dir> 450
2. build_features.py <dir> team_games.csv
3. split rows by season (season = year+1 for Aug-Dec), then: train_model.py tg_2025.csv tg_2027.csv

## Known limitations (11/8)
- Historical window is one partial week of Nov 2024; 2022-23/2023-24 not collected; 2024-25 season nowhere near complete. No training/validation claim can be made.
- The 11/8 smoke output (model MAE 21.49 vs home-mean baseline 19.60 on 124 walk-forward games) is machinery verification at trivial coverage, NOT evidence about model quality.
- Point-in-time discipline verified structurally (snapshot-then-update) but not yet audited by a second party.
- Early-season games with no priors are skipped, so test n is coverage-dependent.
- Player-level, matchup-style, rankings, roster-experience, and talent inputs are not yet built; each must pass the validation window before shipping, and each needs an as-of snapshot provenance check.
