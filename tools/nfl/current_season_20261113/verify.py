import json,pathlib,numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
P=pathlib.Path(__file__).parent;d=json.load(open(P/'current_forecasts.json'));tr=json.load(open(P/'training_features.json'));prov=json.load(open(P/'feature_provenance.json'));g=pd.read_csv(P/'sources/games.csv',low_memory=False).set_index('game_id');md=d['metadata'];fs=md['features'];assert len({x['game_id']for x in tr})==len(tr);assert len({x['event_id']for x in d['games']})==13
for p in prov:
 for e in p['context_games']+p['home_history']+p['away_history']:
  assert g.loc[e,'gameday']<p['cutoff_date'];assert int(g.loc[e,'season'])==int(p['game_id'][:4])
 assert p['game_id']not in p['context_games'];assert len(p['home_history'])>=3 and len(p['away_history'])>=3
assert not any(any(v in f for v in ['talent','preseason','prior','odds','line','injury'])for f in fs)
D=pd.DataFrame(tr);X=D[fs].to_numpy();y=D.margin.to_numpy();m=make_pipeline(StandardScaler(),Ridge(alpha=10,fit_intercept=False)).fit(np.vstack([X,-X]),np.r_[y,-y]);assert np.allclose(m[1].coef_,md['coefficients'],rtol=0,atol=1e-10)
for r in d['games']:
 x=np.array([[r['features'][f]for f in fs]]);p=float(m.predict(x)[0]);assert abs(p-r['raw_margin_home'])<1e-10;assert abs(p+float(m.predict(-x)[0]))<1e-10;assert r['display_margin_home']==round(p*2)/2
 assert pd.isna(g.loc[r['game_id'],'home_score']);assert g.loc[r['game_id'],'espn']==int(r['event_id'])
sl=json.load(open(P/'sources/week10.json'));tnf=[e for e in sl['events']if e['id']=='401873052'][0]['competitions'][0];assert tnf['status']['type']['completed'];t={x['team']['abbreviation']:int(x['score'])for x in tnf['competitors']};assert t=={'WSH':24,'NYG':21},t
out=dict(correctness_only_not_accuracy_validation=True,unique_training_rows=len(tr),future_games=13,strict_prior_date_and_same_season_provenance=len(prov),coefficient_rebuild_exact=True,side_swap_and_half_point_checks=True,thursday_final_reconciled=True,no_odds_preseason_prior_year_or_injury_features=True,current_roster_projection_not_verified=True)
(P/'correctness_checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
