# NFL Week 4 grade (Oct 6)

`grade/build_grade.py` grades the frozen margin-Elo v1 Week 4 raw margins against the last pre-kickoff FanDuel IL spread published on the board (`grade/published_week4_book_lines_snapshot.json`, with capture times). Raw capture ledgers for Oct 2-5 were lost in the Oct 5 workspace reset, so that snapshot is the surviving record. Finals: ESPN scoreboard archived in `grade/`. Result: model 8, book 8, no ties; mean absolute error 7.38 vs 7.25. Measurement only.
