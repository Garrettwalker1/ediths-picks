# Player projections weekly sync runbook

## Purpose
Rebuild root `player_projections.json` for the dashboard's Player projections tab. The output contains NFL median/interval projections, anytime-TD probability, BOOM/BUST probabilities, roster highlights from root `fantasy.json`, and descriptive weekly player-vs-defense context. It does not scrape or claim FanDuel prop coverage. The FanDuel fields stay inactive until a reliable feed is connected.

## Committed files
- `tools/generate_player_projections.py`
- `tools/validate_player_projections.py`
- root `fantasy.json` (input, produced by the separate fantasy sync)
- root `player_projections.json` (atomic output)

## Public inputs
The generator downloads and caches these exact nflverse assets under `tools/player_projection_cache/`:
- 2023-25 weekly player stats: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_YEAR.csv`
- 2023-25 play-by-play: `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_YEAR.parquet` (reserved for the weekly feature extension; downloaded so the cache has the audited source set)
- NFL schedule: `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv`

No credentials, cookies, API keys or private responses are used. Runtime dependencies: Python 3.10+, pandas, numpy, scikit-learn, pyarrow, requests.

## Dry run
From repo root:
```bash
python3 -m pip install pandas numpy scikit-learn pyarrow requests
python3 tools/generate_player_projections.py --repo-root .
python3 tools/validate_player_projections.py player_projections.json
```
For deterministic testing of slate selection:
```bash
python3 tools/generate_player_projections.py --repo-root . --now 2026-09-01T19:00:00-05:00
```
Inspect the diff. Only commit when the generator and validator exit 0 and the JSON contains the intended upcoming week.

## Fail-closed rules
The generator writes to a temporary file and uses an atomic rename only after every gate passes. On any failure it exits 2 and leaves the previous root JSON untouched. It refuses to overwrite when:
- a public download fails;
- any 2023-25 stats season has fewer than 4,500 regular-season rows;
- root `fantasy.json` is absent or does not contain exactly seven leagues;
- fewer than 150 unique player rows or fewer than 20 roster matches are produced;
- the current-year schedule has no future regular-season slate or an implausible slate size;
- fewer than 100 weekly matchup rows are produced;
- any probability falls outside 0-1;
- the locked bust model fails to beat the past-yardage baseline on both Brier score and AUC;
- JSON serialization or final validation fails.

A failure must never be “fixed” by weakening a threshold mid-run. Investigate the source/schema change, update the code deliberately, rerun the locked evaluation, then review the change.

## Schedule
Tuesday at 7:00 PM America/Chicago. Preferred trigger: the upcoming NFL slate differs from `player_projections.json.matchup_context.week` or the file is missing. If the trigger system cannot compare the slate, run weekly and rely on fail-closed behavior.

## Commit procedure
1. Pull latest `main` and confirm a clean worktree.
2. Run generator and validator.
3. Review `git diff -- player_projections.json`; confirm `sportsbook.active` remains false unless a separately audited prop feed has been approved.
4. Commit only `player_projections.json` when changed. Do not commit cache files.
5. Wait for Pages propagation and verify all four tabs at 390x844. Player tab must have no page-level horizontal overflow; Fantasy must still show seven league cards and current injury flags.

## Current evidence limits
- Matchup context is descriptive. It did not improve held-out 2025 receiving MAE (16.2579 base vs 16.2536 with matchup features, n=5,035).
- CFB receiving is withheld because 2024 target/player data completeness did not match 2025.
- No reliable automated FanDuel player-prop source is connected, so line, price, over probability and CLV fields must remain inactive.
