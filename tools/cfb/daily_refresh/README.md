# Daily CFB update

Daily refresh starts at 07:05-07:20 America/Chicago, separately from book comparison captures. The Sunday review remains for grading and weekly review. Reconcile its inputs with the latest daily release before fetching or fitting again.

## Scope

- Incorporate newly completed 2026 games, current season player production, record strength and schedule strength.
- Keep the current season-only forecast specification. Historical seasons are training examples with their own past-only same-season features, not prior-year profiles substituted for current team production.
- No book inputs, recruiting talent profiles or AP inputs in the primary forecast.
- Rebuild the fixed 75% Colley W/L and 25% scoring/yardage resume ranking with its existing head-to-head rule. Rating points are not calibrated margins.
- Refresh dated roster snapshots and availability designations. Preserve primary versus secondary evidence and missing coverage. No guessed injury/replacement point effects.
- Future team-side picks can back only a verified current Power4 member. Opponents can be non-Power4. This is a pick filter, not a training, ranking or forecast-population filter. No automated bets.

## Preparation

`python tools/cfb/daily_refresh/prepare.py` stages a new dated issue and stops if that issue already exists. It acquires the current season scoreboard union, fetches missing final summaries, prepares a new current-season fit, current rosters and ranking. It does not publish or repoint the live release. Review failures before continuing, never relabel old quotes or change an earlier issue.

`python tools/cfb/daily_refresh/collect_availability.py /absolute/path/to/new/forecast/directory` collects current availability pages and public primary SEC/ACC conference report data. Source dates and matchup bindings must match the new slate. Big Ten/Big12 and other secondary evidence is explicitly secondary until checked against a primary report. An unavailable report or unlisted player is not health clearance. Exclude unofficial old notes. Report times are local to the source, not UTC dates.

These preparation scripts require review, not blind execution. On a new week, confirm the discovered provider week and full remaining-week slate. On a new year or changed input schema, stop for review. The November 20 contract tests contain that release's expected counts; update the new issue's checks from verified source coverage, not to make a failing assertion disappear.

## Before publishing

1. Reconcile every current final ID with the new or preserved summary store. Verify event/header IDs and completed states. Fail visibly on coverage loss.
2. Verify original forecast and source bytes from the previous issue. All earlier sealed and unsealed issues remain unchanged. New forecasts must be issued before kickoff; never recompute a started game's historical prediction.
3. Verify past-only chronology, coefficient reconstruction, side-swap symmetry, half-point display, and feature exclusions. These are correctness tests, not proof of accuracy improvement.
4. Verify roster season, nonempty counts, raw and compressed source hashes. Keep participant/roster mismatches explicit, never call them injured players.
5. Normalize the primary report response to data fields only, omit large image/font/color presentation fields, and record the original-response and normalized/stored hashes. Label the result a normalized projection, not a raw-byte archive. Compress source files losslessly and keep original/stored hashes and paths. Do not publish duplicate uncompressed discovery copies or credentials.
6. Add truthful metadata: issue time, exact source cutoff, final count, new summaries, current roster receipt range, forecast count, and injury source coverage. Seal the new forecast bytes. Archive the previous issue link. Update `cfb_current_release.json` only after all checks pass.
7. Update the power ranking data and visible date/count text together. Show AP comparison only when the verified AP poll actually exists; it still does not become a model input. Preserve old grades and dated reviews.
8. Inspect actual local pixels for current scope, current prediction, primary and secondary injury cards, rankings and stale text. Check mobile and desktop widths and JavaScript errors. Run the comparison regression suite.
9. Publish only the intended files. Verify remote commit, live bytes of every changed current resource and old forecast preservation, then repeat live visual checks. Remove any temporary credential copy.
10. Report cutoff, coverage, changes, explicit injury limits and live URL. Do not call a refresh a validated improvement. Keep routine odds updates separate.

## November 20 initial daily issue

758 completed FBS-involving final IDs, six new midweek summaries, 2,008 past-only eligible training rows, 60 remaining weekly FBS-vs-FBS forecasts including 54 Saturday games. 128 remaining-game team rosters checked, 126 season-participant/roster mismatches. Availability: 28 teams primary, 92 secondary pages, eight without a matched current report; 91 teams have 963 designations, 37 have no current designations and remain unknown. All prior 2,091 tracked CFB/reference files were checked unchanged. No numerical CFB injury or replacement correction.
