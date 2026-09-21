# NFL 2026 Week 2 source data

Free ESPN scoreboard and summary responses captured September 21, 2026 after each listed game reached final. These are factual Week 2 outcomes and box-score inputs for the next strict-as-of model refresh. The Monday Giants-Rams game is not final and is intentionally excluded; it must be added only after final.

Source endpoints:
- https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard
- https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=<event_id>

Book lines are not model inputs. `model_tracking.json` grades the frozen model against recorded pregame book margins separately.
