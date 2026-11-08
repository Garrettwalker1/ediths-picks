# Independent review - November 8, 2026

Experimental retrospective validation, not production or a proven predictive model. This directory preserves the candidate runner/adapter, updated split manifest and claimed evaluation manifest. No 2026 season file was adapted, loaded or evaluated in this independent reproduction. Original defective and earlier corrected code remain in their separate directories.

## Reproduction

From repository root, adapt only ending seasons 2023,2024,2025 with bulk_adapter.py. Run train_model.py on those three CSVs with --eval-start 2024-11-01 --eval-end 2025-05-01. The submitted recipe's August bounds select the same actual rows. Input asset hashes are in data/bulk/manifest.json at acquisition commit17cc0f0.

Exact reproduction: adapter rows12440/12480/12570, fit11966games, validation6285, sigma13.324. Model MAE10.601/RMSE13.997/Brier.1819; train-home-mean MAE13.307/Brier.2213; regular6162/postseason123. Full returned output in independent_reproduction.json. These are experimental validation metrics on this feed/cohort, not D1-only or final-test results. Feature choices and code are not yet frozen for a final run.

## Checks passed

- All three input seasons have zero schedule-ID duplication, team-game row duplication and score mismatches in matched source rows (coverage audit).
- Independently matched team IDs to schedule home/away: zero mismatches. Team-box vs schedule season_type matches for these seasons. Both sides of every adapted game have the same neutral flag and two unique team IDs.
- No null neutral flags in source schedules. This confirms the join, not independent truth of every venue's neutral classification.
- No NaNs in the seven resulting feature columns for these inputs; all built feature vectors finite.
- Same-date/future feature perturbation leaves all prior and same-date feature vectors unchanged. Each date's results update only after all that date's predictions are formed.
- Season closure occurs before the next season's first snapshot; only S-1 priors used, keyed by stable IDs. Own/future season prior defect repaired.
- Coefficients and sigma fit on fit-window rows only; validation does not fit sigma. No scaler exists; raw feature units determine ridge penalty strength.

## Blocking limitations / required next gates

1. No season-specific D1 membership filter. Source2023/24 lacks away_non_div1_team;2025 field exists but only four adapted games are True. This is not adequate membership truth. Do not label6285games a D1-only sample.
2. Date atomicity uses scheduled source game_date, not verified completion/result-available time. It prevents same-day order leakage, but does not independently prove earlier-date postponed/late/retrocorrected outcomes were available. Resolve source date semantics and exceptional games or use an explicit conservative availability rule with exclusions. Bulk snapshots fetched now are not contemporaneous historical snapshots.
3. Split manifest is not read/enforced by runner. CLI accepts arbitrary dates/files. It filters protected2026season_type3 rows AFTER load parses them; cannot claim never loaded. Missing/malformed season_type defaults2 and can bypass protection (synthetic reproduction confirmed). Advertised --unlock-final-test flag is not parsed; direct True refuses rather than unlocks. Keep2026files out and add fail-closed source/season/window gates before any holdout run.
4. No protected-set hashes, frozen feature/specification manifest or evidence of choices fixed before a final run. This validation window may guide research, never masquerade as final independent testing.
5. Adapter accepts exactly two rows, but does not enforce two unique IDs/opposing sides, completed+post source state, core finiteness or all score joins itself. Actual2023-25 checks passed; add fail-closed tests for future inputs. No omitted-game audit is emitted by adapter.
6. Neutral flags only source-joined, not independently checked. No opponent-strength adjustment, talent/roster inputs or validated calibrated probability model yet. Fit-residual sigma is not proof of out-of-sample calibration; Brier needs reliability/sample uncertainty analysis and stronger baselines.
7. Zero-margin accuracy treats every exact-zero prediction as away, so its printed32.9% accuracy is not a coin-flip50% baseline. Brier.25 and margin-error comparisons remain defined; avoid misdescribing that accuracy.

Conclusion: reported experiment reproduces and key earlier code defects are repaired. It beats the two implemented naive baselines on its retrospective2024-25 feed sample. That does not establish March readiness, market edge, D1-only validity or an untouched final-test result. Preserve experiments; hold forecasts and user-facing validation claims pending these gates.2025-26 is retrospective held-out at best, not prospective. Genuine prospective scoring requires forecasts frozen before future games.
