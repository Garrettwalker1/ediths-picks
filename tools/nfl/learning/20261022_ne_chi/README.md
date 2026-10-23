# Learning from NE-CHI, Oct22

Standing post-TNF pattern (same fixed rules as the Oct16 SEA-DEN record; that record's owner request established the pattern, this run applies it to the new TNF game).

The official 30-24 final and completed player stats are now archived as source-of-truth model inputs, not only ticket outcomes. `learn_game.py` applies the existing Elo and six-game half-life scoring rule and verifies the archived Week 7 player rows. This changes the future New England/Chicago team state without changing fit weights or Thursday's predictions. Run the script from the repo root to reproduce `learning_audit.json`. All numeric diagnostics/state values in that JSON are unrounded; they are not new published game predictions. Current Week7 sealed board and frozen cohorts remain untouched.

## Misses counted

- Frozen total 45.8 vs 54: 8.2 underprediction. The displayed scores 23-23 sum 46 because each score was rounded; use frozen model_total for total error.
- Frozen home margin +0.12 (PK) vs actual +6: 5.88 absolute error; the baseline called a coin-flip, home win probability 50%, Brier 0.25.
- Unproven injury overlay (cohort v5, CHI -1) had 4.9 error - closer this once; one game does not validate it. Weeks 5 and 6 diagnostics favored the baseline.
- Anytime TD: 25 active NE/CHI board players audited, one Bernoulli observation each, mean Brier 0.1578. Six scored (Swift, Stevenson, Burden, Loveland, Maye, Raridon). Henderson (39.0%) and DeMario Douglas (25.8%) did not; each appeared on two tickets - shared players across tickets are not independent observations, and ticket leg counts are never model-performance figures. Monangai (Out) and Doubs (IR) excluded: zero participation.

## Broader total check

All 46 settled frozen totals-ridge forecasts from Weeks 4-7 (Week 7: NE/CHI only so far) are included, no cherry-picking. MAE 10.815 vs 11.154 fixed training-mean baseline; mean signed prediction-minus-actual error -1.185. The model still underpredicts on average in this small sample; tonight's underprediction is consistent with that, and no global correction or fit change is justified by one game. No historical-market superiority claimed.

## Next update

Tuesday's regular rebuild must fresh-fetch completed schedule/player inputs, assert this exact game and the verified Week 7 player rows are present, use all eligible completed games under the unchanged rules, and retain an as-of cutoff before future targets. No rewrite of this audit or frozen cohorts. Candidate calibration changes require declared rules and untouched future evaluation, not fitting to this game.

No cause is asserted for tonight's misses. Injury/weather numerical adjustments remain experimental; no medical, play-calling or luck explanation invented.

Source URLs in learning_audit.json, exact source bytes and SHA256 in source_manifest.json. No new player-model fit or current-week generic forecast changes were made.
