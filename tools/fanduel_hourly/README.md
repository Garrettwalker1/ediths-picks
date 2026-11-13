# Hourly FanDuel comparison overlay

Owner: E.D.I.T.H. publisher. Read-only public browser capture, maximum hourly. Original Oct 1 request authorizes automated checks and publication next to the model with actual state labels. No bet placement. No odds as model inputs.

Current route: public signed-out FanDuel Illinois. Explicit Illinois Gaming Board footer required each collection. Never claim Tennessee unless current page verifies it. No login/security prompt without notice. Stop after exhausted botwall/throttling and report; a clock alone is not a new recovery signal.

## Collection

Scout first, acquire a read lease, open NFL `https://sportsbook.fanduel.com/football/nfl` and CFB `https://sportsbook.fanduel.com/navigation/ncaaf`. Wait for game rows. Use rendered DOM only, no write APIs. For each page evaluate:

```js
const path = location.pathname.includes('ncaaf') ? '/football/ncaa-football-games/' : '/football/nfl/';
return {at:new Date().toISOString(),url:location.href,state_evidence:document.body.innerText.split('\n').filter(s=>s.includes('authorized by the Illinois')),rows:[...document.querySelectorAll('a')].filter(a=>a.href.includes(path)&&a.innerText!=='More wagers').map(a=>({teams:a.innerText,text:a.closest('li')?.innerText,url:a.href}))};
```

Store each result as JSON; `update.py` accepts the content wrapper or decoded result. Report site outcome and release. Do not turn missing listings into new prices.

Run `python3 tools/fanduel_hourly/update.py NFL_CAPTURE CFB_CAPTURE` in a current checkout. It validates team pairs and book date against schedule, parses sides/ML/totals, creates append-only raw captures and a separate `fanduel_comparisons.json`. NFL source schedule is currently Week 10; an assert stops publication if the model slate changes. Validate and update the schedule path for a new model slate, never bypass the assert. CFB source is current sealed Week 11. Replace only when the publication advances, never edit sealed model data for odds.

At/past scheduled kickoff retain the last actual prior capture unchanged and flag frozen. If no FanDuel pregame capture exists, retain and label the older published reference; do not fabricate a close. Missing future quotes retain any prior capture with its original time. Raw rows remain available for audit, including rows not joined. Never use a same-pair future-week quote as the current game.

First restored Nov 13, 2026 10:04 CT: 13/13 upcoming NFL, 56/59 upcoming CFB matched. No listed rows for Illinois-UCLA, Northwestern-Ohio State, Nevada-Northern Illinois, so dated references remain. One already-started NFL and eight CFB games keep existing dated references, with no backfilled FanDuel close. Restoration covers game sides, ML and totals capture. Display shows sides/totals. Player props and TD hourly coverage are not restored.

Test syntax/parser, confirm model/seal files unchanged, inspect actual mobile pixels, push, verify live overlay and page. If deployment is not yet live, own a bounded follow-up before reporting complete.

## Partial NFL player comparison route, November 13 afternoon

`fanduel_player_comparisons.json` and `loadFanduelPlayerComparisons` add a visibly PARTIAL NE-DET player comparison board, not full 13-event restoration. All six standard categories were captured from 25 expanded accordions on the event's Same Game Parlay tab; anytime-TD Show more expanded to Show less. Read only accessible selection labels, never click price selections. The parser excludes alt/first/last/defense markets, requires exact market/name agreement, and fails duplicate/ambiguous identities. Fresh same-season ESPN rosters plus unique stable ESPN-to-GSIS IDs from the existing TD snapshot establish current team membership, not game clearance. Missing IDs remain withheld. `player_label_candidate.py`, `test_player_label_candidate.py`, and `build_player_comparison.py` implement the current partial route; the builder now takes an explicit archive, current-slate event ID, independently verified source URL and output path. It emits an event artifact only, never silently replaces the live board. URL, state footer, actual pregame capture time, expanded accordions, all six categories, roster provenance/hash/season, exact identity and matching over/under pairs fail closed. Replay preserves the original source time. A separate per-event publisher must merge/freeze events before wider deployment.

Current archive `player_captures/20261113T214129161Z`: 72 parsed selections, 71 joined, 1 identity gap (Jackson Meeks), 47 player-market rows across six categories. TD comparisons use the existing owner-adopted Oct29 primary probability, still unvalidated and captured November 10; receiving/rushing/reception comparisons use the separately dated generic medians, no current matchup/personnel adjustment. Missing compatible passing projections and unranked players show unavailable, never fabricated model values. Books never feed the models, and no edge/EV claim is made.

Next recurring source round must capture NE-DET at most hourly and own current identity/freeze checks; expand the remaining 12 events with the same fail-closed contract. Until all-game recurrence and display are verified, the full original props/TD restoration remains open. Existing game-comparison hourly route continues independently.

Generalized event build (actual archive replay, not a source refresh):

```sh
python tools/fanduel_hourly/build_player_comparison.py \
  --archive tools/fanduel_hourly/player_captures/20261113T214129161Z \
  --event-id 401873053 \
  --source-url https://sportsbook.fanduel.com/football/nfl/new-england-patriots-@-detroit-lions-35605986 \
  --output /tmp/fd-player-event.json
```

`test_build_player_comparison.py` retains the first capture's comparison reference for exact replay, and rejects wrong URLs, future/post-kickoff captures, missing state, unexpanded accordions and roster hash changes. No source refresh is implied by running tests or rebuilding an archive. `merge_player_comparisons.py` prepares multi-event data with per-event timestamps and kickoff freezes; it rejects less-than-hourly replacements and post-kickoff backfills. Its replay preserves existing quotes byte-for-byte at the row level. Wider-event UI and actual recurring captures remain pending. The merge is not yet wired into the live board.

## Full event source coverage, partial identity joins (Nov13 16:43-16:53CT)

All13 upcoming NFL events now have actual rendered captures of the six requested standard categories:430expanded accordions,1,173parsed selections,1,075strict joins,98selection-level identity gaps withheld,690published player-market rows. Current rosters plus the dated TD snapshot's exact ESPN/GSIS crosswalk are deliberately restrictive; missing stable mappings are not fuzzy-matched. New QB/new-team names can remain gaps even when a market exists. An observed category is not every offered player matched, and book listing is not game clearance.

NE-DET has two actual source rounds more than60minutes apart. Other12events have first captures only; full-slate recurrence is not yet verified. `merge_player_comparisons.py` preserves per-event times and prevents early replacements or post-kickoff backfills. UI event/market filters and every row's book/model time prevent a latest-board timestamp from masquerading as fresh prices for all games. The dated model values have not changed. Unknown passing projections remain unavailable.
