# Props backtest project notes

- Closing-line history accumulates from **2026-09-04** (first timestamped FanDuel VA prop capture). Coverage: ~916-926 prop quotes per snapshot, 3x daily (7:10 AM / 1:10 PM / 7:10 PM CT) via the capture cron, stored in this directory (`*-props_*.csv`, indexed by the props manifests).
- 2026-09-09 decision (Garrett): **free path only** - keep the daily captures running, no Odds API purchase. Historical-depth backfill stays deferred.
- Unlock condition for the props backtest harness: weeks of closing-line depth, then grade v3 model-implied lines vs closing book prices ATS-style with locked-holdout + bootstrap discipline (same rules as the game-line models). Ship only if it clears.
- Models waiting on that test: v3 yardage (pass/rush/rec - settled vs naive baselines on locked 2025, never market-tested) and v3 anytime TD (AUC 0.731 locked test, never market-tested).
