# Guarded candidate, still experimental - November 8, 2026

Three files preserved: newly supplied trainer and eight-test script unchanged; build_features.py copied from corrected_20261108 for its imported dependency. No real-game fit/evaluation rerun. All eight supplied synthetic tests passed independently.

High-risk review: manifest enforcement is NOT implemented as claimed. `enforce_manifest` ignores eval_start/eval_end; it checks only a filename substring against any declared season, not row content, partition, file hash or window. Manifest is optional, and run calls load before manifest validation. An allowed-looking filename or arbitrary evaluation dates can pass. Supplied test verifies only an undeclared filename rejection; it does not test these bypasses. Split guard remains open.

Improvements: malformed season_type no longer defaults to regular; protected2026/type3 rows are removed before numeric feature parsing (but CSV contents are still read); unlock flag parsed and always refused; scaler fitted only on fit-window vectors, read-only transform. This does not guarantee protected bytes were never accessed or mislabeled metadata cannot bypass filtering. Actual calendar-date validation is also incomplete (length check, not parsed date validation).

All prior independent-review gates remain unless explicitly fixed: season-specific D1 membership, outcome-availability lineage and exceptional scheduled dates, fail-closed adapter audit, frozen input/spec/split hashes, neutral-truth check and calibration/uncertainty. Standardizing features changes the fitted model, so older unscaled validation metrics are not this model's results. Do not inherit those claims. No final-test or production approval.
