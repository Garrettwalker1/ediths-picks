# ediths-picks
E.D.I.T.H.'s Picks football model dashboard

Forward game-line history is append-only. The frozen historical base is `tools/3-edith_movement_ledger_reconstructed.csv`; the prefixed path is intentional because GitHub's web editor truncates this multi-megabyte CSV during rename.

## Forward ledger layout

- Never replace or rename a ledger file through the web editor or uploader.
- Add each capture as a new, immutable part under `tools/ledger/`. Keep every new file below 1 MB; split a capture into multiple parts when needed.
- The GitHub uploader prefixes filenames. Consumers must read the filenames listed in the authoritative manifest, never infer a part's path from its local filename.
- Concatenate the frozen base and manifest-listed parts with `tools/ledger/7-read_ledger_manifest.py`. The reader de-duplicates by `quote_id`.
- The authoritative movement manifest is currently `tools/ledger/1-movement_manifest_v4.json`.
- The authoritative props manifest is currently `tools/ledger/3-props_manifest_v2.json`.
- Other manifest files and prefixed artifacts under `tools/ledger/` are deliberate superseded debris from establishing this layout. Do not treat them as authoritative, rename them, replace them, or select them as cleanup candidates.
