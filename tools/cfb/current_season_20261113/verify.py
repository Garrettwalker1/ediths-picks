import json,pathlib,hashlib,collections,math
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
P=pathlib.Path(__file__).parent;d=json.load(open(P/'current_forecasts.json'));tr=json.load(open(P/'training_features.json'));prov=json.load(open(P/'feature_provenance.json'));g=json.load(open(P/'canonical_used.json'));by={r['event_id']:r for r in g};md=d['metadata'];fs=md['features'];assert len({x['event_id']for x in tr})==len(tr);assert len({x['event_id']for x in d['games']})==len(d['games']);assert not any(any(v in f for v in ['talent','prior','roster','portal','ret_share','qb_ret','gone_share'])for f in fs)
for p in prov:
 assert all(by[e]['date'][:10]<p['cutoff_date']for e in p['context_games']+p['home_history']+p['away_history']);assert p['event_id']not in p['context_games'];assert len(p['home_history'])>=3 and len(p['away_history'])>=3
D=pd.DataFrame(tr);X=D[fs].to_numpy();y=D.margin.to_numpy();m=make_pipeline(StandardScaler(),Ridge(alpha=10,fit_intercept=False)).fit(np.vstack([X,-X]),np.r_[y,-y]);assert np.allclose(m[1].coef_,md['coefficients'],rtol=0,atol=1e-10)
for r in d['games']:
 x=np.array([[r['features'][f]for f in fs]]);p=float(m.predict(x)[0]);assert abs(p-r['raw_margin_home'])<1e-10;assert abs(p+float(m.predict(-x)[0]))<1e-10;assert r['display_margin_home']==round(p*2)/2
rs=json.load(open(P/'current_roster_manifest.json'));assert len(rs)==118 and all(r.get('season',{}).get('year')==2026 and r.get('player_count',0)>0 for r in rs);pg=pd.read_csv(P/'current_player_games.csv',dtype={'player_id':str});rmap={r['team']:set(r['player_ids'])for r in rs};unmatched=[]
for team,grp in pg.groupby('team'):
 if team not in rmap:continue
 for aid,a in grp.groupby('player_id'):
  if aid not in rmap[team]:unmatched.append(dict(team=team,player_id=aid,player_name=a.iloc[0].player_name,reason='seasonparticipantnotincurrentroster;notassumedhealthy/currentcontributor'))
(P/'roster_participation_gaps.json').write_text(json.dumps(unmatched,indent=2)+'\n')
# Original source and sealed files remain byte-for-byte in current repository.
R=pathlib.Path('/tmp/edith');seals=[]
for p in R.glob('tools/cfb/**/*sealed_research.sha256'):
 target=p.with_suffix('.json');assert hashlib.sha256(target.read_bytes()).hexdigest()==p.read_text().split()[0];seals.append(str(target))
res={'correctness_only_not_performance_validation':True,'training_unique_rows':len(tr),'forecast_rows':len(d['games']),'strict_date_provenance_rows':len(prov),'no_preseason_or_prior_stat_columns':True,'coefficient_rebuild_match':True,'all_future_side_swap':True,'original_seals_unchanged':len(seals),'current_rosters':len(rs),'roster_counts':dict(collections.Counter(r['player_count']for r in rs)),'season_participant_current_roster_gap_count':len(unmatched),'injury_adjustment_still_unavailable':True}
(P/'correctness_checks.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
