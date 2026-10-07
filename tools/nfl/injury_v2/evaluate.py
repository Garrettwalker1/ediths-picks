#!/usr/bin/env python3
"""Fixed exploratory injury variants. 2025 is SEEN diagnostic, not a fresh holdout."""
import pathlib,sys,json,re,hashlib
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge,LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/model_nfl_v3_2/point_in_time'))
import elo_candidate as E,totals_candidate as T
norm=lambda s:re.sub('[^a-z]','',re.sub(r'\b(jr|sr|ii|iii|iv)\b','',str(s).lower()))
AL={'OAK':'LV','SD':'LAC','STL':'LA'}
def load_features(snap_frame=None, injury_frame=None):
 sc=snap_frame.copy() if snap_frame is not None else pd.concat([pd.read_csv(ROOT/f'tools/nflverse/{220+y-2020}-snap_counts_{y}.csv').assign(season=y) for y in range(2020,2026)],ignore_index=True)
 sc=sc[sc.game_type=='REG'].copy();sc['team']=sc.team.replace(AL);sc['name']=sc.player.map(norm)
 sc['share']=sc[['offense_pct','defense_pct']].max(axis=1)
 # Every weight is built from weeks strictly less than the scored injury report week.
 hist={(s,t,n):x.sort_values('week')[['week','share']] for (s,t,n),x in sc.groupby(['season','team','name'])}
 inj=injury_frame.copy() if injury_frame is not None else pd.concat([pd.read_csv(ROOT/f'tools/nflverse/{232+y-2020}-injuries_{y}.csv').assign(season=y) for y in range(2020,2026)],ignore_index=True)
 inj=inj[inj.game_type=='REG'].copy();inj['team']=inj.team.replace(AL);inj['name']=inj.full_name.map(norm)
 inj=inj.drop_duplicates(['season','week','team','name'],keep='last')
 pos=lambda p:'QB' if p=='QB' else 'SKILL' if p in ['RB','FB','WR','TE'] else 'OL' if p in ['C','G','T','OG','OT','OL'] else 'DEF' if p in ['DE','DT','NT','DL','LB','ILB','OLB','CB','DB','S','FS','SS'] else 'OTHER'
 data=[];missing=0
 for r in inj.itertuples():
  x=hist.get((r.season,r.team,r.name));a=x[x.week<r.week].tail(4).share if x is not None else pd.Series(dtype=float)
  # Prior-year share is only used for Week 1, not same-year first game as older code did.
  if a.empty:
   x=hist.get((r.season-1,r.team,r.name));a=x.tail(4).share if x is not None else pd.Series(dtype=float)
  weight=float(a.mean()) if len(a) else 0.0
  if not len(a):missing+=1
  data.append([r.season,r.week,r.team,pos(r.position),str(r.report_status),weight,str(r.practice_status)])
 z=pd.DataFrame(data,columns=['season','week','team','group','status','weight','practice'])
 out=[]
 for (s,w,t),xs in z.groupby(['season','week','team']):
  d={'season':s,'week':w,'team':t}
  for p in ['QB','SKILL','OL','DEF']:
   sub=xs[xs.group==p]
   d[p+'_absent']=sub.loc[sub.status.isin(['Out','Doubtful']),'weight'].sum()
   d[p+'_question']=sub.loc[sub.status=='Questionable','weight'].sum()
   d[p+'_practice']=sub.loc[sub.practice=='Did Not Participate In Practice','weight'].sum()
  out.append(d)
 return pd.DataFrame(out),{'injury_rows':len(z),'weights_missing':missing,'weight_missing_policy':'zero, explicit missing coverage; not treated as healthy evidence','limitations':['IR players absent from report are not captured','2025 data has no publication timestamp; historical status assumed final pregame and cannot reproduce Wednesday status','first-year players lack prior weight','2025 previously seen; no fresh holdout claim']}
def bootstrap(y,b,p):
 delta=np.abs(y-p)-np.abs(y-b);rng=np.random.default_rng(20261007)
 return {'delta_mae':float(delta.mean()),'ci95':np.percentile([delta[rng.integers(0,len(delta),len(delta))].mean() for _ in range(2000)],[2.5,97.5]).tolist()}
def main():
 iw,coverage=load_features();g=pd.read_csv(ROOT/'tools/nflverse/231-games_all.csv',low_memory=False)
 g=g[g.game_type.isin(['REG','WC','DIV','CON','SB'])].copy();g['elo']=g.game_id.map(E.diffs(g));g['margin']=g.home_score-g.away_score
 full=g[(g.season>=2010)&(g.season<=2025)&(g.game_type=='REG')].dropna(subset=['margin']);tr=full[full.season<=2022]
 mm=LinearRegression().fit(tr[['elo']],tr.margin);g['margin_base']=mm.predict(g[['elo']])
 gt=T.feats(g[g.game_type=='REG'].copy());tt=gt[(gt.season>=2010)&(gt.season<=2022)].dropna(subset=['total_pts']);tm=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tt[T.COLS],tt.total_pts);gt['total_base']=tm.predict(gt[T.COLS])
 for side in ['home','away']:
  feat=iw.rename(columns={k:side+'_'+k for k in iw if k not in ['season','week','team']}).rename(columns={'team':side+'_team'})
  gt=gt.merge(feat,on=['season','week',side+'_team'],how='left')
 for c in iw.columns:
  if c not in ['season','week','team']:
   for side in ['home','away']:gt[side+'_'+c]=gt[side+'_'+c].fillna(0)
   gt['diff_'+c]=gt['home_'+c]-gt['away_'+c];gt['sum_'+c]=gt['home_'+c]+gt['away_'+c]
 x=gt[(gt.season>=2020)&(gt.season<=2025)].dropna(subset=['margin','total_pts'])
 res={'protocol':'train residual weights 2020-22; select on 2023-24; 2025 SEEN diagnostic only','coverage':coverage,'variants':{},'n':x.groupby('season').size().to_dict(),'baseline_fit':{'margin_coef':mm.coef_[0],'margin_intercept':mm.intercept_}}
 selected={}
 for target,base,actual,prefix in [('margin','margin_base','margin','diff_'),('total','total_base','total_pts','sum_')]:
  results={};models={}
  for label,cols in [('qb',[prefix+'QB_absent',prefix+'QB_question']),('position_groups',[prefix+p+'_'+st for p in ['QB','SKILL','OL','DEF'] for st in ['absent','question']]),('practice_groups',[prefix+p+'_'+st for p in ['QB','SKILL','OL','DEF'] for st in ['absent','question','practice']])]:
   train=x[x.season<=2022];v=x[x.season.isin([2023,2024])];diag=x[x.season==2025]
   model=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(train[cols],train[actual]-train[base]);models[label]=(model,cols)
   offset=float((train[actual]-train[base]).mean())
   rr={}
   for split,z in [('selection_2023_24',v),('seen_2025',diag)]:
    y=z[actual].to_numpy();b=z[base].to_numpy();p=b+model.predict(z[cols]);rr[split]={'n':len(z),'baseline_mae':float(np.abs(y-b).mean()),'candidate_mae':float(np.abs(y-p).mean()),'same_window_intercept_baseline_mae':float(np.abs(y-(b+offset)).mean()),'incremental_vs_intercept_baseline':bootstrap(y,b+offset,p),**bootstrap(y,b,p)}
   rr['residual_intercept']=float(model.named_steps['ridge'].intercept_);rr['baseline_residual_intercept']=offset;rr['feature_mean']=model.named_steps['standardscaler'].mean_.tolist();rr['feature_scale']=model.named_steps['standardscaler'].scale_.tolist();rr['coefficients']=dict(zip(cols,model.named_steps['ridge'].coef_.tolist()));results[label]=rr
  best=min(results,key=lambda k:results[k]['selection_2023_24']['candidate_mae']);selected[target]=best;res['variants'][target]=results;res.setdefault('selected',{})[target]=best
 res['interval_caveat']='Game-level bootstrap is descriptive, not adjusted for model selection or shared-team/season dependence. No predictive significance claim.'
 res['deployment']='NOT DEPLOYED: historical tests are reused; need untouched forward validation and recoverable current injury/IR/role coverage'
 out=pathlib.Path(__file__).parent; (out/'results.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
if __name__=='__main__':main()
