# Oct15 Week6 source refresh

New separately versioned, unvalidated injury experiment. No baseline or fit changes. The historical Week5 cohort stays byte-identical. No book inputs.

284 Week6 report rows across25/28 scheduled teams, roster IR inventory, snaps through Week5 only.12 numerical games. BUF-LV and WSH-SF have no numerical injury output because BUF/SF/WSH reports are absent.83 inventory rows have missing roles. A roster pfr_id binds nickname variants to snap pfr_player_id, including Pat/Patrick Surtain. No fuzzy-name assumption. IR is provider inventory, not a transaction audit; long absences may be double-counted against scores-only baseline. Sunday/Monday statuses are not final.

Same Oct7 fitted status/practice coefficients and zero-vs-no-injury adjustment, with no refit. No totals, score or win-probability injury adjustment; no DNP participation probabilities or teammate redistribution. Week5 experiment was not better than baseline. Not a betting edge.

Seattle-Denver baseline SEA-0.5, frozen score23-22 and total44.5 unchanged. This snapshot's injury-only experiment is PK, with four missing roles. Raw home margin+0.19 and change+0.90 are unrounded diagnostics, not promoted model values.

Weather is fresh Denver city-grid context only, not a fitted numerical adjustment. Numerical weather adjustment remains unfinished. CFB uses an independent current-status sidecar; its sealed Week7 predictions and gate remain unchanged.

Rebuild independently without overwriting this cohort:

```sh
python3 tools/nfl/week6_2026/refresh_20261015/build_injury_snapshot.py --as-of 2026-10-15T21:30:25.594779+00:00 --output /tmp/rebuilt-injury.json
```

Source URLs are retained in the snapshot, per-row inventory, and source manifests. The Charbonnet PUP/Out override is grounded in the Seahawks final report linked in its row. Baseline source recheck uses the live nflverse schedules release and reproduced all14 frozen Week6 rows exactly.
