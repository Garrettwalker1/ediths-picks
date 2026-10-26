import pathlib,sys,json,datetime
import numpy as np,pandas as pd
from sklearn.linear_model import LinearRegression,Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
P=pathlib.Path(__file__).resolve().parent;R=P.parents[3]
sys.path.insert(0,str(R/'tools/model_nfl_v3_2/point_in_time'));import elo_candidate as E,totals_candidate as T
sys.path.insert(0,str(R/'tools/nfl/injury_v2'));from evaluate import load_features
frames=[]
for year in range(2020,2027):
 f=R/f'tools/player_projection_cache/stats_{year}.csv' if year>=2023 else R/f'tools/nflverse/{226+year-2020}-player_stats_{year}.csv'
 d=pd.read_csv(f,low_memory=False);d=d[d.position=='QB'].copy();d['team']=d.get('team',d.get('recent_team'));d['sacks']=d.get('sacks_suffered',d.get('sacks'));d=d[d.season_type=='REG'];d['opps']=d.attempts.fillna(0)+d.sacks.fillna(0)+d.carries.fillna(0);d['epa']=d.passing_epa.fillna(0)+d.rushing_epa.fillna(0);frames.append(d)
stats=pd.concat(frames,ignore_index=True);stats['team']=stats.team.replace({'OAK':'LV','SD':'LAC','STL':'LA','LAR':'LA','WAS':'WSH'})
g=pd.read_csv(R/'tools/nfl/week7_2026/games_nflverse_20261020.csv',low_memory=False);g=g[g.game_type.isin(['REG','WC','DIV','CON','SB'])].copy();g['elo']=g.game_id.map(E.diffs(g));g['margin']=g.home_score-g.away_score
tr=g[(g.season>=2010)&(g.season<=2022)&(g.game_type=='REG')].dropna(subset=['margin'])
mm=LinearRegression().fit(tr[['elo']],tr.margin);g['mb']=mm.predict(g[['elo']]);g=T.feats(g[g.game_type=='REG'].copy());tr=g[(g.season>=2010)&(g.season<=2022)].dropna(subset=['total_pts']);tm=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[T.COLS],tr.total_pts);g['tb']=tm.predict(g[T.COLS])
statmap={(int(s),int(w),t):x for (s,w,t),x in stats.groupby(['season','week','team'])};qstate={};tstate={};features=[];qw=.5**(1/12);tw=.5**(1/6)
for r in g.sort_values(['gameday','game_id']).itertuples():
 z={};updates=[]
 for side in ['home','away']:
  team=getattr(r,side+'_team');pid=getattr(r,side+'_qb_id');qs=qstate.get(pid,[0.,0.]);ts=tstate.get(team,[0.,0.]);rate=qs[0]/(qs[1]+100);recent=ts[0]/(ts[1]+100);z[side+'_qb_context']=rate-recent;z[side+'_qb_skill']=rate;z[side+'_team_qb_rate']=recent;z[side+'_prior_opps']=qs[1]
  x=statmap.get((int(r.season),int(r.week),team))
  if x is not None and pd.notna(r.home_score):updates.append((team,x))
 features.append(dict(game_id=r.game_id,**z))
 for team,x in updates:
  ep=float(x.epa.sum());opp=float(x.opps.sum());old=tstate.get(team,[0.,0.]);tstate[team]=[old[0]*tw+ep,old[1]*tw+opp]
  for a in x.itertuples():
   old=qstate.get(a.player_id,[0.,0.]);qstate[a.player_id]=[old[0]*qw+a.epa,old[1]*qw+a.opps]
g=g.merge(pd.DataFrame(features),on='game_id');iw,cov=load_features();cols=[x for x in iw.columns if x not in ['season','week','team'] and not x.startswith('QB')]
for side in ['home','away']:
 z=iw[['season','week','team']+cols].rename(columns={'team':side+'_team',**{x:side+'_'+x for x in cols}});g=g.merge(z,on=['season','week',side+'_team'],how='left')
for c in cols+['qb_context']:
 for side in ['home','away']:g[side+'_'+c]=g[side+'_'+c].fillna(0)
 g['diff_'+c]=g['home_'+c]-g['away_'+c];g['sum_'+c]=g['home_'+c]+g['away_'+c]
# Current non-QB inputs: current immutable inventory, explicit roster/news corrections, no guessed QB point value.
inv=json.load(open(R/'injury_adjustments.json'))['inventory'];teamfeat={}
for a in inv:
 if a['team'] not in ['DAL','PHI'] or a['position_group'] not in ['SKILL','OL','DEF']:continue
 # Match report-only historical training: long-term IR inventory is not a game-report feature.
 if a['status']=='IR':continue
 f=teamfeat.setdefault(a['team'],{});w=a.get('snap_weight') or 0;gr=a['position_group'];st=a['status'];practice=a['practice']
 if a['player'] in ['Dallas Goedert','Saquon Barkley','Marquise Brown']:practice='Full Participation in Practice'
 if a['player'] in ['DeVonta Smith','Dontayvion Wicks','Nolan Smith','Michael Carter II','KaVontae Turpin','Dee Winters','Drew Shelton']:st='Out'
 if a['player'] in ['Saquon Barkley','Jalyx Hunt','Jonathan Greenard']:st='Active' # Official Eagles inactives Oct26 6:45PM ET; practice flags preserved
 for typ,flag in [('absent',st in ['IR','Out','Doubtful']),('question',st=='Questionable'),('practice',practice=='Did Not Participate In Practice')]:f[gr+'_'+typ]=f.get(gr+'_'+typ,0)+w*flag
cur=g[g.game_id=='2026_07_DAL_PHI'].iloc[0].copy()
# Set externally verified starter explicitly, using strictly prior-game stats.
ps=stats[stats.player_display_name.str.contains('Tanner McKee',case=False,na=False)];pid=ps.player_id.iloc[-1];qs=qstate.get(pid,[0.,0.]);ts=tstate.get('PHI',[0.,0.]);cur['home_qb_context']=qs[0]/(qs[1]+100)-ts[0]/(ts[1]+100);cur['home_qb_skill']=qs[0]/(qs[1]+100);cur['home_prior_opps']=qs[1];cur['home_team_qb_rate']=ts[0]/(ts[1]+100)
for c in cols:
 cur['home_'+c]=teamfeat.get('PHI',{}).get(c,0);cur['away_'+c]=teamfeat.get('DAL',{}).get(c,0)
for c in cols+['qb_context']:cur['diff_'+c]=cur['home_'+c]-cur['away_'+c];cur['sum_'+c]=cur['home_'+c]+cur['away_'+c]
out={'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol':(P/'QB_PLAN.md').read_text(),'coverage':cov,'starter':'Tanner McKee','starter_id':pid,'current_qb_context':{c:float(cur[c]) for c in ['home_qb_context','away_qb_context','home_qb_skill','home_team_qb_rate','home_prior_opps']},'targets':{},'current_nonqb_features':teamfeat,'current_input_policy':'Saturday/Monday official report designations override stale provider No game designation. Long-term IR excluded to match report-only historical coverage; missing long-term IR effects are not silently modeled.'}
for target,base,prefix in [('margin','mb','diff_'),('total','tb','sum_')]:
 cc=[prefix+c for c in ['qb_context']+cols];train=g[g.season.between(2020,2022)].dropna(subset=[target if target=='margin' else 'total_pts']);actual='margin' if target=='margin' else 'total_pts'
 model=make_pipeline(StandardScaler(with_mean=False),Ridge(alpha=10,fit_intercept=False)).fit(train[cc],train[actual]-train[base]);delta=float(model.predict(pd.DataFrame([cur])[cc])[0]);r={'delta':delta,'baseline':float(cur[base]),'prediction':float(cur[base]+delta),'diagnostics':{},'coefficients':dict(zip(cc,(model[-1].coef_/model[0].scale_).tolist()))}
 for label,years in [('2023_24',[2023,2024]),('2025_seen',[2025])]:
  x=g[g.season.isin(years)].dropna(subset=[actual]);bp=x[base].to_numpy();pred=bp+model.predict(x[cc]);yy=x[actual].to_numpy();dd=abs(yy-pred)-abs(yy-bp);rng=np.random.default_rng(20261026);ci=np.percentile([rng.choice(dd,len(dd)).mean() for _ in range(1000)],[2.5,97.5]).tolist();r['diagnostics'][label]={'n':len(x),'baseline_mae':float(abs(yy-bp).mean()),'new_mae':float(abs(yy-pred).mean()),'delta_mae':float(dd.mean()),'ci95':ci}
 out['targets'][target]=r
(P/'qb_context_result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
