# CFB weekend input audit - October 16, 2026

## What is current

- Stats:455 of455 completed 2026 regular-season games returned by ESPN's FBS-involving schedule (groups80, Weeks1-7).910 team rows. Scores, total/passing/rushing yards, turnovers and parsed passing lines checked. This is not an audit of every FCS game or the entire2020-25 historical archive.
- Seven new Week7 final boxscores were added. Three older cached payloads were still nonfinal: JSU-North Dakota State, Sacramento State-Eastern Michigan and UMass-Rutgers. Those were retrieved as verified finals.
- Weather: all52 upcoming FBS-v-FBS modeled games, plus3 excluded FBS-v-FCS fixtures. Coordinates match the venue city and US state. These are city forecasts, not exact stadium microclimates. Window is the kickoff hour through four hours later. Indoor flags come from ESPN.
- Availability:64 of104 teams in the remaining modeled slate have official SEC, ACC, Big Ten, Big12 or Sun Belt reports (32 games). SEC/ACC/BigTen/Big12 are Thursday reports; Sun Belt reports remain initial, not final. The other40 have secondary Covers listings only. Secondary lists may omit players or retain old statuses. No listing is not clearance. Reports can change before kickoff.

## What did not change

The original59-game Week7 sealed research JSON and coefficients are unchanged. The original448-file boxscore store was left intact so the sealed experiment remains reproducible. Use the replacement/additional10 boxscores here when constructing current features, not the old nonfinal versions.

A separate current stats feature snapshot includes every final, using the original fitted coefficients without training on Week7 outcomes. Five remaining game research margins change because the three old missing finals are now included. Those outputs are marked STATS UNPROVEN and do not replace the frozen predictions or enter their evaluation.

WX UNPROVEN is a separate weather companion beside the unchanged sealed margin. It reuses the previously fitted October10 candidate coefficients. That candidate failed2024 validation (MAE13.0646 to13.0750) and its2025 comparison was inconclusive. Historical observed weather differs from pregame forecast evidence, indoor filtering was incomplete, and wind coefficient signs were unstable. This is not an adopted improvement or betting signal. No weather total and no numeric injury adjustment were invented.

## Artifacts

- `stats_audit.json`: game/stat coverage and repaired files.
- `source_manifest.json`: source identities, original and replacement hashes, immutable seal hash.
- `boxscores/`: ten fresh verified final payloads.
- `current_research.json`:52 current stats research predictions, with unrounded differences and feature changes.
- `current_team_features.csv` / `sealed_team_features.csv`: auditable before/after inputs.
- `official-injuries.json`: Thursday conference reports, grouped by team and player status.
- `secondary-injuries.json`: source-attributed secondary snapshot, not complete clearance.
- `forecasts/`:55 forecast snapshots.
- Root `cfb_current_status.json`: UI sidecar with coverage, weather calculation and availability facts per game.

No book prices enter any calculation. Displayed predictions round to half or whole points. Raw values remain labeled unrounded for audit. Week7 validation is still pending.

## Sources

ESPN college scoreboard and summary APIs, https://www.secsports.com/fbreports , https://theacc.com/sports/2025/8/28/availability-reporting-football.aspx , https://bigten.org/fb/availability-reports/ , https://www.covers.com/sport/football/ncaaf/injuries , https://open-meteo.com/en/docs . Exact per-game ESPN URLs are in the source manifest.
