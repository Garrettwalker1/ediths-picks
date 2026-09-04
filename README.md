# ediths-picks
E.D.I.T.H.'s Picks football model dashboard

Forward game-line history is append-only. The frozen historical base is `tools/3-edith_movement_ledger_reconstructed.csv`; the prefixed path is intentional because GitHub's web editor truncates this multi-megabyte CSV during rename.

## Forward ledger layout

- Never replace or rename a ledger file through the web editor or uploader.
- Add each capture as a new, immutable part under `tools/ledger/`. Keep every new file below 1 MB; split a capture into multiple parts when needed.
- The GitHub uploader prefixes filenames. Consumers must read the filenames listed in the authoritative manifest, never infer a part's path from its local filename.
- Concatenate the frozen base and manifest-listed parts with `tools/ledger/7-read_ledger_manifest.py`. The reader de-duplicates by `quote_id`.
- The authoritative movement manifest is currently `tools/ledger/1-movement_manifest_v4.json`.
- The authoritative props manifest is currently `tools/ledger/6-props_manifest_v4.json`.
- Other manifest files and prefixed artifacts under `tools/ledger/` are deliberate superseded debris from establishing this layout. Do not treat them as authoritative, rename them, replace them, or select them as cleanup candidates.

## Model builders and capture tools

- `tools/1-build_player_pregame_priors.py` builds the frozen pregame player priors behind `player_projections.json` (model_version player-pregame-prior-v2.0.0-w1-2026 and later): 2023-25 nflverse stats + play-by-play, exact-match name joining, eligibility reasons for players without model lines, QB rushing-TD allocation from red-zone/goal-line carry shares. See `tools/5-PLAYER_PROJECTIONS_RUNBOOK-36986334.md`.
- `tools/2-fanduel_capture_parser_v2.py` is the current FanDuel VA props capture parser: reads lines from `runner.handicap` and player names from "Name Over/Under" runner labels. `tools/1-fanduel_capture_parser-8795ffdd.py` is retained unchanged for the original feed shape. Procedure: `tools/2-FANDUEL_CAPTURE_RUNBOOK-3dd64464.md`.
- `tools/cfb/` tracks 2026 CFB Week 1 FBS games and box scores (ESPN) to feed the college model.
