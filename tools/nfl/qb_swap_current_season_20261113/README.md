# Experimental current-season QB-change input

Owner-directed inclusion November 13, 2026. No extra performance-adoption test. This is partial QB-passing input, not full injury coverage or proof of improved accuracy.

## Production interface

`injury_overlay.json` is consumed by the site's current NFL board. It preserves the unmodified current-season core and all original seals. One conditional prediction is shown alongside its baseline, marked exactly `(QB injury flag)`.

- Minnesota at Green Bay: if Kirk Cousins starts and Green Bay stays at its baseline-embedded QB production, raw home margin -1.2855315, displayed Minnesota -1.5. Baseline raw +0.2676371, displayed Green Bay -0.5. Minnesota team swing +1.5531686. This is a conditional unchanged-opponent-production assumption, not verified Green Bay health, a confirmed zero injury effect, or a complete game adjustment.
- Seattle at Las Vegas: flag disclosed but no adjusted spread. Darnold ruled out; Lock expected, not explicitly confirmed; Mendoza named starter. Samples of 78 and 8 dropbacks have data weights 22.1% and 2.8%, so league-mean priors dominate. No prior-only estimate represented as measured replacement quality.
- Other games: current QB role coverage unverified, not healthy or zero by default.
- Every `raw_home_adjustment_pts` stays null. The Minnesota conditional calculation is explicitly nested under `conditional_scenario`. Non-QB positions and CFB injuries are not included.

## Rebuild and correctness

1. Obtain fresh same-season data and verify source roles; do not blindly reuse this dated artifact.
2. `build_cs.py` creates current-season QB qualities and chronological core residuals. The core is reconstructed at each historical date from strictly earlier training rows, not all-row fitted residuals. Historical actual opening-starter labels support retrospective association, not proof those roles were known pregame.
3. `deploy_cs.py --cutoff 2026-11-13 --season 2026` computes current team-level inputs with stable IDs from `roles_input.json` and checks ID/name consistency. Cutoff is a strict earlier-date boundary. It consumes all passing EPA rows, including 0.47% of dropbacks from non-QB positions. Same-season EPA/dropback quality is shrunk to the same-season league mean; historical seasons determine variance parameters, not a prior-year player profile.
4. `apply_scenarios.py` checks exact current-core margins and creates the explicitly conditional interface. It must be generalized and source-checked before a new week or cutoff.
5. `verify_integration.py` checks hashes, unchanged current core, scenario arithmetic, half-point display, null unknown/full-game effects and prior-dominated abstention. These are correctness checks, not an accuracy test.

Coefficient-only bootstrap uncertainty is partial, crosses zero and excludes starter-quality, role, embedded-proxy and confounding uncertainty. It is not full predictive uncertainty. Association is not a causal injury estimate. The embedded EPA proxy is not identical to the core's conventional-rate input. Do not transfer this coefficient to another baseline.

`source_bundle_manifest.json` retains the supplied engine file hashes before publisher contract edits. `MANIFEST.json` records this integrated version. Raw public football sources are preserved for reproducibility. No logs are needed by the live interface.

## Primary role sources, checked November 13 at 14:10 CT

- https://www.vikings.com/news/nfl-expert-picks-packers-rivalry-renews-week-10 : owning team says starter not announced. Cousins scenario only.
- https://www.packers.com/news/packers-defense-ready-for-another-round-with-kirk-cousins-nov-13-2026 : Cousins expected, not official.
- https://www.seahawks.com/news/week-10-injury-report-seahawks-at-raiders : Darnold ruled out, Lock expected/preparing to start, Thursday report stage.
- https://www.raiders.com/news/fernando-mendoza-named-raiders-starting-quarterback : Mendoza explicitly named Week 10 starter.
- https://www.packers.com/video/packers-daily-a-high-noon-qb-showdown-nov-13-2026 : current Love matchup context, not a substitute for Minnesota confirmation.

Raw stats source pattern: https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv (same pattern for 2020-2025). Games: https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv . Current-core raw input hashes match the published November 13 core exactly. Player stats were retrieved for the supplied engine around November 13 14:02 CT; role checks were refreshed at 14:10 CT.

## Additional factual flags, checked November 13 at 15:26 CT

Miami-Indianapolis, Rams-Arizona and Chargers-Baltimore also carry `(QB injury flag)` without numerical effects. Owning-team sources confirm Willis IR/McCord first start, Minshew season-ending elbow injury/Beck first start with Brissett's departure separate, and Jackson/Huntley IR/Brissett acquired and slated to start Monday. Unknown new-starter quality and unimplemented new-to-team applications remain explicit. These facts do not replace the baseline or stack with another QB method. URLs are stored per game in the overlay. Baltimore has a separate Monday pregame check; Sunday's check is not Monday clearance.
