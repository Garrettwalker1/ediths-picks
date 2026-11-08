# CBB v1 validation manifest v2 (EXPERIMENTAL - not production, not a forecast)
As-of: 2026-11-08 ~08:20 CT. Split: SPLIT_MANIFEST.json (cbb_v1_split_v1).

## Exact reproduction recipe
1. Pull bulk assets (read-only) from repo commit 17cc0f0: tools/model_cbb_v1/data/bulk/{team_box,mbb_schedule}_{2023,2024,2025,2026}.parquet (sha256 in data/bulk/manifest.json; SportsDataverse ESPN-derived, MIT, license retained at data/bulk/UPSTREAM_LICENSE.txt).
2. python3 bulk_adapter.py data/bulk 2023 data/bulk_tg_2023.csv (same for 2024, 2025). Do NOT adapt/load 2026 for any tuning run; the final-test gate lives in train_model.run().
3. python3 train_model.py data/bulk_tg_2023.csv data/bulk_tg_2024.csv data/bulk_tg_2025.csv --eval-start 2024-08-01 --eval-end 2025-08-01

## Counts from the 11/8 08:18 run
- Adapter output: 12,440 / 12,480 / 12,570 team-game rows (seasons 2023/2024/2025); exactly 2 rows per game upstream.
- Stream: 0 duplicate event-sides dropped; 0 protected (2026 postseason) rows present or touched.
- Fit window: 11,966 scorable games (2022-24, walk-forward; early-2023 games unscorable without priors - correct behavior).
- Frozen train sigma: 13.324 (fit-window residuals only).
- Validation window: 6,285 games (2024-25 incl. 123 postseason).

## Results (validation window ONLY; not a final test)
- Model: MAE 10.601, RMSE 13.997, home-win acc 0.7173, Brier 0.1819.
- Baseline zero-margin: MAE 14.503, Brier 0.250. Baseline train-home-mean: MAE 13.307, Brier 0.2213.
- Segments: regular (6,162) MAE 10.606/Brier 0.1811; postseason (123) MAE 10.346, acc 0.626, Brier 0.2197.
- Coefficients: intercept 1.656, off_eff +0.542, def_eff -0.449, eFG -8.530, TO% -8.831, OR% -0.052, FTr +8.067, pace -0.268, home_ind +3.637.

## Claims discipline
- Beats naive baselines on the validation window ONLY. No market comparison exists (no historical odds). Coefficient plausibility is not validation.
- 2025-26 regular season is a RETROSPECTIVE held-out test at best, not prospective; nothing is frozen until audits (split, season-specific D1 membership, adapter, as-of lineage, neutral flags, priors, scaler) complete and model choices are fixed.
- Known open blockers: season-specific D1 membership (source flags only away non-D1; home non-D1 unflagged); no independent as-of audit; no opponent adjustment/talent/roster/matchup inputs; box-score possession approximation; no injury data.
