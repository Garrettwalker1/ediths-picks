# Learning from SEA-DEN, Oct16

Owner request: "Just need to have the model learn from this game".

The official17-14 OT final and completed player stats are now archived as source-of-truth model inputs, not only ticket outcomes. `learn_game.py` applies the existing Elo and six-game half-life scoring rule, and established latest-player rolling features. This changes the future Seattle/Denver team state and JSN player state without changing fit weights or Thursday predictions. Run the script from the repo root to reproduce `learning_audit.json`. All numeric diagnostics/state values in that JSON are unrounded; they are not new published game predictions. Current Week6/Week7 sealed boards remain untouched.

## Misses counted

- Frozen total44.5 vs31:13.5 overprediction. The separate displayed scores23-22 sum45 because each score was rounded, so use frozen model_total for total error.
- Frozen home margin-0.71 vs actual+3:3.71 absolute error and wrong baseline winner. Experimental home margin+0.19 had2.81 error; one game does not validate it.
- JSN TD probability55.8% vs0: one Bernoulli observation, Brier0.311364.12catches,134yards,16targets. Three tickets sharing this player are not three independent probability misses; no joint SGP probability was established. No forced reduction to probability0.

## Broader total check

All32 settled frozen totals-ridge forecasts from Weeks4,5,and Thursday6 are included, no cherry-picking. MAE10.90625 vs11.53125 fixed training-mean baseline; mean signed prediction-minus-actual error-2.0375. The existing model has underpredicted on average in this small sample, despite Thursday overprediction. No global downward correction or fit change is justified by this game. No historical-market superiority claimed.

## Next update

Tuesday's regular rebuild must fresh-fetch completed schedule/player inputs, assert this exact game and JSN0TD row are present, use all eligible completed games under the unchanged rules, and retain an as-of cutoff before future targets. Do not rerun the hardcoded Week6 pregame publisher, which correctly refuses completed Week6 outcomes. New Week7 forecasts get their own artifact after all Week6 games finish. No rewrite of this audit or frozen cohorts. Candidate calibration changes require declared rules and untouched future evaluation, not fitting to this game.

No cause is asserted for Thursday's miss. Injury/weather numerical adjustments remain unfinished; no medical, play-calling or luck explanation invented. A high-usage receiving game can still end with0TD.

Source URLs in learning_audit.json, exact source bytes and SHA256 in source_manifest.json. The2025 JSN prior-history CSV is the player-ID-filtered extract of the public full2025 file, included so six-game rolling means bridge seasons exactly as the existing pipeline does. No new player-model fit or current-week generic forecast changes were made.
