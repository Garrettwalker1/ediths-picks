#!/usr/bin/env python3
"""Week 5 NFL board: margin-Elo v1 + totals ridge, exactly the predeclared Week 4 settings (tools/model_nfl_v3_2/point_in_time).
Inputs: nflverse games.csv snapshot (completed scores only through Week 4; Week 5 rows have no scores). Book lines are never inputs.
Validation gate: refit coefficients must match the locked Week 4 fit (margin coef 0.038256/1.96382; train n 3359) or the script aborts.
Usage: build_week5.py games.csv out.json"""
import sys,json,pathlib
import numpy as np,pandas as pd
from sklearn.linear_model import LinearRegression,LogisticRegression,Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'model_nfl_v3_2/point_in_time'))
import elo_candidate as E,totals_candidate as T
g=pd.read_csv(sys.argv[1],low_memory=False);g=g[g.game_type.isin(['REG','WC','DIV','CON','SB'])]
# chronology guard: nothing scored at/after Week 5 may exist
assert g[(g.season==2026)&(g.week>=5)].home_score.isna().all()
d=E.diffs(g);g['elo']=g.game_id.map(d);g['margin']=g.home_score-g.away_score
x=g[(g.season>=2010)&(g.season<=2025)&(g.game_type=='REG')].dropna(subset=['margin','spread_line']);tr=x[x.season<=2022]
m=LinearRegression().fit(tr[['elo']],tr.margin)
assert len(tr)==3359 and abs(m.coef_[0]-0.03825649573945323)<1e-6 and abs(m.intercept_-1.9638223701043989)<1e-4,(len(tr),m.coef_,m.intercept_)
cal=LogisticRegression(max_iter=1000).fit(m.predict(tr[['elo']]).reshape(-1,1),(tr.margin>0).astype(int))
gt=T.feats(g[g.game_type=='REG'].copy())
xt=gt[(gt.season>=2010)&(gt.season<=2025)].dropna(subset=['total_pts','total_line']);ttr=xt[xt.season<=2022]
tm=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(ttr[T.COLS],ttr.total_pts)
w5=g[(g.season==2026)&(g.week==5)].copy();tw=gt[(gt.season==2026)&(gt.week==5)]
out=[]
for _,r in w5.sort_values(['gameday','gametime','game_id']).iterrows():
    mm=float(m.predict(pd.DataFrame({'elo':[r.elo]}))[0]);hw=float(cal.predict_proba(np.array([[mm]]))[0,1])
    t=tw[tw.game_id==r.game_id].iloc[0];tot=float(tm.predict(pd.DataFrame([t[T.COLS].to_dict()]))[0])
    out.append(dict(game_id=r.game_id,date=r.gameday,time_et=r.gametime,away=r.away_team,home=r.home_team,raw_margin_home=round(mm,2),home_win_prob=round(hw,3),elo_diff=round(float(r.elo),1),model_total=round(tot,1),home_score=round((tot+mm)/2),away_score=round((tot-mm)/2)))
json.dump(out,open(sys.argv[2],'w'),indent=1);print(len(out),'games');[print(o) for o in out]
