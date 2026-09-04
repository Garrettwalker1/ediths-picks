# ESPN 2020-2025 harvest (NFL + CFB)

Purpose: gather ESPN game and player stats for the 2020-2025 NFL and FBS college football seasons so veteran player history can feed matchup-edge analysis for player props and anytime-TD props. Facts only; book lines never enter model inputs.

## Layout
- `games/nfl_<year>_games.csv` / `games/cfb_<year>_games.csv`: one row per game (event_id, date, teams, score, status), built by merging per-date ESPN scoreboard pulls with `tools/espn/merge_season.py`.
- `player_games/` (planned): per-player-game stat rows extracted from ESPN game summary box scores. Raw summary JSON is too large for the repo and is kept in scratch cache only.
- NFL seasons run Sep-Feb; CFB FBS (ESPN groups=80) runs Aug-Jan. Per-date pulls use `site.api.espn.com/apis/site/v2/sports/football/<league>/scoreboard?dates=YYYYMMDD&limit=100` (CFB adds `&groups=80`). The `year=` parameter is silently ignored by the site API - always pull by `dates=`.
- Box scores: `summary?event=<event_id>` on the same host.

## Harvest status
- NFL 2025: complete (286 games, all final).
- NFL 2020-2024, CFB 2020-2025, and box-score extraction: in progress on continuation wakes.
