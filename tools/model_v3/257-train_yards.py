#!/usr/bin/env python3
"""E.D.I.T.H. v3 yards models: passing/rushing/receiving yards regression.
Splits: train 2020-2023, validation 2024, locked test 2025 REG. No book data.
Baselines: player r6 rolling mean of the target. Metrics: MAE/RMSE/R2 + paired game-cluster bootstrap CIs (model minus baseline; negative favors model).
"""
import numpy as np, pandas as pd, json
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

OUT=Path('/tmp/training/out')
d=pd.read_parquet(OUT/'player_games_features.parquet')
d=d[d.prior_games>=3].copy()

FORM=['passing_yards_r6','passing_tds_r6','attempts_r6','passing_epa_r6','passing_cpoe_r6','passing_interceptions_r6',
 'carries_r6','rushing_yards_r6','rushing_tds_r6','targets_r6','receptions_r6','receiving_yards_r6','receiving_tds_r6',
 'target_share_r6','air_yards_share_r6','wopr_r6','is_home']
QB=['qb_att_r6','qb_yards_r6','qb_tds_r6','qb_epa_per_att_r6','qb_int_r6']
DEF=['al_pass_yds_r6','al_rush_yds_r6','al_rec_yds_r6','al_ypa_r6','al_ypc_r6','al_ypt_r6','al_tds_r6']

def boot(df,pm,pb,target,reps=500):
    rng=np.random.default_rng(7); games=df.game_id.unique(); vals=[]
    y=df[target].to_numpy(float); pm=np.asarray(pm,float); pb=np.asarray(pb,float)
    idx_all=np.arange(len(df))
    gid=df.game_id.to_numpy()
    for _ in range(reps):
        pick=rng.choice(games,len(games),replace=True)
        mask=np.isin(gid,pick)
        vals.append(mean_absolute_error(y[mask],pm[mask])-mean_absolute_error(y[mask],pb[mask]))
    a=np.asarray(vals)
    return {'estimate':float(np.mean(a)),'ci95':[float(v) for v in np.quantile(a,[.025,.975])]}

QBFORM=['passing_yards_r6','passing_tds_r6','attempts_r6','passing_epa_r6','passing_cpoe_r6','passing_interceptions_r6']
RUSHFORM=['carries_r6','rushing_yards_r6','rushing_tds_r6','target_share_r6','wopr_r6']
RECFORM=['targets_r6','receptions_r6','receiving_yards_r6','receiving_tds_r6','target_share_r6','air_yards_share_r6','wopr_r6']
results={}
for target,positions,feats in [
    ('passing_yards',('QB',),QBFORM+QB+['al_pass_yds_r6','al_ypa_r6','al_pass_tds_r6','al_tds_r6','is_home']),
    ('rushing_yards',('QB','RB','WR','TE'),RUSHFORM+QB+['al_rush_yds_r6','al_ypc_r6','al_rush_tds_r6','al_tds_r6','is_home']),
    ('receiving_yards',('RB','WR','TE'),RECFORM+QB+['al_rec_yds_r6','al_ypt_r6','al_rec_tds_r6','al_tds_r6','is_home'])]:
    sub=d[d.position.isin(positions)].dropna(subset=feats+[target]).copy()
    tr=sub[sub.season<=2023]; va=sub[sub.season==2024]; te=sub[sub.season==2025]
    models={
      'ridge':make_pipeline(StandardScaler(),Ridge(alpha=10.0)),
      'hgb':HistGradientBoostingRegressor(max_depth=4,learning_rate=0.06,max_iter=300,l2_regularization=1.0,random_state=7)}
    rec={'n':{'train':len(tr),'validation':len(va),'locked_test':len(te)},'features':feats}
    base_te=te[f'{target}_r6'].to_numpy(); base_va=va[f'{target}_r6'].to_numpy()
    rec['baseline_r6']={'validation':{'mae':float(mean_absolute_error(va[target],base_va))},
                        'locked_test':{'mae':float(mean_absolute_error(te[target],base_te)),
                                       'rmse':float(mean_squared_error(te[target],base_te)**0.5),
                                       'r2':float(r2_score(te[target],base_te))}}
    best=None
    for name,m in models.items():
        m.fit(tr[feats],tr[target])
        pv=m.predict(va[feats]); pt=m.predict(te[feats])
        rec[name]={'validation':{'mae':float(mean_absolute_error(va[target],pv))},
                   'locked_test':{'mae':float(mean_absolute_error(te[target],pt)),
                                  'rmse':float(mean_squared_error(te[target],pt)**0.5),
                                  'r2':float(r2_score(te[target],pt))},
                   'mae_delta_vs_r6_baseline_bootstrap':boot(te,pt,base_te,target)}
        if best is None or rec[name]['validation']['mae']<best[1]: best=(name,rec[name]['validation']['mae'])
    rec['selected_on_validation']=best[0]
    results[target]=rec
    print(target, '->', best[0], json.dumps(rec[best[0]]['locked_test'],indent=None))


# Props-universe evaluation: only players with real market-relevant volume in the locked test
UNIV={'passing_yards':('attempts_r6',10.0),'rushing_yards':('carries_r6',3.0),'receiving_yards':('targets_r6',3.0)}
for target,positions,feats in [
    ('passing_yards',('QB',),QBFORM+QB+['al_pass_yds_r6','al_ypa_r6','al_pass_tds_r6','al_tds_r6','is_home']),
    ('rushing_yards',('QB','RB','WR','TE'),RUSHFORM+QB+['al_rush_yds_r6','al_ypc_r6','al_rush_tds_r6','al_tds_r6','is_home']),
    ('receiving_yards',('RB','WR','TE'),RECFORM+QB+['al_rec_yds_r6','al_ypt_r6','al_rec_tds_r6','al_tds_r6','is_home'])]:
    col,thr=UNIV[target]
    sub=d[d.position.isin(positions)].dropna(subset=feats+[target]).copy()
    tr=sub[sub.season<=2023]; te=sub[sub.season==2025]
    sel=results[target]['selected_on_validation']
    m={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=10.0)),
       'hgb':HistGradientBoostingRegressor(max_depth=4,learning_rate=0.06,max_iter=300,l2_regularization=1.0,random_state=7)}[sel]
    m.fit(tr[feats],tr[target])
    u=te[te[col]>=thr]
    pt=m.predict(u[feats]); pb=u[f'{target}_r6'].to_numpy()
    results[target]['props_universe']={'filter':f'{col}>={thr}','n_locked_test':int(len(u)),
      'baseline_r6_mae':float(mean_absolute_error(u[target],pb)),
      'model_mae':float(mean_absolute_error(u[target],pt)),
      'mae_delta_vs_r6_baseline_bootstrap':boot(u,pt,pb,target)}
    print(target,'props-universe n=',len(u),'model',round(results[target]['props_universe']['model_mae'],2),'base',round(results[target]['props_universe']['baseline_r6_mae'],2))

(OUT/'yards_results.json').write_text(json.dumps(results,indent=2))
print('saved yards_results.json')
