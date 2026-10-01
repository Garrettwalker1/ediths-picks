#!/usr/bin/env python3
"""Predeclared NFL totals candidate. Features use only completed prior games (day-lagged): each team's exponentially
weighted points for/against (halflife 6 games, carried across seasons with 1/3 regression to league mean at season start),
plus dome flag. Fit ridge(alpha=10) on 2010-22 REG; validation 2023; locked test 2024-25 evaluated once.
Compared with: train-mean baseline and closing total (benchmark only, never an input)."""
import sys,json
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
AL={'OAK':'LV','SD':'LAC','STL':'LA'};HL=6;REG=1/3
def feats(g):
    g=g.copy()
    for c in('home_team','away_team'):g[c]=g[c].replace(AL)
    g=g.sort_values(['season','gameday','game_id']).reset_index(drop=True)
    st={};lg=22.5;out=[]
    for s,gs in g.groupby('season',sort=True):
        for t in st:st[t]['pf']=lg*REG+(1-REG)*st[t]['pf'];st[t]['pa']=lg*REG+(1-REG)*st[t]['pa']
        for day,gd in gs.groupby('gameday',sort=True):
            upd=[]
            for i,r in gd.iterrows():
                h=st.setdefault(r.home_team,{'pf':lg,'pa':lg,'n':0});a=st.setdefault(r.away_team,{'pf':lg,'pa':lg,'n':0})
                out.append((i,h['pf'],h['pa'],a['pf'],a['pa']))
                if pd.notna(r.home_score):upd.append((r.home_team,r.away_team,r.home_score,r.away_score))
            w=1-0.5**(1/HL)
            for h,a,hs,as_ in upd:
                st[h]['pf']+=w*(hs-st[h]['pf']);st[h]['pa']+=w*(as_-st[h]['pa']);st[a]['pf']+=w*(as_-st[a]['pf']);st[a]['pa']+=w*(hs-st[a]['pa'])
    f=pd.DataFrame(out,columns=['i','hpf','hpa','apf','apa']).set_index('i');g=g.join(f)
    g['dome']=g.roof.isin(['dome','closed']).astype(float);g['total_pts']=g.home_score+g.away_score
    g['x_sum']=g.hpf+g.apa+g.apf+g.hpa  # offence+defence blend
    return g
COLS=['hpf','hpa','apf','apa','dome']
if __name__=='__main__':
    g=pd.read_csv(sys.argv[1],low_memory=False);g=g[g.game_type=='REG'];g=feats(g)
    x=g[(g.season>=2010)&(g.season<=2025)].dropna(subset=['total_pts','total_line']);tr=x[x.season<=2022];va=x[x.season==2023];te=x[x.season.isin([2024,2025])]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[COLS],tr.total_pts);pv=m.predict(va[COLS]);pt=m.predict(te[COLS])
    mae=lambda y,p:float(np.abs(y-p).mean())
    base=tr.total_pts.mean()
    rng=np.random.default_rng(20261001);dl=np.abs(te.total_pts.to_numpy()-pt)-np.abs(te.total_pts.to_numpy()-te.total_line.to_numpy())
    ci=np.percentile([dl[rng.choice(len(dl),len(dl))].mean() for _ in range(1000)],[2.5,97.5]).tolist()
    res={'n':[len(tr),len(va),len(te)],'val_mae':mae(va.total_pts,pv),'val_baseline_mae':mae(va.total_pts,base),'val_book_mae':mae(va.total_pts,va.total_line),'test_mae':mae(te.total_pts,pt),'test_baseline_mae':mae(te.total_pts,base),'test_book_mae':mae(te.total_pts,te.total_line),'ci_model_minus_book':ci,'train_mean':float(base)}
    print(json.dumps(res,indent=1))
