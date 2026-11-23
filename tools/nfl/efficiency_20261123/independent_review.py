import pandas as pd,numpy as np,json,pathlib
P=pathlib.Path(__file__).parent;d=pd.read_parquet(P/'pbp2026.parquet');a=d[d.play_type.isin(['pass','run']) & ~d.qb_kneel.eq(1)& ~d.qb_spike.eq(1)& ~d.two_point_attempt.eq(1)].copy();a['dist_success']=(a.yards_gained>=a.ydstogo*a.down.map({1:.5,2:.7,3:1.,4:1.})).astype(float);teams=sorted(a.posteam.unique());idx={x:i for i,x in enumerate(teams)};checks=[]
for prefix,subset in [('',a),('pass_',a[a.play_type=='pass']),('rush_',a[a.play_type=='run'])]:
 for metric,col in [('success','dist_success'),('epa','epa')]:
  # Independent play-level design, equivalent team-game weighting without any group aggregation.
  n=len(subset);X=np.zeros((n,66));X[:,0]=1;X[:,1]=(subset.posteam==subset.home_team).astype(float);X[np.arange(n),[2+idx[x]for x in subset.posteam]]=1;X[np.arange(n),[34+idx[x]for x in subset.defteam]]=1
  penalty=np.diag([0,0]+[20]*64);b=np.linalg.solve(X.T@X+penalty,X.T@subset[col].to_numpy());name=prefix+metric
  for side,key,higher in [('offense','posteam',True),('defense','defteam',False)]:
   csv=pd.read_csv(P/('nfl_2026_'+side+'.csv')).set_index('team');expected={t:b[0]+b[(2 if side=='offense'else 34)+idx[t]]for t in teams};rank={t:i+1 for i,t in enumerate(sorted(teams,key=lambda t:expected[t],reverse=higher))}
   for t in teams:
    assert abs(csv.loc[t,name+'_adj']-expected[t])<.00000051
    assert abs(csv.loc[t,name+'_raw']-subset[subset[key]==t][col].mean())<.00000051
    assert csv.loc[t,name+'_rank']==rank[t]
   checks.append({'metric':name,'side':side,'rates_ranks_checked':32,'denominators':{t:int((subset[key]==t).sum())for t in teams}})
result={'checks':checks,'total_rates_and_ranks':384,'independent_method':'Play-level design and pandas raw means, no builder team-game aggregation','source_sha256':__import__('hashlib').sha256((P/'pbp2026.parquet').read_bytes()).hexdigest()};(P/'independent_review.json').write_text(json.dumps(result,indent=2));print('PASS384rates/ranksreproduced, EPA/distance-success/pass/rush/bothsides; independent denominators saved')
