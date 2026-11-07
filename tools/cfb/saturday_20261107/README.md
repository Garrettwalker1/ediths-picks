# November 7 CFB source recovery

Fresh ESPN source recovery, not restoration of original capture bytes. Public source inputs and collection audit only. Private ticket selections and research outputs are not published by this recovery.

A fresh working copy originally contained only 189 distinct 2026 summary IDs. Scoreboards for weeks 1-10 returned 634 completed event IDs as of November 7 morning. The recovery fetched 445 missing summaries with zero reported fetch failures. Twelve current-week summaries were already separately fetched during this run. New raw summaries are stored losslessly as gzip, with decompressed SHA256 hashes in raw_summary_manifest.json. Previously committed summaries remain at their original paths.

Scoreboard source pattern: https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week=10&groups=80&limit=400
Summary source pattern: https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=401856852

refresh.py reconstructs the unchanged-spec no-AP Ridge alpha10 research model from the recovered boxscore union. It loads gzip and existing plain JSON, constructs postgame as-of feature rows, excludes AP from fitted features and treats book only as comparison. Requires numpy, pandas, scikit-learn. Run from any checkout location. Generated predictions, coefficients, scaler and feature files remain local research outputs unless separately approved for publication. Historical seals are not overwritten.

Coverage check: 634 completed summaries, 1268 team-game records, 3765 fitted rows including 2022-26 history. Representative current teams have 8-9 completed games. Nov5 as-of replay produces the expected 3758 fitted rows but differs by up to 0.043688 points from saved rounded predictions. Exact reproduction is NOT claimed; data revision/dependency causes remain unresolved. The saved Nov5 companion and original seals remain unchanged. No validated player-level injury effect, current QB-specific adjustment or weather-margin improvement is established by this recovery. No calibrated win, spread or joint betting probabilities are supplied.
