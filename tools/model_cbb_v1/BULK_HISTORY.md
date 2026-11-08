# Bulk historical inputs

Public SportsDataverse ESPN-derived releases replace slow per-game historical harvesting. Ending seasons2023-2026 cover2022-23 through2025-26. This is feed-wide season coverage, not a claim of exhaustive D1-v-D1 or complete boxes. See `data/bulk/coverage_audit.json` for exact gaps.

Run `python3 tools/model_cbb_v1/acquire_bulk_history.py`, then `python3 tools/model_cbb_v1/audit_bulk_history.py` (pandas/pyarrow required for the audit). Acquisition is bounded to three metadata requests and at most12 sequential public assets,1second spacing, no parallelism or automatic retries. Cached matching hashes skip downloads. HTTP403/429 or any other error stops the run. A successful bounded batch does not establish a permitted sustained request rate. No paid or authenticated source is used.

Sources and actual URLs, asset modification times, response receipt times, sizes and SHA256 hashes are in `data/bulk/manifest.json`. Preserve downloaded season archives unchanged. Keep historical collection separate from prospective daily ESPN captures.

Do not use schedule current ranks, records, athlete active flags or retrospectively enriched roster/talent fields as historical pregame features. Game outcomes/boxscores only become feature inputs for later games. Enforce stable IDs, season-specific membership, exact side joins and earlier-game-only statistics. Keep validation/final-test boundaries fixed to the research plan; this acquisition does not authorize fitting or evaluating the2026 tournament. Whole-season2026 files include held-out outcomes and must not guide feature choice. Coverage audit is not evaluation.

Attribution: SportsDataverse/sportsdataverse-data, produced by hoopR-mbb-data from ESPN. The repository advertises MIT; its license is retained alongside the archives. Upstream third-party data rights remain with their owners. No permission to sell or relicense upstream data is asserted.

Repository: https://github.com/sportsdataverse/sportsdataverse-data
Producer: https://github.com/sportsdataverse/hoopR-mbb-data
Releases: espn_mens_college_basketball_schedules, espn_mens_college_basketball_team_boxscores, espn_mens_college_basketball_player_boxscores.
