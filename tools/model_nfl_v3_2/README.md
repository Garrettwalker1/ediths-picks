# NFL model v3.2 - margin + moneyline (built 2026-09-14)

Garrett's direction (9/14): "Build similar to the CFB model. Fuse injury, history, stats player,
career stats, offensive coaches, defensive coaches, talent rosters, etc." Version label v3.2 is his call.

CFB-v2-style Ridge margin model over nflverse, with feature fusion:
- history/form: prior-season means + shifted rolling-4 form for points, yards (total/pass/rush, for/against),
  giveaways/takeaways, sacks, QB completion % and passing TDs
- talent rosters / career stats: returning-production share + incoming production (free agency) per team-season
- injury: pregame weekly injury-report points (Out=1, Doubtful=0.75, Questionable=0.25) + QB-out flag
- coaches: head-coach change flag (OC/DC not yet - see results.json known_gaps)
- rest: rest-day differential
- QB facts: same-QB-as-last-game continuity

Protocol: train 2010-2022, validation 2023 (selection), LOCKED test 2024-2025 reported separately,
game-cluster bootstrap 500x. Book lines (nflverse spread_line/moneyline) are the benchmark ONLY.

Gate verdict (see results.json for full numbers): beats Elo (-0.397 MAE, CI95 [-0.767,-0.063]),
LOSES to the closing spread (+0.432 MAE, CI95 [0.131,0.707]) and to the closing moneyline
(brier 0.2170 vs 0.2075). descriptive_failed_close - measurement, not picks. Published for the
record on day one of the build; iteration continues under the 9/6 rule (val selection, locked test,
bootstrap discipline, honest reporting either way).

## Iteration 2 (2026-09-14, Garrett-approved feature set)

Added: snap-weighted injury impact (starter snap share x pregame report status; pre-2020 seasons scaled
by a 0.55 average-starter proxy since snap counts start 2020), weather/turf (dome, wind, cold,
wind x pass-form interaction), week-18 resting-starters handling (tested dropping week-18 games
from training). build_v32b.py + boot_v32b.py.

Val-2023 selection picked v3.2b full: val MAE 10.556 (best), locked-test 10.239 vs iter1's 10.263.
The injury upgrade is small but real; weather/turf and week-18 handling were neutral.
Gate: beats Elo (-0.389 MAE, CI95 [-0.763,-0.059]); LOSES to the closing spread
(+0.438 MAE, CI95 [0.168,0.720]) and closing moneyline (acc 0.643 vs 0.688, brier 0.2176 vs 0.2075,
logloss 0.6240 vs 0.6006). descriptive_failed_close stands - measurement, not picks.

OC/DC data status: no free structured source (nflverse has no coaches release - only head coaches in
games.csv). Coordinator identities 2006-2021 secured from jchernak96/NFL_Coordinator_Data (PFR-derived);
2022-2025 being filled from Wikipedia team-season staff sections (rate-limited crawl in progress).
PFR direct crawl blocked from datacenter IPs (403) and Cloudflare-challenges the cloud browser.
OC/DC change flags join iteration 3 once the table is complete.

## Iteration 3 (2026-09-14): OC/DC change flags - honest negative, not adopted

coordinators_2006_2025.csv: team-season head coach / offensive coordinator / defensive coordinator
identities 2006-2025 (PFR-derived 2006-2021; Wikipedia team-season staff sections 2022-2025 with 20
structural gaps patched from pro-football-reference team pages; GB 2025 DC web-verified). Null = the
team officially listed no coordinator that season. build_v32c.py + boot_v32c.py.

Val 2023 preferred v3.2c (10.534 vs 10.556) but the locked test did not confirm: 10.254 vs v3.2b's
10.239 (v3.2c-minus-v3.2b mean +0.014, CI95 [-0.009,0.036]). Val/test ordering disagrees, so under the
9/6 rule the flags are NOT adopted. v3.2c still loses to the closing spread with a settled interval
(+0.454 MAE, CI95 [0.159,0.729]). descriptive_failed_close stands; v3.2b remains the reference model.

## Iteration 4 (2026-09-14): EPA features + PFF+ lever - both recorded, neither adopted

EPA lever (build_v32d.py, agg_epa.py): team-game offensive/defensive EPA per play, success rate and
pass/rush EPA splits from nflverse play-by-play 2010-2025, same prior+rolling-4 gp-weighted
construction as the base features. 8 variants tested; all lose to v3.2b on validation
(10.610-10.687 vs 10.556) - EPA is collinear with the incumbent yards/points block. Recorded as an
honest negative. One recorded note: EPA-only+context hit the best locked-test MAE seen so far
(10.159, ATS 52.3%) but fails the val-first selection rule, so it is not adopted.

PFF lever: vault login to Garrett's PFF+ account works. On his subscription tier, premium.pff.com
server-side restricts every differentiating field (all grades, EPA, pressures, turnover-worthy plays,
big-time throws, dropbacks, snaps); the unlocked fields are box-score counting stats that nflverse
already covers with full history. No features to test - blocked by tier, not by auth.

v3.2b remains the reference model. descriptive_failed_close stands.

## Iteration 5 (2026-09-14): richer free play-by-play aggregation - honest negative

Garrett's standing direction is to keep testing free material without checking in per variant.
`build_v32e.py` tested situation-neutral EPA/success, early- and third-down splits, line decomposition
(rush efficiency, sacks, QB hits, stuffs), skill decomposition (pass efficiency, CPOE, air/YAC EPA),
and explosive-play/red-zone splits. All are pregame features: shifted rolling-4 blended with prior season.

Every richer-PBP variant lost to v3.2b on 2023 validation. The closest was line decomposition at
10.576 MAE vs 10.556; the full variant range was 10.576-10.914. No candidate passed val-first
selection, so none qualifies for bootstrap promotion. For the complete locked-test record, new variants
were 10.246-10.402 vs v3.2b's 10.239 and the closing line's 9.804. NOT ADOPTED; v3.2b remains the
reference and descriptive_failed_close stands.
