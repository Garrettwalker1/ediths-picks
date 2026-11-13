"""Apply owner-requested experimental QB input as explicit conditional predictions.
Never converts an unknown side into a confirmed zero effect.
"""
import json,pathlib,datetime,hashlib
P=pathlib.Path(__file__).parent
art=json.load(open(P/'out/integration_artifact_cs.json'));core=json.load(open(P.parent/'current_season_20261113/current_forecasts.json'));by={g['game_id']:g for g in core['games']};out=[]
assert art['cutoff']=='2026-11-13'
for row in art['games']:
 g=by[row['game_id']];assert abs(g['raw_margin_home']-row['core_raw_margin_home'])<1e-10
 z=dict(event_id=g['event_id'],game_id=g['game_id'],baseline_raw_margin_home=g['raw_margin_home'],raw_home_adjustment_pts=None,status='unknown_QB_coverage',conditional_scenario=None)
 if row['away']=='MIN' and row['home']=='GB':
  s=row['away_side'];assert s['starter']=='Kirk Cousins'and not s['prior_dominated'];swing=s['unilateral_team_swing_pts_raw'];m=g['raw_margin_home']-swing
  z.update(status='experimental_conditional_QB_input',conditional_scenario=dict(raw_margin_home=m,display_margin_home=round(m*2)/2,min_team_swing_raw=swing,display_min_team_swing=round(swing*2)/2,assumptions='If Kirk Cousins starts for Minnesota and Green Bay stays at its baseline-embedded QB production. The Green Bay unchanged-production assumption is not verified health, confirmed starter status, or a measured zero injury effect.',role_status='Minnesota starter not announced in the owning-team source checked Nov13 14:10CT. Cousins is a scenario, not confirmed.',source_urls=s['role_urls'],season_dropbacks=s['season_dropbacks'],shrink_weight_on_data=s['shrink_weight_on_data'],coefficient_only_team_swing_ci95=s['unilateral_swing_coefficient_only_ci95'],uncertainty='Coefficient-only interval crosses zero and is NOT full predictive uncertainty. It excludes player-quality, role, embedded-proxy and confounding uncertainty. Association, not causal injury effect. Non-QB injuries not included.'))
 elif row['away']=='SEA'and row['home']=='LV':
  z.update(status='withheld_prior_dominated_replacement_quality',coverage_note='Darnold ruled out; Lock expected, not confirmed. Mendoza named by Raiders. Lock 78 current-season dropbacks, data weight 22.1%; Mendoza 8, weight 2.8%. League-mean prior dominates both. No numerical replacement-quality claim or adjusted spread.',source_urls=row['away_side']['role_urls']+row['home_side']['role_urls'])
 else:z['coverage_note']='Current QB roles and replacement coverage not verified. Unknown is not healthy or zero effect. Baseline only.'
 out.append(z)
res=dict(version='NFL-experimental-current-season-QB-input-v1',generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),core_version=core['metadata']['version'],performance_status='Owner-directed experimental inclusion without another performance test. Accuracy improvement not established.',scope='QB passing production only. 1 conditional game prediction; 12 games without numerical adjustment. No non-QB or CFB injury effects.',engine_cutoff=art['cutoff'],full_game_injury_adjustments=0,conditional_predictions=1,games=out)
(P/'injury_overlay.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps([r for r in out if r['conditional_scenario']],indent=2))
