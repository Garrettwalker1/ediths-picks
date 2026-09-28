# NFL v3.2b reproducible fit, not a published game rerun

This is a forensic reproduction of the old model, NOT a repaired point-in-time model.
Its recorded diagnostics are contaminated by feature chronology defects: the
original historical season-prior fallback uses that season's full-year league
statistics; roster-return data knows everyone who played that season; QB
continuity compares against the QB with the most attempts in the target game;
and the first-game snap proxy can use that game's own snaps. Never describe
these reproduced metrics as a clean out-of-sample forecast. The point-in-time
feature rebuild, source-backed 2026 as-of rows, and a properly revalidated
model are still outstanding.

The frame is the historical 2010-25 games built by `../build_v32.py` and
`../build_v32b.py`. It includes all 156 original columns and the 26 selected
pregame features. Re-run `python3 train.py --check-only` to confirm historical
selection (2023 validation MAE 10.556 and 2024-25 locked test MAE 10.239).
`python3 train.py` saves the full-history refit, scaler, ordered features,
coefficients, frame SHA256, and in-sample retrospective margin-to-win mapping.
Historical inputs and script hashes are in `source_manifest.json`; raw public
nflverse downloads were scratch, not committed. The build scripts require
`/tmp/training/nflv32` with `spw_2010.csv` ... `spw_2025.csv`, `inj_2010.parquet`
... `inj_2025.parquet`, `games.csv`, and an alias `/tmp/ediths-picks` to this
repository for existing `tools/nflverse/22?-snap_counts_202?.csv` inputs.
Source releases can be revised, so hashes must be checked against this manifest.

`score_asof.py input.json --baseline 4.2838503159` requires a 26-feature
`features` object in the saved `feature_order`, a `provenance` object with
`source_url`, timezone-aware `observed_at`, and `method` for **each** feature,
plus `game_id`, timezone-aware `kickoff` and `as_of` timestamps. It rejects
missing, nonfinite, future, or unsourced inputs and fails if the frozen baseline
is not reproduced within 1e-7 raw points. This guards *input completeness*,
not truthfulness of claims at a URL: a reviewer must verify that each cited
source supports its derived numeric feature and that no target-week result
entered the row. Never substitute the book spread for a model feature.

Current Week 3 PHI-CHI input row was not saved in the frozen prediction archive.
Do not use this tool to publish a new number until the original as-of frame is
reconstructed, the archived +4.2838503159 Bears margin passes the baseline
guard, and current Week 3 injuries and planned QB are independently sourced.
The existing features count listed QB Out/Doubtful and the prior QB continuity,
but they do not encode whether Keenum or Bagent is the starter. Under the
current model, swapping those backups alone cannot produce a defensible
player-specific margin shift. This artifact is descriptive and still worse than
the closing-spread benchmark. It provides no validated moneyline edge.
