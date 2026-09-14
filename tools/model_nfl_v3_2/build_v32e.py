#!/usr/bin/env python3
"""NFL v3.2 iteration 5: richer free nflverse play-by-play aggregation.
Situation-neutral, down/distance, line-vs-skill, explosives and red-zone splits.
Selection is 2023 validation only; 2024-25 remains locked test."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
D=Path('/tmp/training/nflv32')
OUT=D/'out'
cols=['game_id','season','week','posteam','defteam','play_type','epa','success','down','ydstogo',
      'yardline_100','game_seconds_remaining','score_differential','sack','qb_hit','yards_gained',
      'cpoe','air_epa','yac_epa','air_yards','yards_after_catch']

def safe_mean(s, mask):
    x=s[mask]
    return x.mean() if len(x) else np.nan

def aggregate_side(p, teamcol, prefix):
    rows=[]
    for (gid,season,week,team),x in p.groupby(['game_id','season','week',teamcol],sort=False):
        pas=x.play_type.eq('pass'); run=x.play_type.eq('run')
        neutral=(x.game_seconds_remaining.gt(300)&x.score_differential.abs().le(16))
        early=x['down'].isin([1,2]); third=x['down'].eq(3)
        rz=x.yardline_100.le(20)
        vals={
          'neutral_epa':safe_mean(x.epa,neutral), 'neutral_success':safe_mean(x.success,neutral),
          'early_epa':safe_mean(x.epa,early), 'early_success':safe_mean(x.success,early),
          'third_epa':safe_mean(x.epa,third), 'third_success':safe_mean(x.success,third),
          'pass_epa':safe_mean(x.epa,pas), 'rush_epa':safe_mean(x.epa,run),
          'pass_success':safe_mean(x.success,pas), 'rush_success':safe_mean(x.success,run),
          'sack_rate':safe_mean(x.sack,pas), 'qbhit_rate':safe_mean(x.qb_hit,pas),
          'rush_stuff':safe_mean((x.yards_gained<=0).astype(float),run),
          'rush_explosive':safe_mean((x.yards_gained>=10).astype(float),run),
          'pass_explosive':safe_mean((x.yards_gained>=20).astype(float),pas),
          'cpoe':safe_mean(x.cpoe,pas), 'air_epa':safe_mean(x.air_epa,pas),
          'yac_epa':safe_mean(x.yac_epa,pas), 'air_yards':safe_mean(x.air_yards,pas),
          'yac':safe_mean(x.yards_after_catch,pas),
          'rz_epa':safe_mean(x.epa,rz), 'rz_success':safe_mean(x.success,rz)
        }
        rows.append({'game_id':gid,'season':season,'week':week,'team':team,**{prefix+k:v for k,v in vals.items()}})
    return pd.DataFrame(rows)

parts=[]
for y in range(2010,2026):
    p=pd.read_parquet(D/f'pbp/pbp_{y}.parquet',columns=cols)
    p=p[p.posteam.notna()&p.defteam.notna()&p.play_type.isin(['pass','run'])&p.epa.notna()].copy()
    off=aggregate_side(p,'posteam','o_')
    de=aggregate_side(p,'defteam','d_')
    z=off.merge(de,on=['game_id','season','week','team'],how='inner')
    parts.append(z); print('aggregate',y,len(z),flush=True)
tg=pd.concat(parts,ignore_index=True)
tg.to_parquet(OUT/'team_game_rich_pbp.parquet')

# Pregame features: shifted rolling-4 blended with prior-season average.
metric_cols=[c for c in tg if c.startswith(('o_','d_'))]
tg=tg.sort_values(['team','season','week','game_id']).reset_index(drop=True)
base=tg[['game_id','season','week','team']].copy()
for c in metric_cols:
    r4=tg.groupby(['team','season'])[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
    prior=tg.groupby(['team','season'])[c].mean().rename('v').reset_index(); prior['season']+=1
    pm=tg[['team','season']].merge(prior,on=['team','season'],how='left')['v']
    lg=tg.groupby('season')[c].mean()
    pm=pm.fillna(tg.season.map(lg)).fillna(tg[c].mean())
    gp=tg.groupby(['team','season']).cumcount()
    w=(gp/(gp+2)).clip(0,1)
    base[c+'_f']=w*r4.fillna(pm)+(1-w)*pm

sched=pd.read_csv(D/'games.csv')
sched=sched[(sched.season>=2010)&(sched.season<=2025)&(sched.game_type=='REG')]
h=base.merge(sched[['game_id','home_team']],left_on=['game_id','team'],right_on=['game_id','home_team'])
a=base.merge(sched[['game_id','away_team']],left_on=['game_id','team'],right_on=['game_id','away_team'])
h=h.set_index('game_id'); a=a.set_index('game_id')
diff=pd.DataFrame(index=h.index.intersection(a.index))
for c in [x+'_f' for x in metric_cols]: diff['p_'+c]=h.loc[diff.index,c]-a.loc[diff.index,c]
diff=diff.reset_index()
gm=pd.read_parquet(OUT/'v32b_games.parquet').merge(diff,on='game_id',how='left')

V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
CONTEXT=NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']
V32B=V1+CONTEXT
# Differential convention: home offense minus away offense, and home defense minus away defense.
def fs(*names):
    out=[]
    for n in names: out += ['p_o_'+n+'_f','p_d_'+n+'_f']
    return out
SITUATION=fs('neutral_epa','neutral_success','early_epa','early_success','third_epa','third_success')
DOWNS=fs('early_epa','early_success','third_epa','third_success')
LINE=fs('rush_epa','rush_success','sack_rate','qbhit_rate','rush_stuff')
SKILL=fs('pass_epa','pass_success','cpoe','air_epa','yac_epa','air_yards','yac')
EXPLOSIVE=fs('rush_explosive','pass_explosive')
REDZONE=fs('rz_epa','rz_success')
variants={
 'v3.2b_repro':V32B,
 'situation_neutral':V32B+SITUATION,
 'down_splits':V32B+DOWNS,
 'line_decomposition':V32B+LINE,
 'skill_decomposition':V32B+SKILL,
 'explosives_redzone':V32B+EXPLOSIVE+REDZONE,
 'line_plus_skill':V32B+LINE+SKILL,
 'rich_full':V32B+SITUATION+LINE+SKILL+EXPLOSIVE+REDZONE,
 'rich_context_no_yards':CONTEXT+SITUATION+LINE+SKILL+EXPLOSIVE+REDZONE,
}
res={}
preds={}
for label,feats in variants.items():
    sub=gm.dropna(subset=feats+['margin']).copy()
    tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[feats],tr.margin)
    pv=m.predict(va[feats]); pt=m.predict(te[feats])
    vm=mean_absolute_error(va.margin,pv); tm=mean_absolute_error(te.margin,pt)
    ats=(np.sign(pt-te.spread_line)==np.sign(te.margin-te.spread_line)).mean()
    mm=mean_absolute_error(te.margin,te.spread_line)
    res[label]={'features':len(feats),'val_mae':round(vm,4),'test_mae':round(tm,4),'market_mae':round(mm,4),'ats':round(float(ats),4),'n_val':len(va),'n_test':len(te)}
    preds[label]=(te[['game_id','margin','spread_line']].copy(),pt)
    print(f'{label:24s} p={len(feats):2d} val={vm:.3f} test={tm:.3f} mkt={mm:.3f} ats={ats:.3f} n={len(te)}',flush=True)
# Val-first selection compares richer variants with the reference.
selected=min(res,key=lambda k:res[k]['val_mae'])
ref='v3.2b_repro'
# game-cluster bootstrap test deltas for winner and each promising val improvement
rng=np.random.default_rng(3205)
def boot_delta(label, comparator):
    te,p=preds[label]; _,q=preds[comparator]
    a=np.abs(te.margin.to_numpy()-p); b=np.abs(te.margin.to_numpy()-q)
    n=len(a); ds=[]
    for _ in range(1000):
        ix=rng.integers(0,n,n); ds.append(float(np.mean(a[ix]-b[ix])))
    return {'mean':round(float(np.mean(ds)),4),'ci95':[round(float(x),4) for x in np.quantile(ds,[.025,.975])]}
for label in res:
    if label!=ref and res[label]['val_mae'] < res[ref]['val_mae']:
        res[label]['bootstrap_vs_v32b']=boot_delta(label,ref)
        # market interval
        te,p=preds[label]; a=np.abs(te.margin.to_numpy()-p); b=np.abs(te.margin.to_numpy()-te.spread_line.to_numpy())
        ds=[]
        for _ in range(1000):
            ix=rng.integers(0,len(a),len(a)); ds.append(float(np.mean(a[ix]-b[ix])))
        res[label]['bootstrap_vs_close']={'mean':round(float(np.mean(ds)),4),'ci95':[round(float(x),4) for x in np.quantile(ds,[.025,.975])]}
out={'built':'2026-09-14','protocol':'train 2010-22, validation 2023, locked test 2024-25; Ridge alpha=10; 1000 game bootstraps for val-improving variants','variants':res,'val_selected':selected,'reference':ref}
(OUT/'v32e_results.json').write_text(json.dumps(out,indent=2)+'\n')
gm.to_parquet(OUT/'v32e_games.parquet')
print(json.dumps({'val_selected':selected,'selected':res[selected],'reference':res[ref]},indent=2))
