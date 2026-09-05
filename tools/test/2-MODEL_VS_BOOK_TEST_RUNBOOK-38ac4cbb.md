# Prospective model-vs-book test

## Freeze before comparison

Keep each numeric model snapshot immutable and timestamped. A row is eligible only if the model freeze predates the audited FanDuel quote. Week 1 uses `player-pregame-prior-v1.1.0-w1-2026`; its numbers were frozen September 1, before the September 2 market capture. The Week 1 packaging adds opponents and labels but does not change predictions.

Join only exact sport, event, player, market type, side and line identities. Do not loosen player names. Keep exclusions with a reason. Use the final eligible pre-kick quote as the close and retain earlier quotes for movement and CLV.

## Settle

Append official results after games. Grade voids and pushes explicitly. Never delete misses, inactive players, stale-role misses or surprising outcomes; exclusions must follow rules registered before kickoff.

For yardage, receptions and passing TD lines, compare the model median's absolute error with the closing line's absolute error on the same player-market outcome. Cluster uncertainty by game.

For anytime TD, compare Brier score and log loss with a no-vig book probability only when the feed captured enough sides to remove vig. A lone Yes price stays labeled raw/vigged and cannot establish betting edge.

## Read the result

Week 1 is descriptive even if the result looks strong. Report the weak number and its interval. Do not tune on it.

A predictive signal requires at least 100 settled NFL games and 500 exact outcomes in that market family, improvement on both registered primary metrics, and paired game-bootstrap 95% upper bounds below zero. A betting-edge label additionally requires prospective positive CLV after vig and a positive lower 95% bound on net return from recommendations whose rules were frozen before the quote.

Until those gates clear, keep the dashboard's model-price differences suppressed and label outputs research only.

## Coverage rule (Garrett, 2026-09-04)

Every game in the week window gets a frozen model prediction - full-week coverage (Thu/Sun/Mon or whatever the window spans) is the standing default for NFL and CFB boards, not a subset. Any number generated after that game's kickoff is labeled post-kickoff and is excluded from pregame grading sets.
