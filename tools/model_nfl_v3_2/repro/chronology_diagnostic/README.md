# Partial chronology repair, diagnostic only

The old script leaks target-game QB identity, season-end roster participation,
current-season full-year league averages in fallback priors, and first-game
snap counts. This diagnostic changes fallback league priors to previous-season
ones, uses a fixed 0.55 snap proxy when no prior snaps exist, and removes QB
continuity and roster turnover from the selected features. Original columns
remain in the frame for audit, but they are not inputs to `evaluate.py`.

Build scripts are copies of the archived v3.2 builders with those two edits and
separate `_clean` scratch outputs. Their original stdout includes outdated
full-feature comparisons using retained leaking columns; ignore those lines.
To regenerate, obtain the public source bytes matching the parent
`source_manifest.json`, place them at `/tmp/training/nflv32`, ensure
`/tmp/ediths-picks` points to the repository, run `build_v32_lagged.py` then
`build_v32b_lagged.py`, and compare output parquet SHA256 to the saved
`frame_lagged_2010_2025.parquet`. Run `evaluate.py` for the 23-feature result.

**Not a clean point-in-time model.** The weather fields are final game
observations rather than archived pregame forecasts, a fixed snap proxy has
not passed sensitivity tests, and season-start roster context is missing.
The candidate loses on validation, remains behind the closing spread on the
locked test, and has no verified Week 3 as-of scoring row. `diagnostic.json` is
research context, not a deployable model. Do not publish a rerun from it.
