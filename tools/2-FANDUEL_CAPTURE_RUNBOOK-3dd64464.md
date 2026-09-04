# FanDuel VA structured capture

The cloud browser must first load `https://sportsbook.fanduel.com/navigation/nfl?tab=player-props`. Confirm the page says Virginia and the market service host is `smp.va.sportsbook.fanduel.com`. Fetch the page's `sbapi/content-managed-page` JSON inside that browser session. Save the returned JSON, then run:

```bash
python3 fanduel_capture_parser.py content-managed-page.json fanduel_player_props_ledger.csv VA
```

The parser accepts only the verified VA catalog. It reads structured market, event, runner, market ID and selection ID objects. It never parses DOM text. It selects only passing yards, passing touchdowns, rushing yards, receiving yards, receptions and anytime touchdown markets. It atomically appends to the separate prop ledger, preserving snapshots at new capture times and dropping only exact retries.

Fail closed if state is not VA, the feed shape changes, eligible capture is empty, IDs are absent, a price is malformed, a required line is absent, a player label cannot be parsed, or the existing ledger schema differs. Never reuse stale prices or write partial rows. Report the failure instead.

Current limitation: FanDuel's payload does not expose a durable player ID in these market objects, so `player_id` remains blank; identity is retained through market ID + selection ID and player name. Do not invent an ID from the name.

Tennessee is not reachable from the Virginia browser. The TN config and TN market-price host exist, but VA market IDs return an empty list on TN; URL paths, query parameters and the region cookie do not steer this browser away from its geolocated VA catalog.


## Tennessee eligibility gate

Use `fanduel_tn_market_policy.json` as the UI and capture policy. The capture admits only six objective professional NFL types that are not prohibited by Tennessee rule: passing yards, passing touchdowns, rushing yards, receiving yards, receptions and anytime touchdown. This classification means the market type is not prohibited; it does not prove that the exact VA market is currently offered in FanDuel Tennessee. Label displayed rows "VA price / TN-eligible market type" and tell the user to check the exact TN market and price in the FanDuel app. Hide all unknown or prohibited types.

Never ingest college player props. The CFB pipeline remains sides and totals only. Tennessee prohibits individual actions/events/statistics in college events and in-game team propositions. Virginia broadly prohibits college propositions.

Primary sources:
- Tennessee current SWC rules: https://publications.tnsosfiles.com/rules_all/2018/1350-01.20250630.pdf
- Tennessee SWC FAQ: https://www.tn.gov/swac/about/faqs.html
- Tennessee SWC glossary: https://www.tn.gov/swac/inquires/glossary.html
- Virginia Lottery Sports Betting Catalog: https://www.valottery.com/aboutus/casinosandsportsbetting/sportsbetting

## CFB (added 2026-09-04)
- CFB route is `https://sportsbook.fanduel.com/navigation/ncaaf` (`/navigation/college-football` 404s).
- The sbapi content-managed-page JSON endpoint is not directly fetchable from the sandbox or via in-page fetch (CORS / HTTP 400 without SPA headers). Scrape the rendered DOM instead: event links match `a[href*="/football/ncaa-football-games/"]`; climb to the parent `LI` for one event per row. Row innerText layout: `[away rank?] away [home rank?] home, away_spread, away_spread_odds, away_ml, "O <total>", over_odds, home_spread, home_spread_odds, home_ml, "U <total>", under_odds, kickoff ("SAT 7:30PM ET"), "Stats", "More wagers"`. Rank numbers are bare digits next to team names; strip them. Page lazy-loads all season games (~120 events) without scrolling; filter kickoff prefix for the day you want.
- Sides/totals/ML only; no college props (TN/VA). VA lines are a labeled proxy, never Garrett's TN prices; book lines are display-only, never model inputs.
- Week-1 capture: tools/ledger/8-cfb_week1_fanduel_va_20260904T1801Z.csv (61 Sat 9/5 games; join to ESPN names via pair-wise token-subset match with aliases: WV Mountaineers=West Virginia, Connecticut=UConn, Miami Ohio=Miami (OH), Appalachian State=App State, Nicholls State=Nicholls, Southeast Louisiana=SE Louisiana, Sam Houston State=Sam Houston, FIU=Florida International, Louisiana=Louisiana Ragin' Cajuns, Hawaii=Hawai'i).
