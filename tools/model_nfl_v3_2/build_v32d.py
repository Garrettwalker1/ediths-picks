#!/usr/bin/env python3
"""NFL v3.2 iteration 4a: player/play-level EPA efficiency features from nflverse pbp.
Same construction as v3.2 (prior-season mean blended with shifted rolling-4, gp-weighted)."""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
D=Path('/tmp/training/nflv32')
tg=pd.read_parquet(D/'out/team_game_epa.parquet')
games=pd.read_csv(D/'games.csv')
games=games[(games.season>=2010)&(games.season<=2025)&(games.game_type=='REG')][['game_id','season','week','home_team','away_team']]
tg=tg.merge(games,on=['game_id','season','week'])  # REG-only, adds home/away
tg=tg.sort_values(['team','season','week']).reset_index(drop=True)
g=tg.groupby(['team','season'],group_keys=False)
for c,new in [('off_epa_pp','epao'),('def_epa_pp','epad'),('off_success','suco'),('def_success','sucd'),
              ('off_pass_epa_pp','pepa'),('off_rush_epa_pp','repa')]:
    tg[new+'_r4']=g[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
    ps=tg.groupby(['team','season'])[c].mean().rename('prior_'+new).reset_index()
    ps['season']+=1
    tg=tg.merge(ps,on=['team','season'],how='left')
    lg=tg.groupby('season')[c].mean()
    tg['prior_'+new]=tg['prior_'+new].fillna(tg.season.map(lg))
tg['gp']=g['week'].transform(lambda x:x.shift().rolling(100,min_periods=1).count()).fillna(0)
w=(tg.gp/(tg.gp+2)).clip(0,1)
for new in ('epao','epad','suco','sucd','pepa','repa'):
    tg[new+'_f']=w*tg[new+'_r4'].fillna(tg['prior_'+new])+(1-w)*tg['prior_'+new]
JC=['team','epao_f','epad_f','suco_f','sucd_f','pepa_f','repa_f']
hh=tg[tg.team==tg.game_id.map(games.set_index('game_id').home_team)].set_index('game_id')
aa=tg[tg.team==tg.game_id.map(games.set_index('game_id').away_team)].set_index('game_id')
ge=games.set_index('game_id').join(hh[JC].add_prefix('h_'),how='inner').join(aa[JC].add_prefix('a_'),how='inner').reset_index()
for c in JC[1:]:
    ge['d_'+c]=ge['h_'+c]-ge['a_'+c]
gm=pd.read_parquet(D/'out/v32b_games.parquet').merge(ge[['game_id']+['d_'+c for c in JC[1:]]],on='game_id',how='left')
EPA=['d_epao_f','d_epad_f','d_suco_f','d_sucd_f','d_pepa_f','d_repa_f']
V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
V32B=V1+NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']
def run(feats,label):
    sub=gm.dropna(subset=feats+['margin']).copy()
    tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[feats],tr.margin)
    pv,pt=m.predict(va[feats]),m.predict(te[feats])
    print(f'{label:36s} va={mean_absolute_error(va.margin,pv):.3f} TEST={mean_absolute_error(te.margin,pt):.3f} (mkt {mean_absolute_error(te.margin,te.spread_line):.2f}) ats={(np.sign(pt-te.spread_line)==np.sign(te.margin-te.spread_line)).mean():.3f}')
    return mean_absolute_error(va.margin,pv)
run(V32B,'v3.2b (repro)')
run(V32B+['d_epao_f','d_epad_f'],'+EPA off/def')
run(V32B+EPA,'+EPA full (6)')
run(NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']+EPA,'EPA-only + context (no yards)')
run(V32B+EPA,'v3.2d full')
gm.to_parquet(D/'out/v32d_games.parquet')
# collinearity-controlled variants
V1_NOPASSRUSH=[c for c in V1 if c not in ('d_pyf_r4','d_pya_r4','d_ryf_r4','d_rya_r4')]
run(V1_NOPASSRUSH+NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']+['d_epao_f','d_epad_f'],'drop pass/rush yards, +EPA off/def')
run(NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']+['d_epao_f','d_epad_f'],'EPA off/def only + context')
run(NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']+['d_epao_f','d_epad_f','d_pepa_f','d_repa_f'],'EPA off/def+splits + context')
run(NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']+['d_pf_f'.replace('d_pf_f','d_pf_f')] if False else NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf','d_pf_f','d_pa_f']+['d_epao_f','d_epad_f'],'points+EPA+context')
