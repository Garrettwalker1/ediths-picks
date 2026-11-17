# Week11 IND-HOU absence and role companion

Prepared November 17, 2026. This is factual context, not an injury-adjusted forecast. Coverage is only the Thursday IND-HOU game: 25 Monday practice-estimate entries and two additional owning-source IR entries. No league-wide clearance is claimed.

## What the sources establish

- The dated Texans Week11 report supplies Monday practice estimates, not final game statuses. Marks is DNP and Montgomery FP. Neither is a formal Out/cleared decision.
- The Colts Monday notebook identifies new Week10 in-game exits for Gardner, Ward and Raimann, and continuing missed-game context for Carlies, Mallory, Travis, Rhodes and Tillery. These facts do not settle Thursday participation.
- The owning Colts Week11 depth chart confirms Alie-Cox and Davis-Gaither on IR. Ogletree moves up one TE place; CJ Allen is listed MLB1. The depth chart is explicitly unofficial, and it supplies no workload percentage.
- Montgomery's owning player log lists his last rushing appearance in Week5. The Nov14 transaction confirms Week10 Out; the new FP estimate does not confirm a Week11 return or assign him Marks's work.

All 27 entries join by exact ESPN ID to the preserved ESPN/GSIS crosswalk. The three name aliases are explicit in build.py. Current roster status and injury tags are preserved separately from owning-source facts. In particular, a roster's generic status can lag a dated IR announcement.

## What can and cannot change

There are zero numerical scenarios in this companion. HOU's raw core home margin remains 6.549619046252752, displayed HOU -6.5. The core injury adjustment remains null. Every future workload and replacement point effect remains null.

The old separate skill-only contract requires same-week formally Out established RB/WR/TE players, at least two prior stat-row appearances and at least 2% trailing team attempts+carries+receptions. Only Marks and Montgomery pass that volume gate among this register's entries; a volume gate alone does not establish eligibility. No qualifying formal Week11 Out event is established here.

IR-only absences, OL, defense and special teams fall outside that contract, not at zero actual effect. The old observational skill coefficient cannot establish replacement-specific effects, and its coefficient-only interval includes zero. Do not stack it with the separate QB passing scenario. The core is a mixed realized-history reference, not a healthy-roster counterfactual.

## Data and preservation

`build.py` deterministically joins the checked sources to the unchanged Nov17 production/core artifacts. `companion.json` retains source URLs, individual source times, exact IDs, trailing volumes, last stat rows, role evidence and limitations. Production uses only the 150 completed 2026 REG games before Nov17. Source bytes/hashes and core/stat hashes are retained.

A production stat row is not an offensive snap count or participation proof. A missing row, especially for OL and special teams, does not establish absence. Last positive volume is historical usage, not a future share. No targets-to-points, recovery rate, arbitrary injury penalty, return-workload projection or individual-stat QB adjustment was added.

No old forecast, seal, existing scenario, player/TD probability, or comparison price changes in this companion. Run `python build.py` and `python test_companion.py` from this directory for the factual rebuild/checks. A live source check is required before calling any later rebuild a fresh availability review.

## Afternoon source check (Nov17, 14:45 CT)

The owning Texans Nov17 transaction confirms Azeez Al-Shaair on Reserve/Injured. The owning Colts Nov17 transaction confirms Jaylon Carlies on Injured Reserve and Quez Watkins signed to the 53-man roster. Both linebackers were already in the Monday estimate register; those original estimates and their source times remain. Availability confirmation and its later source time are separate fields. No source-grounded replacement workload or numerical defensive effect is supplied. The Colts article has a day-label conflict: Tuesday subtitle/Nov17 publication, Monday final boilerplate. We rely on the explicit IR action, not an exact transaction-day conclusion.

Fresh checks of the dated Week11 Texans report and Colts Monday notebook still showed only Monday estimates. Marks is not promoted to formal Out; Montgomery FP is not clearance. The generic Texans week/11 injury page shows a Browns opponent and is rejected for this Colts matchup. No change to any forecast/seal or numerical scenario. Original morning build, companion and manifest are retained under archive_morning. Original fitted panel bytes remain unavailable; recovered builders are not executed or reconstructed.
