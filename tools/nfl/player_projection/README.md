# Fixed-model weekly input refresh

This is an input-compatibility repair, not a new model or validation claim. Never rerun the archived 2025/seven-league generator. Its direct execution is disabled.

## Generate a candidate

Requirements: Python 3.10+, pandas, numpy. No serialized model, temporary fitted object, scikit-learn, or login is needed for these public input reads.

From any checkout path:

```
python tools/nfl/player_projection/test_refresh.py
python tools/nfl/player_projection/refresh.py \
  --output /tmp/player-projections-candidate.json \
  --sources-dir /tmp/player-projections-sources
```

The runner discovers the upcoming regular-season slate from dated nflverse games, including January games belonging to the previous season. It never reads calendar year as season without a dated schedule join. It refuses a slate that has already begun, unfinished prior games, missing completed-game team stats, mismatched game IDs, duplicate player-week rows, missing required features, wrong-season/wrong-team roster feeds, ambiguous roster names, empty fantasy rosters, fewer than eight distinct leagues, or a fantasy snapshot older than four days. A review can choose to wait for a new snapshot rather than widening that limit.

It fetches current player stats for every season from 2023 through the discovered season and all 32 current ESPN roster feeds. The Rams source URL uses `lar`, while nflverse's internal team key remains `LA`. Only prior completed weeks enter features. Current roster membership is not game clearance; IR and older histories stay explicit. Players with fewer than three usable history rows or ambiguous IDs are unranked, never silently zeroed.

The model uses only the published fixed 2023-25 coefficients/scalers, protected by a SHA-256 fingerprint. It never trains, tunes, recalibrates intervals or retests the preserved holdout. A coefficient change stops inference for review. Ten offline tests cover exact prior 252-player/six-output reproduction, all 463 Nov 3 numerical player rows and 435 matchup rows, week/season discovery, January season handling, missing final/stats failures, duplicate roster identity, begun-slate refusal, and exclusion of the current week.

## Review before publication

The output is always a separate atomic candidate. Direct root `player_projections.json` overwrite is forbidden. Source responses and a manifest with URLs, capture time and hashes are retained in `--sources-dir`; none contains credentials. Review:

- slate/week and every prior completed game's team-stat coverage;
- roster additions/removals and history cutoffs;
- all numerical changes against production, with any source revisions;
- exact eight-league fantasy snapshot date and matching coverage;
- frozen parameter hash, unchanged holdout text and disabled book input;
- at least 150 modeled players, 100 descriptive matchup rows, 20 snapshot highlights, probability/interval bounds and unexplained coverage drops.

Then publish only under the existing site-publishing authority. Copy the reviewed candidate to the root, retain the audit/source snapshots, update any static caption or dated research copy to agree with generated metadata, inspect 390x844 pixels and all affected panels locally, commit/push using the saved repo-only credential, delete the credential file, wait for actual deployment, and verify public JSON and pixels. A push is not a completed publication. An old failed or queued run is not the disposition of a newer successful run.

Do not call these opponent-adjusted, injury-adjusted, calibrated betting probabilities, or a validated edge. Matchup context is descriptive only. RB/WR/TE only, no quarterbacks. Fixed interval widths are unchanged research ranges. Generic TD logit differs from the h12/k4 TD board. Fantasy highlighting is a dated snapshot, not live ownership/waiver availability.

## November 4 dry run (not published as data)

Discovered 2026 Week 9 and completed history through Week 8. The candidate had 461 players, 433 matchup rows, 77 unranked and 73 highlights from the Nov 4 eight-league snapshot. Compared with Nov 3 production, roster feeds removed Kenny Yeboah and Alex Bachman from this current modeled set. Provider Week 7 Seattle air-yard-share/WOPR revisions and Emanuel Wilson receiving air yards changing from 7 to 3 produced three rounded-output changes (Cooper Kupp, Jaxon Smith-Njigba, Emanuel Wilson). No coefficient changed. Current site data was intentionally not overwritten by this dry run.

The November 3 scripts in the adjacent dated directory are archived run records and have old absolute-path/joblib dependencies. This runner supersedes them for future input refreshes. Do not use those archived scripts as production entry points.
