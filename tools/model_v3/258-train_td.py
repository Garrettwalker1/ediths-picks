#!/usr/bin/env python3
"""E.D.I.T.H. v3 anytime-TD model. Two stages, no market data anywhere:
stage 1: Poisson team offensive TD expectation from lagged team TDs + lagged opponent TDs allowed + home flag.
stage 2: within-team softmax allocation from lagged usage, RZ/GL share, TD rate, position.
Splits: train 2020-2023, validation 2024 (one pass selecting allocation L2 alpha), locked test 2025 REG.
Baselines: naive opportunity-share allocation of the same team lambda; position base rates from train.
"""
import numpy as np, pandas as pd, json
from pathlib import Path
from scipy.optimize import minimize
from sklearn.linear_model import PoissonRegressor, LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

OUT=Path('/tmp/training/out')
d=pd.read_parquet(OUT/'player_games_features.parquet')
rz=pd.read_parquet(OUT/'rzgl.parquet')
d=d.merge(rz,on=['game_id','player_id'],how='left')
for c in ['carry_rz','carry_gl','target_rz','target_gl']: d[c]=d[c].fillna(0)
d['tds']=d.rushing_tds.fillna(0)+d.receiving_tds.fillna(0)
d['y']=(d.tds>0).astype(int)
d=d[d.prior_games>=2].copy()

d=d.sort_values(['player_id','season','week']).copy(); g=d.groupby('player_id',group_keys=False)
for c in ['tds','carry_rz','carry_gl','target_rz','target_gl']:
    d[c+'_r6s']=g[c].transform(lambda x:x.shift().rolling(6,min_periods=2).sum())
d['opp_r6']=d.carries_r6+d.targets_r6  # per-game means from dataset builder
d['rz_r6']=d.carry_rz_r6s+d.target_rz_r6s; d['gl_r6']=d.carry_gl_r6s+d.target_gl_r6s
for c,new in [('targets_r6','target_sh'),('carries_r6','carry_sh'),('rz_r6','rz_share'),('gl_r6','gl_share')]:
    den=d.groupby(['season','week','game_id','team'])[c].transform('sum')
    d[new]=(d[c]/den.replace(0,np.nan)).fillna(0)
d['td_rate']=(d.tds_r6s/(d.prior_games+2)).fillna(0)
d['log_opp']=np.log1p(d.opp_r6.fillna(0))
for p in ('qb','rb','wr','te'): d['is_'+p]=(d.position==p.upper()).astype(int)

# team TD expectation features
team=d.groupby(['season','week','game_id','team','opponent_team','is_home'],as_index=False).agg(team_tds=('tds','sum'))
team=team.sort_values(['team','season','week'])
team['team_td_r6']=team.groupby('team').team_tds.transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
team=team.sort_values(['opponent_team','season','week'])
team['opp_td_allowed_r6']=team.groupby('opponent_team').team_tds.transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
team[['team_td_r6','opp_td_allowed_r6']]=team[['team_td_r6','opp_td_allowed_r6']].fillna(team[['team_td_r6','opp_td_allowed_r6']].median())
d=d.merge(team[['game_id','team','team_tds','team_td_r6','opp_td_allowed_r6']],on=['game_id','team'],how='left')

TFEATS=['team_td_r6','opp_td_allowed_r6','is_home']
tr_t=team[team.season<=2023].dropna(subset=TFEATS)
tsc=StandardScaler().fit(tr_t[TFEATS])
tm=PoissonRegressor(alpha=1.0,max_iter=1000).fit(tsc.transform(tr_t[TFEATS]),tr_t.team_tds)

ALLOC=['log_opp','rz_share','gl_share','target_sh','carry_sh','td_rate','is_qb','is_rb','is_te']
def fit_alloc(df,alpha):
    tr=df[df.season<=2023].dropna(subset=ALLOC).copy()
    sc=StandardScaler().fit(tr[ALLOC]); X=sc.transform(tr[ALLOC]); y=tr.tds.to_numpy(float)
    groups=pd.factorize(tr.game_id.astype(str)+'|'+tr.team)[0]
    idx=[np.where(groups==k)[0] for k in np.unique(groups)]
    def obj(w):
        val=.5*alpha*np.dot(w,w); grad=alpha*w; z=X@w
        for ii in idx:
            zz=z[ii]-z[ii].max(); pr=np.exp(zz); pr/=pr.sum(); n=y[ii].sum()
            if n: val-=np.dot(y[ii],np.log(np.clip(pr,1e-12,1))); grad+=X[ii].T@(n*pr-y[ii])
        return val,grad
    res=minimize(lambda w:obj(w),np.zeros(X.shape[1]),jac=True,method='L-BFGS-B',options={'maxiter':400})
    if not res.success: raise RuntimeError(str(res.message))
    return sc,res.x

def predict(df,afit):
    asc,w=afit; o=df.copy()
    o['team_lambda']=np.maximum(.01,tm.predict(tsc.transform(o[TFEATS].fillna(o[TFEATS].median()))))
    o['score']=asc.transform(o[ALLOC].fillna(0))@w; o['allocation']=0.0
    for _,ii in o.groupby(['game_id','team']).groups.items():
        ii=list(ii); z=o.loc[ii,'score'].to_numpy(); z-=z.max(); p=np.exp(z); o.loc[ii,'allocation']=p/p.sum()
    o['p_model']=1-np.exp(-o.team_lambda*o.allocation)
    raw=1+6*o.targets_r6.fillna(0)+6*o.carries_r6.fillna(0)+2*(o.target_rz_r6s.fillna(0)+o.carry_rz_r6s.fillna(0))+3*(o.target_gl_r6s.fillna(0)+o.carry_gl_r6s.fillna(0))
    den=raw.groupby([o.game_id,o.team]).transform('sum'); o['p_naive']=1-np.exp(-o.team_lambda*raw/den)
    rates=d[d.season<=2023].groupby('position').y.mean().to_dict()
    o['p_position']=o.position.map(rates).fillna(d[d.season<=2023].y.mean())
    return o

def metrics(y,p):
    p=np.clip(np.asarray(p),1e-8,1-1e-8); y=np.asarray(y)
    out={'n':int(len(y)),'events':int(y.sum()),'event_rate':float(y.mean()),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1])),'mean_probability':float(p.mean())}
    out['auc']=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None
    z=np.log(p/(1-p)).reshape(-1,1); cal=LogisticRegression(C=1e6,max_iter=1000).fit(z,y)
    out['calibration_intercept']=float(cal.intercept_[0]); out['calibration_slope']=float(cal.coef_[0,0])
    return out

def boot(x,reps=500):
    rng=np.random.default_rng(4242); games=x.game_id.unique(); vals=[]
    for _ in range(reps):
        pick=rng.choice(games,len(games),replace=True)
        b=pd.concat([x[x.game_id==g] for g in pick],ignore_index=True)
        y=b.y.to_numpy(); pm=np.clip(b.p_model.to_numpy(),1e-8,1-1e-8); pn=np.clip(b.p_naive.to_numpy(),1e-8,1-1e-8)
        vals.append((np.mean((y-pm)**2)-np.mean((y-pn)**2), np.mean(-(y*np.log(pm)+(1-y)*np.log(1-pm)))-np.mean(-(y*np.log(pn)+(1-y)*np.log(1-pn)))))
    a=np.asarray(vals)
    return {k:{'estimate':float(e),'ci95':[float(v) for v in q]} for k,e,q in [
        ('brier_delta_model_minus_naive',np.mean(a[:,0]),np.quantile(a[:,0],[.025,.975])),
        ('log_loss_delta_model_minus_naive',np.mean(a[:,1]),np.quantile(a[:,1],[.025,.975]))]}

grid=[]
for a in (.1,1.0,10.0):
    af=fit_alloc(d,a); p=predict(d,af); v=p[p.season==2024]
    grid.append((metrics(v.y,v.p_model)['log_loss'],a,af))
    print('alpha',a,'val logloss',round(grid[-1][0],5))
_,alpha,afit=min(grid,key=lambda x:x[0]); print('selected alpha',alpha)
p=predict(d,afit)
splits={'validation_2024':p[p.season==2024],'locked_test_2025':p[p.season==2025]}
res={'selected_alpha':alpha,'splits':{}}
for n,x in splits.items():
    res['splits'][n]={k:metrics(x.y,x[k]) for k in ['p_model','p_naive','p_position']}
res['locked_test_bootstrap']=boot(splits['locked_test_2025'])
(OUT/'td_results.json').write_text(json.dumps(res,indent=2))
te=res['splits']['locked_test_2025']
print(json.dumps({k:{m:round(v,5) if isinstance(v,float) else v for m,v in te[k].items()} for k in te},indent=1))
print(json.dumps(res['locked_test_bootstrap'],indent=1))
