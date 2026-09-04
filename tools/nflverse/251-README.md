# nflverse historical training extracts (NFL)

Source: nflverse open data releases, pulled 2026-09-04 for E.D.I.T.H.'s Picks model training.
Free public data, no license restrictions beyond nflverse's own terms.

## Files and source URLs

- player_stats_2020.csv .. player_stats_2024.csv - weekly player stats
  https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_<season>.csv
- stats_player_week_2025_part1.csv + _part2.csv (split - over GitHub web-upload size limit) / stats_player_reg_2025.csv / stats_player_post_2025.csv - 2025 weekly / regular-season aggregate / postseason
  https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_<split>_2025.csv
- player_stats_season_2020..2024.csv - season aggregates (offense)
  https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_season_<season>.csv
- player_stats_def_season_2020..2024.csv - season aggregates (defense)
  https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_def_season_<season>.csv
- player_stats_def_season_2025.csv - DERIVED locally from stats_player_reg_2025.csv (nflverse had not published the def-season 2025 file at pull time). Column mapping: team<-recent_team, def_tackles = def_tackles_solo + def_tackles_with_assist, def_safety<-def_safeties, def_fumble_recovery_*<-fumble_recovery_* (all-purpose, not defense-only), def_penalty/def_penalty_yards<-penalties/penalty_yards (all-purpose).
- snap_counts_2020..2025.csv
  https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_<season>.csv
- injuries_2020..2025.csv - weekly injury reports
  https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_<season>.csv
- roster_weekly_2025_part1.csv + _part2.csv (split - over GitHub web-upload size limit) - weekly rosters 2025
  https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2025.csv
- games_all.csv - game index with ESPN + PFF join keys (assembled locally from nflverse schedules
  https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv)

## Known gaps

- player_stats_2025 weekly from the player_stats release returned Not Found at pull time; 2025 coverage comes from the stats_player release files above (week/reg/post) instead.
- schedules_all.csv download failed (Not Found); game data is covered by games_all.csv.
- No 2025 player_stats_season aggregate from nflverse at pull time; use stats_player_reg_2025.csv (same schema family, season-level REG) and stats_player_post_2025.csv.
