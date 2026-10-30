from pathlib import Path
import pandas as pd,numpy as np,json,datetime
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error,mean_squared_error
R=Path('/tmp/edith-oct28');P=Path('/tmp/prop-matchup');frames=[]
for y in range(2021,2026):
 p=Path('/tmp/td-matchup/cache')/f'stats_{y}.csv'
 if not p.exists():p=R/'tools/player_projection_cache'/f'stats_{y}.csv'
 d=pd.read_csv(p,low_memory=False);frames.append(d[d.season_type.eq('REG')])
d=pd.concat(frames,ignore_index=True).sort_values(['player_id','season','week']);allcols=['receiving_yards','targets','receptions','receiving_air_yards','target_share','air_yards_share','wopr','rushing_yards','carries','receiving_tds','rushing_tds','fantasy_points_ppr']
for c in allcols:
 for n in (3,6):d[f'{c}_r{n}']=d.groupby('player_id')[c].transform(lambda x:x.shift().rolling(n,min_periods=3).mean())
# Current-team/current-season recent production, avoids carrying return/change-team usage as if unchanged.
for c in ['receiving_yards','rushing_yards','receptions','receiving_air_yards']:
 d[c+'_current4']=d.groupby(['player_id','season','team'])[c].transform(lambda x:x.shift().rolling(4,min_periods=2).mean())
z=pd.read_pickle('/tmp/td-matchup/out/dataset.pkl');z=z.merge(d,on=['player_id','game_id','season','week','team'],how='left',validate='one_to_one',suffixes=('','_source'))
new=json.load(open(R/'tools/nfl/td_matchup_20261029/diagnostics.json'))['features'];new=[x for x in new if x!='baseline_logit']+['receiving_yards_current4','rushing_yards_current4','receptions_current4','receiving_air_yards_current4']
old={'receiving_yards':['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receptions_r3','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3'],'rushing_yards':['rushing_yards_r3','rushing_yards_r6','carries_r3','carries_r6'],'receptions':['receptions_r3','targets_r3','targets_r6']}
res={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Skill-player props only; same prior-history eligibility as TDtrial, conditional played-player not expected-availability model. No QBpassingtested.','split':'Train2021-23; selectRidgealpha2024MAE;2025SEENdiagnostic, not newholdout.','comparators':'old_formula refitted only2021-23 (not deployed2024-25fit), current4mean, usage_matchup candidate with TDfeaturefamily but stat-specific target. No future outcomes in features.','features':new,'targets':{}}
for target in old:
 a=z[z.position.isin(['RB','WR','TE'])].dropna(subset=list(set(new+old[target]+[target]))).copy()
 if target=='rushing_yards':a=a[a.position.eq('RB')]
 out={'n':len(a),'models':{}}
 for name,fs in [('old_formula',old[target]),('usage_matchup',old[target]+new)]:
  tr=a.season.le(2023);va=a.season.eq(2024);te=a.season.eq(2025);cands=[]
  for alpha in [1,10,100]:
   m=make_pipeline(StandardScaler(),Ridge(alpha=alpha)).fit(a.loc[tr,fs],a.loc[tr,target]);p=np.maximum(0,m.predict(a.loc[va,fs]));cands.append((mean_absolute_error(a.loc[va,target],p),alpha,m))
  _,alpha,m=min(cands,key=lambda x:x[0]);rr={'alpha':alpha}
  for label,mask in [('validation2024',va),('seen2025',te)]:
   p=np.maximum(0,m.predict(a.loc[mask,fs]));y=a.loc[mask,target];rr[label]={'n':int(mask.sum()),'MAE':mean_absolute_error(y,p),'RMSE':float(np.sqrt(mean_squared_error(y,p)))};a.loc[mask,name]=p
  out['models'][name]=rr
 a.to_pickle(P/'out'/f'{target}_paired.pkl');res['targets'][target]=out
 print(target,out,flush=True)
(P/'out/diagnostics.json').write_text(json.dumps(res,indent=2)+'\n')
