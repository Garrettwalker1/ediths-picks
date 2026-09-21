# AP poll source archive

Free ESPN AP Top 25 snapshots used for a point-in-time feature experiment. Historical files come from ESPN Core API paths scoped by season, regular-season type and week. The current file is ESPN's 2026 Week 4 site API response, published September 20, 2026.

Sources:
- https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/<season>/types/2/weeks/<week>/rankings/1
- https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings

Only a poll published before kickoff may join a historical game. Unranked teams receive zero rank-score/points. Book data is never used.
