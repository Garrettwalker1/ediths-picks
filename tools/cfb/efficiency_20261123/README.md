# Current-season descriptive offense/defense rankings, Nov23

Display-only release. Existing forecasts, issue seals, ranking resume model, injury-null fields and protected study unchanged. New root cfb_efficiency_rankings.json and cfb-efficiency.js supply independent metric/side selectors and team search.

Sources remain separate:
- Game on Paper / Sportsdataverse adjusted EPA/play, FBS-v-FBS. Offense source stamp2026-11-22T15:02Z; defense2026-11-21T20:09Z, possibly before Saturday games. Only adjusted EPA accounts for opponent/garbage time; displayed raw splits do not. Source-provided ranks preserved despite rounded metric ties.
- Custom fixed-penalty20 opponent-adjusted success,85082accepted regulation plays/686games,138teams. Thresholds50/70/100percent distance on downs1/2/3-4. Defense lower allowed is better. All9whole-game quarantines and unresolved adverse-play omissions retained. Not full-season completeness, causal effect, calibrated point margin or demonstrated forecast improvement.

Original source pages and complete ledger/source manifest are retained beside reproducible builder. Run build_current_rankings.py from this directory, with numpy available. No remote requests or target forecast-error evaluation occur. Each accepted/full-ledger row carries real ESPN source URL, source/play hashes and exact event identity; original source manifest paths refer to preserved archive locations, not public links. Do not claim archive receipt equals pregame preservation.

Independent review reran34ledger/10score guards, rehashed138ESPNteamstat responses from the supporting private source bundle, replayed85082accepted plays, and reproduced all276adjusted rates and rank order exactly. Stats universals zeros/display-only/duplicate fields were NOT inserted as numerical inputs. The full138response bundle is supporting research, not merged into current forecasts.

Public source pages:
https://gameonpaper.com/year/2026/teams/offensive
https://gameonpaper.com/year/2026/teams/defensive
https://www.espn.com/college-football/stats/team

Future refreshes require a fresh source snapshot and new dated directory; never overwrite this release or pretend older defense data is current through a newer offense stamp. Tiny adjacent rank gaps are not confident differences. No betting action.
