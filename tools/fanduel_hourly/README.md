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
