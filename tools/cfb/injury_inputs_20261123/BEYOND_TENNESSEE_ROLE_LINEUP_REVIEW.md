# Beyond-Tennessee injury inputs: verified roles and official starting lineups

Research checkpoint, November 23, 2026, 1:05 PM CT. Prepared for the 3 PM review. Research only. Existing forecasts and protected evaluation remain unchanged.

## Decision

Free official gamebooks do fill a gap that ESPN positive counting statistics cannot fill: actual offensive/defensive starters, offensive-line starting-five changes, and participation. Two complete team-season collections now provide a working adapter, with source-quality gates and explicit identity matching. They do not solve prospective workload probabilities, medical clearance, snap shares, or causal injury costs.

The most important new integration fix is role classification. A current-roster WR can actually be an emergency QB. Automatically holding all non-QB passing shares fixed as trick plays is wrong for that case. Use a sourced event-specific role override, not a permanent position change or a heuristic that turns every WR pass into QB play.

## Verified North Texas transition

The November 17 ESPN report attributes to coach Neal Brown that Tayven Jackson would miss at least the next two games, Tulane and UAB, not the entire remaining season. Chaston Ditta was also ruled out for Tulane. The official November 17 team preview names Chris Jimerson as the replacement starter.

The official November 21 recap then reports Jimerson left with an injury and WR James Tyre played quarterback, with White and Haygood also taking direct snaps. This supersedes a simplistic assumption that the first replacement remained available for a full game. A November 23 RotoWire note predicts Jimerson should remain starter without addressing the subsequent injury in the official recap. That prediction is not sufficient clearance or a resolved UAB role distribution.

The play ledger independently matches the official recap's 29 straight rushing snaps after the final Jimerson play and before Tyre's first pass. The 29 accepted rushes split 12 White, 11 Haygood and 6 Tyre. These are carrier counts, not QB snap counts. Individual RB direct snaps cannot be assigned from those carrier fields. ESPN display clocks include placeholders and differ from play text, so this segmentation uses source order and durable play IDs. The final Jimerson pass involved interference and is quarantined for rate calculations, but remains a valid sourced transition boundary.

North Texas's exact production baseline still contains 300 Jackson pass attempts out of 347 FBS-v-FBS attempts, or 86.46%. It also contains 29 Jimerson, 11 Ditta and 7 Tyre attempts. Old absence is therefore not automatically fully absorbed. But the correct future mixture is unresolved, so no arbitrary player penalty is added. Tyre's roster position is WR while his November 21 event role is QB_EMERGENCY. The adapter preserves that distinction.

## Lineup collection and quality

| Team | Official 2026 games collected | Starter/participation rows | Exact ESPN identity matches | Important quality limit |
|---|---:|---:|---:|---|
| North Texas | 11 | 695 | 695 | November 21 defensive starters table contains only 10 entries |
| Houston | 11 | 667 | 663 | Four unmatched reserve participation rows represent two distinct people, not four identities |

Both collections include the FCS game. The existing model's exact FBS history IDs remain the integration scope. Collection breadth does not authorize mixing FCS observations into those model rates.

Identity matching requires the same team, full normalized name and jersey. Historical jersey changes can bridge only through the exact same official roster URL already independently matched in another row. No fuzzy name-only join is accepted. North Texas Roberto Rodriguez has historical participation jersey 97 and current roster jersey 64; the exact official URL bridge resolves this without pretending jerseys never change.

North Texas's observed OL starter sets change between Goodacre, Shaw and Rodriguez over the season. The November 14 to November 21 transition changes one of five starters, Goodacre to Rodriguez. This is an observed lineup change, not proof of injury. Missing from a starter table alone is not absence from the game. The defensive 10-entry table is explicitly barred from complete-unit-state admission rather than inventing an eleventh player.

Houston provides an independent second case. Official November 13 and November 21 listed starting offensive lines are identical. This does not establish continuity of actual snaps or health. QB changes from Conner Weigman to Keisean Henderson while the other ten listed offensive starters are the same. That improves descriptive separation of a QB transition from a simultaneous listed-OL change. It is not a causal estimate, because opponents, game state, health, substitutions and scheme still differ. The official recap and November 23 award report confirm Henderson's first start. A November 21 injury report concerns that game and does not establish Weigman's status against Baylor.

Houston's exact FBS baseline contains 287 Weigman attempts and 29 Henderson attempts, not the all-opponent official cumulative 299 and 36. The difference includes the excluded FCS game. Replacing model denominators with cumulative-site totals would silently change scope.

## Integration path

1. Retain the official source URL, content hash, observed collection time and event date for every lineup row. Postgame collection is not proof the row was available before kickoff.
2. Join official team-season athlete URLs to ESPN IDs through strict verified matches and exact URL bridges. Keep unresolved identities unresolved.
3. Store observed starter and participant state separately from medical status, current depth chart and prospective workload.
4. Add event-scoped role overrides for documented emergencies before constructing historical QB versus trick-play mixtures. A Tyre override applies to North Texas/Tulane only. Other games and teams retain their roster role.
5. Enforce 11-player and 5-OL completeness checks before complete-unit comparisons. Preserve incomplete-source warnings.
6. Build future workload only from current corroborated coach/depth-chart/availability evidence or label it a conditional scenario. Current evidence does not justify UAB probabilities for Jimerson/Tyre or a Baylor start assumption for Henderson.
7. Keep rate estimation and a linked feature-accounting stage separate. This descriptive adapter does not rescue the previously rejected QB variance prior or unit-state causal inference.

The code includes nine explicit assertions for event/team role isolation, season collection scope, incomplete-lineup rejection, verified North Texas identities and unchanged Houston OL. These are not nine independent unit tests, and they are not an accuracy result.

## Independent qualification

The publisher's independent replay agrees with the official source rows and supports event-scoped emergency-QB classification. Four unmatched Houston reserve rows represent two distinct people. This qualifies only the descriptive source and event-role layer, not prospective workloads, direct-snap attribution, snap/health continuity or numerical injury forecasting. The independent audit is preserved separately as independent_audit.json.

## Sources

Official schedule links were used to discover the boxscores; all 22 raw official pages and their source manifests are attached in the package. URLs below were observed, not constructed from guessed event IDs.

- North Texas official schedule: https://meangreensports.com/sports/football/schedule/2026
- North Texas November 17 preview: https://meangreensports.com/news/2026/11/17/football-mean-green-hit-the-road-to-face-tulane
- North Texas November 21 recap: https://meangreensports.com/news/2026/11/21/football-mean-green-drop-heartbreaker-at-tulane
- North Texas/Tulane official boxscore: https://meangreensports.com/sports/football/stats/2026/tulane/boxscore/7208
- North Texas/Tulane gamebook, linked from official boxscore: https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/meangreensports.com/stats/football/2026/pdf/20261121025348-45025.pdf
- ESPN November 17 Jackson report: https://www.espn.com/college-football/story/_/id/50513204/north-texas-qb-tayven-jackson-upper-body-injury
- RotoWire November 23 speculative Jimerson starter note, not accepted as clearance: https://www.rotowire.com/cfootball/headlines/chris-jimerson-news-accounts-for-td-in-first-start-241119
- Houston official schedule: https://uhcougars.com/sports/football/schedule/2026
- Houston/West Virginia official boxscore: https://uhcougars.com/sports/football/stats/2026/west-virginia/boxscore/16252
- Houston November 21 recap: https://uhcougars.com/news/2026/11/21/-20-21-20-football-rallies-in-win-at-west-virginia
- Houston November 23 award report: https://uhcougars.com/news/2026/11/23/football-henderson-yates-receive-weekly-big-12-conference-honors
- ESPN November 21 Weigman injury/Henderson report, subsequently updated to recap: https://www.espn.com/college-football/story/_/id/50550966/sources-houston-qb-conner-weigman-henderson-start

No paid source, signup, roster commitment, bet or group disclosure was made. Numeric forecasts were not changed. The earlier conditional Tennessee RB candidate remains conditional only.
