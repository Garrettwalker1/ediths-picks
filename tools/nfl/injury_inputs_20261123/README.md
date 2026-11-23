# NFL injury source layer, November 23, 2026

Working development implementation only. No numerical forecast effect, allocator, injury penalty, return share restoration or active forecast caller change.

`source_adapter.py` consumes retained current-season sources without network calls. It separates ordinal depth snapshots, weekly injury designations, snap exposure and ESPN status entries. It uses unique stable-ID crosswalks only, retaining unmapped identities. ESPN player IDs come from consistent athlete links, never injury entry IDs. Depth selection is strictly before the supplied decision time, per team, and checks formation/position-slot/rank uniqueness. Record-load times are not disclosure times or lineup certainty. Weekly injury rows have no per-row timestamp. A retained ESPN response cannot be applied to an earlier decision.

`source_layers.json` is an incorporated descriptive artifact from sources retained on November23. Its decision-time field is a development as-of bound, not a public forecast issuance or a fresh status collection. No polling was added. Original source receipts and hashes are retained. Seven latest depth rows and two ESPN crosswalk misses remain unresolved. The CartNa00 snap crosswalk remains unmapped even though Carter has a separate ESPN-to-depth identity chain. Exposure snaps do not become additive carry or target shares. Seasonal baseline mixture alignment is still required before any numerical input.

Reproduce:
```
python source_adapter.py --decision-time 2026-11-23T21:08:20Z
python -m unittest test_source_adapter.py
python -O -m unittest test_source_adapter.py
```
Twelve actual unit tests pass normal and optimized. These test mechanics, not predictive quality. No historical2020-23 audit was reopened. Parent retains coordination of opportunity-history work; existing carry estimator dependencies already provided through parent need no recollection.

Source semantics checked in official documentation:
- https://nflreadr.nflverse.com/articles/dictionary_depth_charts.html
- https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html
- https://nflreadr.nflverse.com/articles/dictionary_injuries.html
- https://nflreadr.nflverse.com/articles/dictionary_snap_counts.html
