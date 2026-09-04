#!/usr/bin/env python3
"""E.D.I.T.H. CFB game-line model v1 - SEPARATE from the NFL model.
Predicts FBS game margin (home perspective) and total points from the ESPN corpus.
Features: shifted prior-season ratings + current-season rolling (r4) team offense/defense/QB-play.
No book/market data anywhere. Splits: train 2020-2023, validation 2024, locked test 2025.
Baselines: (1) home +2.5 / league-average total; (2) rolling points-differential.
"""
import numpy as np, pandas as pd, json
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

ESPN=Path('/tmp/ediths-picks/tools/espn'); OUT=Path('/tmp/training/cfb/out'); OUT.mkdir(parents=True,exist_ok=True)
SEASONS=(2020,2021,2022,2023,2024,2025)

games=pd.concat([pd.read_csv(p) for p in ESPN.glob('games/*cfb_*_games.csv')],ignore_index=True)
games=games[games.completed==True].copy()
games['margin']=games.home_score-games.away_score
games['total']=games.home_score+games.away_score
games['date']=pd.to_datetime(games.date)

# --- team-game table from defense extracts: team defense + inferred offense ---
td=pd.concat([pd.read_csv(p) for p in ESPN.glob('team_defense/*cfb_*.csv')],ignore_index=True)
td['date']=pd.to_datetime(td.date)
# offense = opponent's allowed line
off=td[['event_id','season','team','opponent','points_allowed','pass_yds_allowed','rush_yds_allowed','total_yds_allowed']].rename(
    columns={'team':'opponent','opponent':'team','points_allowed':'points_for','pass_yds_allowed':'pass_yds_for','rush_yds_allowed':'rush_yds_for','total_yds_allowed':'total_yds_for'})
tg=td.merge(off,on=['event_id','season','team','opponent'],how='left')

# QB play per team-game from player_games
pg=pd.concat([pd.read_csv(p) for p in ESPN.glob('player_games/*cfb_*.csv')],ignore_index=True)
qb=pg[pg.pass_att.fillna(0)>0].groupby(['event_id','team'],as_index=False).agg(
    qb_att=('pass_att','sum'),qb_cmp=('pass_cmp','sum'),qb_yds=('pass_yds','sum'),qb_td=('pass_td','sum'),qb_int=('pass_int','sum'))
qb['qb_cmp_pct']=qb.qb_cmp/qb.qb_att.replace(0,np.nan)
tg=tg.merge(qb[['event_id','team','qb_cmp_pct','qb_yds','qb_td','qb_int']],on=['event_id','team'],how='left')
tg=tg.sort_values(['team','season','date']).reset_index(drop=True)
print('team-games',len(tg))

# prior-season team ratings (full-season means)
prior=tg.groupby(['team','season'],as_index=False).agg(
    ps_pf=('points_for','mean'),ps_pa=('points_allowed','mean'),ps_yf=('total_yds_for','mean'),ps_ya=('total_yds_allowed','mean'))
prior['season']+=1
prior=prior.rename(columns={c:'prior_'+c.split('_',1)[1] for c in ['ps_pf','ps_pa','ps_yf','ps_ya']})
tg=tg.merge(prior,on=['team','season'],how='left')
lg=tg.groupby('season')[['points_for','points_allowed','total_yds_for','total_yds_allowed']].mean()
for c,src in [('prior_pf','points_for'),('prior_pa','points_allowed'),('prior_yf','total_yds_for'),('prior_ya','total_yds_allowed')]:
    tg[c]=tg[c].fillna(tg.season.map(lg[src]))

# current-season shifted rolling r4
g=tg.groupby(['team','season'],group_keys=False)
for c,new in [('points_for','pf'),('points_allowed','pa'),('total_yds_for','yf'),('total_yds_allowed','ya'),
              ('pass_yds_for','pyf'),('pass_yds_allowed','pya'),('rush_yds_for','ryf'),('rush_yds_allowed','rya'),
              ('turnovers_forced','tof'),('qb_cmp_pct','qbc'),('qb_yds','qby'),('qb_td','qbtd'),('qb_int','qbi')]:
    tg[new+'_r4']=g[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
tg['gp']=g['date'].transform(lambda x:x.shift().rolling(100,min_periods=1).count()).fillna(0)
# blend: early season leans on prior, later on rolling (weight = gp/(gp+2))
w=(tg.gp/(tg.gp+2)).clip(0,1)
for b,cols in [('pf',('prior_pf','pf_r4')),('pa',('prior_pa','pa_r4')),('yf',('prior_yf','yf_r4')),('ya',('prior_ya','ya_r4'))]:
    tg[b+'_f']=w*tg[cols[1]].fillna(tg[cols[0]])+(1-w)*tg[cols[0]]

# game-level assembly (home perspective)
h=tg[tg.home_away=='home'].set_index('event_id'); a=tg[tg.home_away=='away'].set_index('event_id')
gm=games.set_index('event_id').join(h[['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','gp']].add_prefix('h_'),how='inner')
gm=gm.join(a[['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','gp']].add_prefix('a_'),how='inner')
gm=gm.reset_index()
print('games assembled',len(gm), gm.groupby('season').size().to_dict())

FEATS=[]
for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; FEATS.append('d_'+s)
gm['d_gp']=gm.h_gp-gm.a_gp; FEATS.append('d_gp')

def boot(df,pm,pb,target,reps=500):
    rng=np.random.default_rng(11); ev=df.event_id.unique(); vals=[]
    y=df[target].to_numpy(float); eid=df.event_id.to_numpy()
    for _ in range(reps):
        pick=rng.choice(ev,len(ev),replace=True); mask=np.isin(eid,pick)
        vals.append(mean_absolute_error(y[mask],pm[mask])-mean_absolute_error(y[mask],pb[mask]))
    a=np.asarray(vals); return {'estimate':float(np.mean(a)),'ci95':[float(v) for v in np.quantile(a,[.025,.975])]}

res={}
for target in ['margin','total']:
    sub=gm.dropna(subset=FEATS+[target]).copy()
    tr=sub[sub.season<=2023]; va=sub[sub.season==2024]; te=sub[sub.season==2025]
    models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=10.0)),
            'hgb':HistGradientBoostingRegressor(max_depth=3,learning_rate=0.06,max_iter=300,l2_regularization=1.0,random_state=7)}
    rec={'n':{'train':len(tr),'validation':len(va),'locked_test':len(te)}}
    if target=='margin':
        b_va=np.full(len(va),2.5); b_te=np.full(len(te),2.5)
        b2_va=(va.d_pf_f-va.d_pa_f)+2.5; b2_te=(te.d_pf_f-te.d_pa_f)+2.5
    else:
        lgmean=tr[target].mean(); b_va=np.full(len(va),lgmean); b_te=np.full(len(te),lgmean)
        b2_va=va.h_pf_f+va.a_pf_f; b2_te=te.h_pf_f+te.a_pf_f
    rec['baseline_const']={'validation_mae':float(mean_absolute_error(va[target],b_va)),'test_mae':float(mean_absolute_error(te[target],b_te))}
    rec['baseline_rolling']={'validation_mae':float(mean_absolute_error(va[target],b2_va)),'test_mae':float(mean_absolute_error(te[target],b2_te))}
    best=None
    for name,m in models.items():
        m.fit(tr[FEATS],tr[target]); pv=m.predict(va[FEATS]); pt=m.predict(te[FEATS])
        rec[name]={'validation_mae':float(mean_absolute_error(va[target],pv)),
                   'test_mae':float(mean_absolute_error(te[target],pt)),
                   'test_rmse':float(mean_squared_error(te[target],pt)**0.5),
                   'delta_vs_const':boot(te,pt,b_te,target),'delta_vs_rolling':boot(te,pt,b2_te,target)}
        if best is None or rec[name]['validation_mae']<best[1]: best=(name,rec[name]['validation_mae'])
    rec['selected_on_validation']=best[0]
    if target=='margin':
        m=models[best[0]]; pt=m.predict(te[FEATS])
        rec['winner_accuracy']={'model':float((np.sign(pt)==np.sign(te.margin)).mean()),
                                'baseline_home_win':float((te.margin>0).mean())}
    res[target]=rec
    print(target,best[0],json.dumps({k:round(v,3) if isinstance(v,float) else v for k,v in rec[best[0]].items() if k in ('validation_mae','test_mae','test_rmse')}))

(OUT/'cfb_gameline_results.json').write_text(json.dumps(res,indent=2))
gm.to_parquet(OUT/'cfb_games_features.parquet')
print('saved')
