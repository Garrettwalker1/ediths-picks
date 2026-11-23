# Source snapshots and receipts - NFL prospective injury-input evidence
All retrieved 2026-11-23 from the workspace. sha256 recorded per file. All free; nflverse files CC BY 4.0.

## Files in nfl-source-snapshots-20261123.zip

1. injuries_2026.parquet (69,477 bytes, sha256 0a776262ba55a0189173012de70d8ccde752d72f17fd7631bee5c8813604622f)
   URL: https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.parquet
   Release timestamp.json at retrieval: {"last_updated":"2026-11-23 02:01:31 EST"} (pipeline upload time, not disclosure time)
   Columns: season, season_type, game_type, team, week, gsis_id, position, full_name, first_name, last_name,
   report_primary/secondary_injury, report_status, practice_primary/secondary_injury, practice_status.
   NOTE: the official dictionary lists date_modified, but the actual retained 2026 file contains no per-row
   timestamp; the file governs. Timing semantics are week + release upload time only.
   Rows are one per player per week (final report). report_status: Out 712 / Questionable 762 / Doubtful 61 / none 1,946.
   practice_status: Full 1,824 / DNP 880 / Limited 773 / none 4.

2. depth_charts_2026.parquet (3,519,603 bytes, sha256 0566641e1602790a2d4fc6077708703ca1a4371d3b3632dd6203bd590e9bbd94)
   URL: https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2026.parquet
   Release timestamp.json at retrieval: {"last_updated":"2026-11-23 02:01:34 EST"}
   Columns: dt, team, player_name, espn_id, gsis_id, pos_grp_id, pos_grp, pos_id, pos_name, pos_abb, pos_slot, pos_rank.
   dt semantics per the official dictionary (https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_depth_charts.csv):
   "The timestamp (ISO8601-formatted text) indicating when the data record was loaded." Record-LOAD time, not
   first disclosure and not assured kickoff starter identity. pos_rank: "Player's rank on depth chart grouped by
   pos_slot" - ordinal within position SLOT, not pos_abb (WR spans slots 1/2/8, RDE 3/4, WLB 4/5; KC RBs all slot 11).
   From 2025 onward each update is appended as a new timestamped snapshot (nflverse schedule page). 313 distinct dt
   values 2026-03-22 to 2026-11-23T07:01:28Z; all 32 teams have a 2026-11-23 snapshot; 2,395 latest rows, no duplicate
   slot-rank keys; 7 latest rows lack gsis_id (2 also lack player_name) - identities unknown and explicit.

3. snap_counts_2026.parquet (151,849 bytes, sha256 cfbe0260477f668c30ccd10d3976a0d9b7b1cf7732e1a2684c43fbf314f86ea1)
   URL: https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2026.parquet
   Release timestamp.json at retrieval: {"last_updated":"2026-11-23 07:04:20 EST"} (PFR-sourced; upstream cadence governs)
   Columns: game_id, pfr_game_id, season, game_type, week, player, pfr_player_id, position, team, opponent,
   offense_snaps/pct, defense_snaps/pct, st_snaps/pct. IDs are PFR, not gsis: joining to injuries/depth requires
   the players crosswalk (below) or game_id + name. Snaps are playing time, NOT workload shares (see memo).

4. players.parquet (crosswalk, sha256 8c946dc73db0fb38d9f387e4e745c89ea08bde66efc4d7b32e6aaf74649cdd49)
   URL: https://github.com/nflverse/nflverse-data/releases/download/players/players.parquet
   Release timestamp.json at retrieval: {"last_updated":"2026-11-22 10:51:51 EST"}
   24,871 rows; includes gsis_id, pfr_id, espn_id, pff_id and more.

## ESPN injuries JSON (separate attachment: espn_injuries_20261123T1919Z.json)

5. espn_injuries_20261123T1919Z.json (8,748,720 bytes, sha256 f5b2f6ff7388ebf76fe87f655f076687cced14909427bd96b9badf981f263a32)
   URL: https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries
   Response timestamp 2026-11-23T19:19:41Z; 32 teams, 800 entries. Per-entry keys: athlete, date, details, id,
   longComment, shortComment, source, status, type. date is ESPN's per-entry last-update time. Statuses observed
   include Out / Questionable / Active / Injured Reserve; longComment narratives include transactions
   (practice-squad elevations) and game-day inactives. Undocumented endpoint; terms of use apply, no published license.

## Verified stable-ID join chain (KC backfield example)

- injuries: Kenneth Walker III -> gsis_id 00-0038134 (week-11 row, report_status Out, groin, DNP).
- depth charts: gsis_id 00-0038134 joins directly; 313 rows, pos_rank 1 (RB1) on first and last snapshot.
- snap counts: pfr_player_id WalkKe00 (and JohnEm01, OttxJa01, CartNa00 for Johnson/Ott/Carter).
- players crosswalk: WalkKe00 -> 00-0038134 (matches injuries), JohnEm01 -> 00-0041013, OttxJa01 -> 00-0040959.
  GAP: CartNa00 (Nathan Carter, practice-squad elevation 11/21) has NO gsis_id mapping in the players release as of
  2026-11-22 10:51 EST - late signings/elevations can lag the crosswalk. Carter's ESPN link ID (4605841) chains to
  his depth gsis_id, but that does not resolve the separate PFR snap mapping gap; that join stays withheld, not
  name-filled. Name+team+game_id joins are the fallback and must be logged when used. A name-only join already
  caused one miscount here: injuries "Omar Cooper Jr." missed his PFR snap row; the ID join reproduces the
  publisher's count (3 of 14 week-11 Out skill players had positive week-10 snaps: Marks 30, Williams 50, Cooper 1).
- ESPN identity: entries have no direct athlete.id field; entry id is not athlete id; player IDs recovered from
  player links are unique/consistent across the 800-entry snapshot; 2 link IDs do not match the players crosswalk.

## Schedule/results reference used for week-11 coverage checks

games.csv: https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv (schedules release timestamp
{"last_updated":"2026-11-23 11:16:53 EST"}). Week 11: 13 games, 12 final in pbp; pending at build time
2026_11_CIN_WAS 2026-11-23 20:15 ET.
