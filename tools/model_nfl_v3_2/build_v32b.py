#!/usr/bin/env python3
"""NFL v3.2 iteration 2 (Garrett-approved 9/14): snap-weighted injury impact,
weather/turf, week-18 resting handling. Selection on val 2023; locked test 2024-25."""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error

D=Path('/tmp/training/nflv32')
gm=pd.read_parquet(D/'out/v32_games.parquet')
games=pd.read_csv(D/'games.csv')
games=games[(games.season>=2010)&(games.season<=2025)&(games.game_type=='REG')].copy()

# ---- snap-weighted injury impact ----
sc=pd.concat([pd.read_csv(f'/tmp/ediths-picks/tools/nflverse/22{i}-snap_counts_202{i}.csv') for i in range(0,6)],ignore_index=True)
sc=sc[sc.game_type=='REG'].copy()
sc['snap_pct']=sc[['offense_pct','defense_pct']].max(axis=1)
sc['key']=sc.player.str.lower().str.replace(r'[^a-z]','',regex=True)+'|'+sc.team+'|'+sc.season.astype(str)
# season-to-date snap share through PRIOR week
sc=sc.sort_values(['key','week'])
sc['snap_std']=sc.groupby('key')['snap_pct'].transform(lambda x:x.shift().expanding().mean())
wk1=sc.groupby('key')['snap_pct'].transform('first')  # week1 has no prior; use season avg proxy
sc['snap_std']=sc['snap_std'].fillna(wk1)
snap_map=sc.set_index(['key','week'])['snap_std'].to_dict()
inj=pd.concat([pd.read_parquet(D/f'inj_{y}.parquet').assign(season=y) for y in range(2010,2026)],ignore_index=True)
inj['out_pts']=inj.report_status.map({'Out':1.0,'Doubtful':0.75,'Questionable':0.25}).fillna(0.0)
inj['key']=inj.full_name.str.lower().str.replace(r'[^a-z]','',regex=True)+'|'+inj.team+'|'+inj.season.astype(str)
inj['snap']= [snap_map.get((k,w)) for k,w in zip(inj.key,inj.week)]
inj['snap']=inj['snap'].fillna(0.30)  # unlisted -> rotational proxy
inj['impact']=inj.out_pts*inj.snap
iw=inj.groupby(['season','week','team'],as_index=False).agg(inj_impact=('impact','sum'))
# pre-2020 has no snaps: scale raw points by 0.55 avg-starter proxy
raw=inj.groupby(['season','week','team'],as_index=False).agg(inj_pts=('out_pts','sum'))
iw=iw.merge(raw,on=['season','week','team'])
iw.loc[iw.season<2020,'inj_impact']=iw.loc[iw.season<2020,'inj_pts']*0.55
tgw=iw[['season','week','team','inj_impact']]
h=games[['game_id','season','week','home_team']].rename(columns={'home_team':'team'})
a=games[['game_id','season','week','away_team']].rename(columns={'away_team':'team'})
tg=pd.concat([h,a]).merge(tgw,on=['season','week','team'],how='left').fillna({'inj_impact':0.0})
gm=gm.merge(tg[['game_id','team','inj_impact']].pivot(index='game_id',columns='team',values='inj_impact').rename(columns=lambda t:f'imp_{t}'),left_on='game_id',right_index=True,how='left')
gm['d_inj_impact']=gm.apply(lambda r: r.get('imp_'+r.home_team,0)-r.get('imp_'+r.away_team,0),axis=1)

# ---- weather/turf ----
w=games.set_index('game_id')
gm['dome']=w.roof.isin(['dome','closed']).reindex(gm.game_id).values.astype(float)
gm['wind']=w.wind.fillna(0).clip(0,30).reindex(gm.game_id).values*(1-gm.dome)
gm['cold']=(w.temp.fillna(60)<=32).reindex(gm.game_id).values.astype(float)*(1-gm.dome)
gm['wind_x_dpyf']=gm.wind*gm.d_pyf_r4/100.0
gm['wk18']=(w.week>=18).reindex(gm.game_id).values.astype(float)

V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
FULL=V1+NEW
V32B=FULL+['d_inj_impact','dome','wind','cold','wind_x_dpyf']

def run(feats,label,drop_wk18_train=False):
    sub=gm.dropna(subset=feats+['margin']).copy()
    tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
    if drop_wk18_train: tr=tr[tr.week<18]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[feats],tr.margin)
    pv,pt=m.predict(va[feats]),m.predict(te[feats])
    te2=te.assign(pred=pt)
    print(f'{label:34s} va={mean_absolute_error(va.margin,pv):.3f} TEST={mean_absolute_error(te2.margin,pt):.3f} (mkt {mean_absolute_error(te2.margin,te2.spread_line):.2f}) ats={(np.sign(pt-te2.spread_line)==np.sign(te2.margin-te2.spread_line)).mean():.3f}')
    return mean_absolute_error(va.margin,pv)

run(FULL,'v3.2 iter1 (repro)')
run(FULL+['d_inj_impact'],'+snap-weighted injuries')
run(FULL+['dome','wind','cold'],'+weather/turf')
run(FULL+['wind_x_dpyf'],'+wind x pass-form')
run(FULL,'iter1, wk18 dropped from train',drop_wk18_train=True)
run(V32B,'v3.2b full (no wk18 drop)')
run(V32B,'v3.2b full, wk18 dropped',drop_wk18_train=True)
gm.to_parquet(D/'out/v32b_games.parquet')
