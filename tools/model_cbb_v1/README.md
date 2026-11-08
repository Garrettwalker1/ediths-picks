# College basketball research collection

Development only. No fitted basketball model, current forecasts, validated performance or bracket predictions are supplied here. Football results do not validate basketball.

## Public sources

- ESPN men's college basketball scoreboard: https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard
- ESPN event summaries: https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary

The collector uses `dates=YYYYMMDD&limit=400&groups=50` on scoreboards and `event=EVENT_ID` on summaries. This is the feed's coverage, not an assertion of full D1-v-D1 coverage. D1 teams playing non-D1 opponents can appear. Team IDs and opponent identities must be filtered before model fitting. Missing or empty boxscores remain incomplete coverage.

## Stored records

`collect_espn.py` uses Python's standard library. It stores compact gzip JSON under `data/`. Every newly fetched record carries its source URL, request/receive timestamps and a hash of the source response. Summaries retain the header, boxscore and game information, not news, ads or articles. The hash identifies the response; the full response is not retained. Relevant selected fields are retained.

- `scoreboards/YYYYMMDD.json.gz`: most recent fetch of that day. Recent days are refreshed, never permanently frozen before the games finish.
- `finals.json.gz`: event-ID keyed postgame records. Repeat harvests update entries rather than duplicating them.
- `summaries/EVENT_ID.json.gz`: postgame team and player boxscores. Missing team statistics or athlete rows for either team are retried and counted as incomplete.
- `odds/YYYYMMDD_TIMESTAMP.json.gz`: unique, append-only run files. Every returned event is accounted for, including no line, fetch failure, or not-pregame. Summary status and the actual per-response receipt time must both support pregame classification. Each line retains its provider and raw terms, without guessing spread direction.
- `backfill_progress.json`: resumable daily backfill cursor. A day is reviewed when its returned finals have team statistics and athlete rows for both teams, or an explicitly incomplete summary has been fetched at least twice. Incomplete event IDs stay listed and must be excluded from fitting until coverage is sufficient. Reviewed does not mean complete.

A scheduled 4:30pm Central capture is NOT a verified closing line. Games that already started are excluded from pregame classification. Missing odds are not zero and must not be silently dropped from coverage reports. No clean prospective prediction set exists here. A pregame odds snapshot alone is not a sealed model prediction.

`legacy_finals_2027.json.gz` preserves 192 imported, unique ESPN postgame records. Their original fetch times were not retained. They are a recovery aid, not point-in-time pregame features. A prior November 6 late-evening odds run included in-progress lines and incomplete timing/coverage. It is excluded from prospective grading and is not part of this dataset.

## Commands

Run from the repository root:

```sh
python3 tools/model_cbb_v1/collect_espn.py daily --summary-limit 100
python3 tools/model_cbb_v1/collect_espn.py odds --day 20261107
python3 tools/model_cbb_v1/collect_espn.py backfill --start 2024-11-01 --end 2026-04-15 --day-limit 7 --summary-limit 100
```

`daily` refreshes the previous four Central-time calendar dates. Run again to finish a capped summary batch. Check the printed diagnostics, including fetch failures and incomplete summaries. `range --start YYYY-MM-DD --end YYYY-MM-DD` refreshes a specific interval. Backfill is capped and resumable; capture success is not assumed when an HTTP request fails. Commit and push the resulting data after each successful collection, so a lost local working copy does not lose the records. Never commit credentials.

## Model-research boundaries

Use only information available before each game's tip as model features. These retrospective postgame fetches do not authenticate historical pregame ranks, rosters or talent ratings. Season-final values cannot become earlier-season features. Injuries have no numerical effect until separately tested; missing status is not health clearance.

Feature selection and calibration belong on validation data only. The 2026 NCAA tournament is reserved as the final test, not a feature-selection window. The 2026-27 season is a separate prospective track. Held-out loss, calibration and simple-baseline comparisons remain to be established. Market comparison requires an honestly labeled captured baseline, not an assumed close. Public recruiting, roster, advanced-stat and matchup inputs are research candidates, not implemented or validated features.

## Bulk history route (November8)

Use [BULK_HISTORY.md](BULK_HISTORY.md) for ending seasons2023-2026, source hashes and gap audit. Bulk assets supersede the slow daily historical backfill for these seasons; retain its partial records as provenance. Current-season daily collection and pregame odds captures remain separate. Experimental preserved code in research/experimental_20261108 has known leakage/side-mapping defects; read REVIEW.md before any use. No predictive validation or forecasts are supplied.
