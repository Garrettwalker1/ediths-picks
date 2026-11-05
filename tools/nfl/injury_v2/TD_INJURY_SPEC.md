# Injury-to-workload redistribution spec for the anytime-TD primary (draft v1, 2026-11-05)

Owner direction: phonemsg-01M6P6QBGG3ESRJP91T5DMXTC2 - bake injuries into the
numerical model via expected snaps/touches/targets, adjusted beside baseline,
improvement must be validated, no invented point values. This spec defines the
work; nothing here is validated or live.

## 1. Scope and non-goals
- Target: the frozen Oct 29 anytime-TD candidate's share features (target/carry,
  red-zone, goal-line shares, recent-4 rates) for upcoming weeks.
- Not in scope: game-line injury adjustments (injury-experiment-20261007-v1
  covers that separately, still failing its gate), totals, book prices. No paid
  data. Historical seals and the published Week 8 Thursday 9-player prospective
  test are never revised.

## 2. Inputs (all free, point-in-time, source-timestamped)
- nflverse weekly injury reports: practice participation (DNP/limited/full)
  per day, game designation (out/doubtful/questionable), as of a captured
  pull time stored per week.
- nflverse weekly player stats (already used): targets, carries, snaps
  (snap counts where available), by week.
- Roster/depth source: ESPN roster + current depth ordering already captured
  in tools/nfl/week9_2026/current_rosters.json pipeline.

## 3. Mapping (fixed rule, fit before any forward use)
- Player availability expectation: designation -> expected-play probability
  estimated from historical nflverse designation->did-not-play outcomes by
  position bucket and report-day distance to kickoff. No flat constants
  without the historical fit; the fit table ships in the artifact.
- Vacated volume: an OUT or discounted player's season-to-date target/carry
  and red-zone shares are removed in proportion to expected-play probability.
- Redistribution: vacated shares flow to same-team same-position teammates.
  The recovery fraction and any ceiling are FIT from historical comparable
  absences (games where a player with a similar season-to-date share missed
  time), never assumed. An assumed recovery rate (e.g. "backups cover
  50-70%") is not a supported estimate and must not be presented as a
  bounded range. Yards-to-points proportionality is likewise not assumed;
  the mapping from lost share to expected points uses the historical fit.
  QB changes use a separate team-level passing/rushing efficiency penalty
  fit, never the player-share path.
- Adjusted features feed the SAME frozen candidate coefficients. No refit of
  the TD model itself in v1.

## 4. Validation protocol (pre-registered before first forward week)
- Backtest construction: replay historical weeks with ONLY information
  available at that week's report pull time (no outcome leakage). Report
  Brier/logloss vs the frozen candidate on identical player cohorts, paired
  intervals, and coverage (how often a report existed).
- Promotion gate mirrors the game-line rule: accumulated untouched forward
  weeks, improvement interval excluding zero, before any "validated" wording.
- Failure handling: weeks with missing reports fall back to the unadjusted
  candidate and are flagged, never silently interpolated.

## 5. Publication treatment
- When a forward week runs: site shows PRIMARY (stats-only), ADJUSTED
  (experimental), and baseline side by side, each labeled; the adjusted
  column stays "experimental, unvalidated" until the gate passes.

## 6. First deliverables (Friday Nov 6 checkpoint)
- designation->availability fit table from historical nflverse reports.
- historical comparable-absence fit: replacement production share by role
  (WR1-level target share, lead RB, etc.) from historical games missed.
- redistribution rule implemented against Week 8 as a retrospective
  reconstruction (clearly labeled retrospective; outcomes already known).
- comparison of adjusted vs frozen candidate on that retrospective cohort.
- CFB worked example: Toney absence at Miami using the same fitted rates
  with observed replacement-role evidence (who actually absorbs targets),
  plus reconciliation of Miami's scoring rate (model feature pf_f 41.0 ppg
  full-season vs any higher recent-4 claims) before any points translation.
- Every current-facts claim carries its exact observed source URL.
