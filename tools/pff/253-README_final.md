# PFF Premium Stats exports

Source: PFF Premium Stats (premium.pff.com) via Garrett's account, historical training input (9/3 steering).
Pulled 2026-09-04 via the site's own CSV export (By Position views, full-season week ranges).

Scope: NFL + NCAA (FBS players), seasons 2020-2025, sessions REG (regular season),
PO (postseason: NFL playoffs / NCAA bowls+playoff), PRE (NFL preseason).
Facets: passing, rushing, receiving, defense. File names: <league>_<season>_<session>_<facet>.csv.

Contents are PFF counting stats (attempts, completions, yards, TD, INT, sacks, targets,
tackles, etc.). PFF grades are NOT included: they are locked on the account's current
subscription tier (API marks grade fields restricted). 9/4 user decision: stats are
sufficient for training; grades not pursued.

Known gaps:
- NFL 2020 PRE: no data - the 2020 preseason was canceled (COVID). Not a pull failure.

Note: files in this folder carry GitHub web-upload numeric prefixes (e.g. `14-nfl_2020_REG_passing.csv`). Match by the suffix name.
