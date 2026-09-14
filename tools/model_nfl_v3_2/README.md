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
