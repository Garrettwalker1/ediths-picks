# NFL current-season core, November 13, 2026

Owner-requested new version: explicit schedule strength, record strength, and current-season player production. This version has no preseason talent, prior-season-stat profile, Elo carryover, or book inputs. Historical years train the coefficients; every row's features use only that row's earlier same-season games.

## Sources and method

- Current schedule: https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv
- Current player-game data: https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv
- Current slate/status: https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week=10
- Historical player CSVs: existing `tools/nflverse` extracts, sources documented in its README. Historical inputs are retrospective files, not authenticated pregame captures.
- Record strength: Colley W/L rating, ties half, using this season only. This is not ESPN's proprietary SOR.
- Schedule strength: mean Colley rating of opponents already faced, recomputed at each cutoff.
- Additional opponent-adjusted score rating from past scores, ridge penalty 20. No market input.
- Player features: aggregate passing/rushing/receiving rates from actual player-game rows joined by season/week/team and stable player ID. Yardage is gross passing plus rushing, not net team offense.
- Minimum three earlier REG games per team, with complete player-stat coverage and positive rate denominators.
- Mirrored StandardScaler plus Ridge alpha 10, no intercept; 1,416 eligible rows from 2020 through November 12, 2026. Coefficients fit all rows, so stored fitted historical margins must never be called archived or out-of-sample forecasts.

`build.py` rebuilds forecasts and provenance. `verify.py` checks unique rows, strictly earlier dates and same-season histories, coefficient reconstruction, side-swap symmetry, half-point display, future-state coverage, and Thursday's final against ESPN. These are source/calculation checks, not accuracy validation. No improvement claim.

## Missing inputs

Numerical injury/replacement effects remain null. These forecasts use realized season participants, not confirmed available-player projections. No assumption that unmatched players are healthy, no arbitrary injury penalty, and no transfer of injury weights fitted versus a different baseline. No new model totals or calibrated win probabilities. Existing seals and track records stay unchanged.

13 upcoming Week 10 games only; Washington at New York on Thursday is complete and excluded. Current features include its final and player stats. FanDuel comparisons remain separate in the site's hourly overlay with actual state/time labels.
