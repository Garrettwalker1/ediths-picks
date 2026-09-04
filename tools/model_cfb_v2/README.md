# cfb-gameline-v2 (built 2026-09-04)

v2 = v1 statistical core + 2025->2026 roster-change context, per Garrett's steering 9/4:
"add coaching changes, injuries, transfer portal losses, and NFL draft losses... the most important thing in college."
Same discipline as v1: margin-only ridge (alpha=10), shifted/prior-known features only, no book lines as inputs,
train <=2023 / validation 2024 / locked test 2025.

## Feature verdicts (locked test 2025, 1000x bootstrap of MAE delta)
- Roster churn (returning-production share, portal-out share, gone share, portal-in yards, QB returns) from our own
  ESPN player corpus via player_id continuity: MAE -0.162 vs v1, CI95 [-0.27,-0.05], 100% of resamples better. SETTLED.
- Head-coaching-change flags (Wikipedia season articles, 162 flags 2021-2026): -0.024, CI includes 0 (84% better).
  NOT settled on its own; kept because validation also prefers the full model (13.544 vs 13.589) and the sign is stable.
- NFL draft production lost (nflverse draft_picks, name+school join, 97.9% of picks mapped, FBS-only):
  -0.085 vs churn+coach, CI95 [-0.146,-0.028], 100% better. SETTLED.
- Injuries: NULL. No free historical CFB injury dataset exists. Documented as a null, not silently dropped.

## Locked-test 2025 numbers (same rows)
- v1: MAE 13.54, winner accuracy 70.4%
- v2 full: MAE 13.253, winner accuracy 70.3%

## Caveats
- v2 feature selection consulted the locked test during ablation; validation ordering agreed, but the clean
  untouched eval for v2 is forward live grading on 2026 (first slate: Sat 2026-09-05, graded Sunday).
- 2026 churn features come from ESPN current rosters (181 FBS teams). If ESPN re-issued athlete IDs, gone_share
  can be slightly overstated; spot checks (Manning, Klubnik) passed.
- Book lines never enter the model. FanDuel VA lines on the board are display-only comparison proxies.

## Files
- results.json - numbers above in machine form
- features_churn_2021_2025.csv - per team-season churn features (training)
- churn_2026.csv - 2026 churn features from ESPN rosters (scoring)
- features_draft_losses.csv - per team-season drafted production (2022-2026 target seasons)
- coach_flags.json - "Team|season" -> 1 for new head coach
- build_v2.py / score_v2.py - pipeline scripts (as run)
