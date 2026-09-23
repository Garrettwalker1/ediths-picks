# Fantasy snapshot regeneration runbook

`index.html` only reads the committed root `fantasy.json`. The sync must never put credentials, cookies, invite links, or private raw responses in the repo.

## 1. Collect ESPN in the saved cloud browser profile

Use config-a and a read lease. Navigate to each exact team page and let the client-rendered page settle:

- `https://fantasy.espn.com/football/team?leagueId=1242450525&teamId=8`
- `https://fantasy.espn.com/football/team?leagueId=184489982&teamId=1`
- `https://fantasy.espn.com/football/team?leagueId=416480692&teamId=7`
- `https://fantasy.espn.com/football/team?leagueId=14911042&teamId=10`


For each page, normalize only the visible league/team/roster data into `espn_snapshot.json` using `espn_snapshot.example.json` as the contract. Player rows use:

```json
{"id":"provider player id","name":"Player","position":"RB","nfl_team":"TEN","slot":"RB","points":null,"projected":null,"source":"ESPN Fantasy","source_url":"safe team/fantasycast URL","observed_at":"ISO time","provider_updated_at":null}
```

During season, also open the league scoreboard/fantasycast for the current scoring period. Do not hardcode Week 1:

- `https://fantasy.espn.com/football/fantasycast?leagueId={leagueId}&teamId={teamId}`
- `https://fantasy.espn.com/football/league/scoreboard?leagueId={leagueId}`

Normalize a matchup as:

```json
{"week":1,"opponent":"Team","score":12.3,"opponent_score":8.4,"projected":110.2,"opponent_projected":106.8,"state":"live","source":"ESPN FantasyCast","source_url":"safe fantasycast URL","observed_at":"ISO time","provider_updated_at":null}
```

If any page is a login page, 401, consent wall, or lacks the expected team identity, stop. Preserve the last good `fantasy.json`; do not publish empty ESPN rosters. Release the lease when finished.

## 2. Collect injury status from ESPN Fantasy (permanent, approved 2026-09-23)

Garrett directed that fantasy injury flags come from ESPN Fantasy (and X when publicly readable), never the ESPN NFL injury page (`espn.com/nfl/injuries`), which went stale. Build the ESPN player id list for every rostered player (ESPN roster entries; Sleeper players via the Sleeper player DB `espn_id` or an exact unique name match in ESPN's player pool). In the same logged-in config used for rosters, run `tools/fantasy/espn_injury_status.js` (replace `__IDS__`) with `tools cloud_browser execute-js` on a fantasy.espn.com page and save the returned JSON to `/tmp/espn-injury-status.json`. X is public-read only (specific post oEmbed/syndication); do not sign in. If the ESPN call fails or returns fewer than 50 players, stop and preserve the last good `fantasy.json`.

## 3. Generate

From the repo root:

```bash
python3 generate_fantasy.py \
  --espn /tmp/espn_snapshot.json \
  --injury-status /tmp/espn-injury-status.json \
  --output fantasy.json
python3 -m json.tool fantasy.json >/dev/null
```

The script fetches Sleeper's public league, user, roster, current-week matchup, and NFL player data. It writes atomically only after validating all four expected ESPN leagues (including Not a Dell, 14911042) and the ESPN Fantasy injury status file.

## 4. Validate and publish

Check that there are exactly eight leagues (4 ESPN + 4 Sleeper), timestamps are current, no ESPN login-page text exists, and no sensitive values appear:

```bash
jq -e '.leagues|length==8' fantasy.json
! grep -Eqi 'espn_s2|SWID|cookie|password|inviteId' fantasy.json
```

Serve locally, click Model, Bet tracker and Fantasy at 390x844, and confirm empty/error states and snapshot time. Commit only when `fantasy.json` changed, push, then verify the live `fantasy.json` and Fantasy tab.

## Approved cadence

Preseason: every six hours from 7 AM to 11 PM CT, plus 30 minutes after each draft. In season: every 15 minutes during Thursday/Sunday/Monday game windows; every two hours from 7 AM to 11 PM CT outside game windows; one overnight run around 4 AM. On Wednesday-Friday official practice-report days, run hourly from noon to 7 PM CT. The injury pass runs every time.
