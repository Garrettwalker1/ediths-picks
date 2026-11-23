# NFL 2026 current-season efficiency rankings (provisional, descriptive)

Not a live replacement for anything; not a validated predictor; not complete efficiency (no garbage-time
adjustment, no special teams, no opponent-injury context). Coverage is derived from the input file at build
time (games by week in nfl_2026_metadata.json); this build reflects the 2026-11-23 11:21 EST snapshot with
12 of 13 week-11 games final (CIN @ WAS 2026-11-23 pending). Source sha256 and cutoff in nfl_2026_metadata.json.
Denominators are per side: offensive columns use plays with posteam == team, defensive columns use plays with
defteam == team; they differ (e.g. ARI 689 offensive vs 673 defensive plays). Scrambles are play_type run
(587 on this snapshot, zero as pass); the pass split includes sacks but excludes scrambles classified as run.

Files:
- build_current_rankings_nfl.py - reproducible builder; run: python3 build_current_rankings_nfl.py <pbp.parquet> <out_prefix> '<source last_updated from release timestamp.json>'
- nfl_2026_offense.csv / nfl_2026_defense.csv - 32 teams; per metric (success, epa, pass/rush splits):
  accepted plays, raw rate, opponent-adjusted rate, rank. Offense: higher better. Defense: lower allowed better.
- nfl_2026_metadata.json - definitions, coverage, exclusions, source hash/url/cutoff.

Builder v2: per-side denominators, input-derived metadata, built-in consistency checks (aborts on failure). Definitions are pinned in the builder docstring and metadata. Ridge penalty 20 on team effects (fixed, untuned).
Success metric matches the CFB provisional distance-based definition (50/70/100% by down) for cross-league
comparability. EPA is nflfastR's modeled column. Tiny adjacent gaps are effectively ties, not confident ranks.
