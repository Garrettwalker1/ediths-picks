# Corrected experimental code - November 8, 2026

Preserved separately from experimental_20261108. Not production, validated forecasts or an approved final-test runner. Original corrected attachments retained unchanged.

Executed `python3 test_model.py`: all four included synthetic regressions pass (own/future-season prior, exact prior season, fixed evaluation sigma, flipped home/away order). Code review confirms chronological season closure, stable team IDs, caller-supplied sigma and header-ID side mapping replace the original defective paths. This does not independently prove all as-of boundaries.

Remaining gates:
- No bulk parquet adapter, season-specific D1 membership filter, or independently audited game-completion/as-of feature lineage yet.
- CLI has an evaluation start but no evaluation end or protected tournament exclusion. Do not run on full 2026 assets and accidentally evaluate the reserved 2026 tournament. Freeze explicit train/validation/final-test manifests first.
- Split and order use source date strings. Normalize timestamps and verify outcome availability before later-game features; sorted kickoff alone is not evidence a game was completed at feature cutoff.
- Input pairing silently overwrites duplicate event-side rows; malformed/nonfinal/partial input requires explicit exclusion and audit before use.
- Included tests are synthetic defect regressions, not season-level validation or probability calibration.
- Reported corrected partial-data smoke sample is 11 scorable games versus 124 previously. No performance comparison or model-quality claim follows from these different cohorts.

No fitting, real-game evaluation or final-test inspection was run during preservation.
