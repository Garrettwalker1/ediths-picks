# Talent composite input (v2.1)

Source: 247Sports College Football Team Talent Composite, public pages
(https://247sports.com/Season/<YEAR>-Football/CollegeTeamTalentComposite/), scraped 2026-09-06.
Fields: team (ESPN display name), season, team_247 (source name), rank, avg, talent (composite total points).

Preseason-published each August -> prior-known at prediction time, no leakage.
Service academies are missing from 247's composite in some years (their data gap):
imputed backward-only from each team's most recent prior composite (marked in team_247).
FCS opponents and any still-uncovered team are imputed at the season's FBS floor in the
pipeline (conservative: shrinks the feature's measured value).
Team-name mapping: 247 short names -> ESPN display names, explicit overrides for
Miami/Miami (OH), Louisiana/Louisiana Tech, App State's 2024 ESPN rename, FIU, Hawaii,
San Jose State, UMass, UL Monroe, Southern Miss 2020 variant.

Validation (same protocol as v2: train 2020-2023, validation 2024, locked test 2025,
ridge alpha=10, identical rows): v2_full repro 13.267 -> v2.1 (+d_talent) 12.940 MAE,
winner accuracy 70.2% -> 72.0%. Validation-2024 agrees (13.493 -> 13.222).
Bootstrap vs v2_full: mean delta -0.327, CI95 (-0.596, -0.064), 99% better.
Gain concentrated in high-talent-gap games (13.82 -> 13.10).
