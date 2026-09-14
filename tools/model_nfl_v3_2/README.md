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
