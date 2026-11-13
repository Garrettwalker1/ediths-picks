import pathlib,json,hashlib,math
P=pathlib.Path(__file__).parent;d=json.load(open(P/'injury_overlay.json'));a=json.load(open(P/'out/integration_artifact_cs.json'));core=P.parent/'current_season_20261113/current_forecasts.json'
assert core.read_bytes()==(P/'raw/current_forecasts.json').read_bytes()
assert len(d['games'])==13 and len({g['event_id']for g in d['games']})==13
assert all(g['raw_home_adjustment_pts']is None for g in d['games'])
sc=[g for g in d['games']if g['conditional_scenario']];assert len(sc)==1
r=sc[0];s=r['conditional_scenario'];assert r['game_id']=='2026_10_MIN_GB';assert abs(s['raw_margin_home']-(r['baseline_raw_margin_home']-s['min_team_swing_raw']))<1e-12
assert s['display_margin_home']==round(s['raw_margin_home']*2)/2==-1.5
assert 'Green Bay' in s['assumptions']and 'not verified health'in s['assumptions']
assert 'not announced'in s['role_status']
sea=[g for g in d['games']if g['game_id']=='2026_10_SEA_LV'][0];assert sea['conditional_scenario']is None and sea['status']=='withheld_prior_dominated_replacement_quality'
assert all(g['raw_home_adjustment_pts']is None for g in a['games'])
roles=json.load(open(P/'roles_input.json'));assert all(roles[t].get('player_id')for t in ['MIN','SEA','LV'])
res=dict(correctness_not_accuracy_test=True,unchanged_core=True,game_rows=13,conditional_predictions=1,full_game_adjustments=0,exact_scenario_arithmetic=True,unknown_and_prior_dominated_stay_null=True,stable_ids_explicit=True,nonQB_and_CFB_uncovered=True)
(P/'integration_checks.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
