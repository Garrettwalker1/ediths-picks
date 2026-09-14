#!/usr/bin/env python3
"""NFL v3.2 iteration 3: OC/DC change flags added to v3.2b (coordinators_2006_2025.csv,
PFR-derived 2006-2021 + Wikipedia/PFR team-season pages 2022-2025). Same protocol."""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
D=Path('/tmp/training/nflv32')
gm=pd.read_parquet(D/'out/v32b_games.parquet')
cd=pd.read_csv(D/'coordinators_2006_2025.csv')
cd['name']=cd['name'].str.lower().str.replace(r'[^a-z]','',regex=True)
pv=cd.pivot_table(index=['team','season'],columns='role',values='name',aggfunc='first').reset_index()
pv=pv.sort_values(['team','season'])
for role in ('oc','dc','hc'):
    pv[role]=pv[role].fillna('none')
    pv[role+'_new']=(pv.groupby('team')[role].shift()!=pv[role]).astype(float)
    pv.loc[pv.groupby('team').head(1).index, role+'_new']=np.nan  # first observed season unknown
chg=pv[['team','season','oc_new','dc_new','hc_new']]
games=pd.read_csv(D/'games.csv')
games=games[(games.season>=2010)&(games.season<=2025)&(games.game_type=='REG')][['game_id','season','home_team','away_team']]
g2=games.merge(chg,left_on=['home_team','season'],right_on=['team','season']).drop(columns='team') \
        .merge(chg,left_on=['away_team','season'],right_on=['team','season'],suffixes=('_h','_a')).drop(columns='team')
g2['d_oc_new']=g2.oc_new_h-g2.oc_new_a
g2['d_dc_new']=g2.dc_new_h-g2.dc_new_a
gm=gm.merge(g2[['game_id','d_oc_new','d_dc_new']],on='game_id',how='left')
V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
V32B=V1+NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']
V32C=V32B+['d_oc_new','d_dc_new']
def run(feats,label):
    sub=gm.dropna(subset=feats+['margin']).copy()
    tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[feats],tr.margin)
    pv_,pt=m.predict(va[feats]),m.predict(te[feats])
    print(f'{label:30s} n_tr={len(tr)} va={mean_absolute_error(va.margin,pv_):.3f} TEST={mean_absolute_error(te.margin,pt):.3f} (mkt {mean_absolute_error(te.margin,te.spread_line):.2f}) ats={(np.sign(pt-te.spread_line)==np.sign(te.margin-te.spread_line)).mean():.3f} n_te={len(te)}')
    return mean_absolute_error(va.margin,pv_)
run(V32B,'v3.2b (repro, full sample)')
run(V32B+['d_oc_new'],'+OC change flag')
run(V32B+['d_dc_new'],'+DC change flag')
run(V32C,'v3.2c full (OC+DC flags)')
gm.to_parquet(D/'out/v32c_games.parquet')
