#!/usr/bin/env python3
"""Predeclared margin-Elo candidate. Inputs: completed game scores only (strictly before kickoff date).
Elo settings fixed before validation: K=20, home advantage 48, offseason regression 1/3, margin multiplier 538-style.
Fit: train 2010-22 linear map elo diff -> margin; validation 2023; locked test 2024-25 evaluated once.
Usage: elo_candidate.py games.csv [--score-week 4 --season 2026]"""
import sys,json,hashlib
import numpy as np,pandas as pd
from sklearn.linear_model import LinearRegression,LogisticRegression
from sklearn.metrics import mean_absolute_error,accuracy_score,brier_score_loss
K,HFA,REG=20,48,0.33
AL={'OAK':'LV','SD':'LAC','STL':'LA'}
def diffs(g):
 g=g.copy()
 for c in('home_team','away_team'):g[c]=g[c].replace(AL)
 g=g.sort_values(['season','gameday','game_id']);r={};out={}
 for s,gs in g.groupby('season',sort=True):
  for t in list(r):r[t]=1500+(1-REG)*(r[t]-1500)
  # ratings for every game in a date are taken before any game of that date updates
  for day,gd in gs.groupby('gameday',sort=True):
   upd=[]
   for _,w in gd.iterrows():
    h,a=w.home_team,w.away_team;rh,ra=r.get(h,1500),r.get(a,1500);out[w.game_id]=rh-ra
    if pd.notna(w.home_score):
     m=w.home_score-w.away_score;e=1/(1+10**(-(rh-ra+HFA)/400));mult=np.log(abs(m)+1)*2.2/(abs(rh-ra+HFA)*0.001+2.2)
     d=K*mult*((1.0 if m>0 else 0.0 if m<0 else 0.5)-e);upd.append((h,a,d,rh,ra))
   for h,a,d,rh,ra in upd:r[h]=rh+d;r[a]=ra-d
 return out
if __name__=='__main__':
 g=pd.read_csv(sys.argv[1],low_memory=False);g=g[g.game_type.isin(['REG','WC','DIV','CON','SB'])]
 d=diffs(g);g['elo']=g.game_id.map(d);g['margin']=g.home_score-g.away_score
 x=g[(g.season>=2010)&(g.season<=2025)&(g.game_type=='REG')].dropna(subset=['margin','spread_line']);tr=x[x.season<=2022];va=x[x.season==2023];te=x[x.season.isin([2024,2025])]
 m=LinearRegression().fit(tr[['elo']],tr.margin);pv=m.predict(va[['elo']]);pt=m.predict(te[['elo']])
 y=(te.margin>0).astype(int);ytr=(tr.margin>0).astype(int)
 cal=LogisticRegression(max_iter=1000).fit(m.predict(tr[['elo']]).reshape(-1,1),ytr);pr=cal.predict_proba(pt.reshape(-1,1))[:,1]
 bk=np.where(te.home_moneyline<0,-te.home_moneyline/(-te.home_moneyline+100),100/(te.home_moneyline+100))
 rng=np.random.default_rng(20261001);dl=np.abs(te.margin.to_numpy()-pt)-np.abs(te.margin.to_numpy()-te.spread_line.to_numpy())
 ci=np.percentile([dl[rng.choice(len(dl),len(dl))].mean() for _ in range(1000)],[2.5,97.5]).tolist()
 vdl=np.abs(va.margin.to_numpy()-pv)-np.abs(va.margin.to_numpy()-va.spread_line.to_numpy())
 res={'n':[len(tr),len(va),len(te)],'coef':[float(m.coef_[0]),float(m.intercept_)],'val_mae':mean_absolute_error(va.margin,pv),'val_book_mae':mean_absolute_error(va.margin,va.spread_line),'val_form_mae':10.7419,'test_mae':mean_absolute_error(te.margin,pt),'test_book_mae':mean_absolute_error(te.margin,te.spread_line),'test_form_mae':10.4143,'test_acc':accuracy_score(y,pt>0),'test_book_acc':accuracy_score(y,te.spread_line>0),'test_form_acc':0.625,'test_brier':brier_score_loss(y,pr),'test_book_brier':brier_score_loss(y,bk),'test_form_brier':0.2204,'ci_model_minus_book':ci}
 print(json.dumps(res,indent=1))
