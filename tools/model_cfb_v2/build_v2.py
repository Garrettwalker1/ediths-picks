#!/usr/bin/env python3
"""CFB v2 experiment: add roster-churn features (returning production, portal in/out,
QB continuity) computed from the ESPN player-game corpus. Same protocol as v1:
train 2020-2023, validation 2024 (selection), locked test 2025. Ridge vs v1 baseline.
"""
import numpy as np, pandas as pd, json
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error

ESPN=Path('/tmp/ediths-picks/tools/espn')
games=pd.concat([pd.read_csv(p) for p in ESPN.glob('games/*cfb_*_games.csv')],ignore_index=True)
games=games[games.completed==True].copy()
games['margin']=games.home_score-games.away_score
games['date']=pd.to_datetime(games.date)
td=pd.concat([pd.read_csv(p) for p in ESPN.glob('team_defense/*cfb_*.csv')],ignore_index=True)
td['date']=pd.to_datetime(td.date)
off=td[['event_id','season','team','opponent','points_allowed','pass_yds_allowed','rush_yds_allowed','total_yds_allowed']].rename(
    columns={'team':'opponent','opponent':'team','points_allowed':'points_for','pass_yds_allowed':'pass_yds_for','rush_yds_allowed':'rush_yds_for','total_yds_allowed':'total_yds_for'})
tg=td.merge(off,on=['event_id','season','team','opponent'],how='left')
pg=pd.concat([pd.read_csv(p) for p in ESPN.glob('player_games/*cfb_*.csv')],ignore_index=True)
qb=pg[pg.pass_att.fillna(0)>0].groupby(['event_id','team'],as_index=False).agg(
    qb_att=('pass_att','sum'),qb_cmp=('pass_cmp','sum'),qb_yds=('pass_yds','sum'),qb_td=('pass_td','sum'),qb_int=('pass_int','sum'))
qb['qb_cmp_pct']=qb.qb_cmp/qb.qb_att.replace(0,np.nan)
tg=tg.merge(qb[['event_id','team','qb_cmp_pct','qb_yds','qb_td','qb_int']],on=['event_id','team'],how='left')
tg=tg.sort_values(['team','season','date']).reset_index(drop=True)

# ---- roster churn features ----
pg['prod']=pg[['pass_yds','rush_yds','rec_yds']].fillna(0).sum(axis=1)
pg['tds']=pg[['pass_td','rush_td','rec_td']].fillna(0).sum(axis=1)
ps=pg.groupby(['player_id','season','team'],as_index=False).agg(production=('prod','sum'),tds=('tds','sum'),att=('pass_att','sum'))
# player-season totals regardless of team (a player can appear for 2 teams in a season; keep team rows)
pset={s:set(zip(q.player_id,q.team)) for s,q in ps.groupby('season')}
prod_prev={(r.player_id,r.season,r.team):r.production for r in ps.itertuples()}
att_prev={(r.player_id,r.season,r.team):r.att for r in ps.itertuples()}

rows=[]
for (team,s),grp in ps.groupby(['team','season']):
    if s==2020: continue
    prev=ps[(ps.season==s-1)&(ps.team==team)]
    tot_prev=prev.production.sum()
    if tot_prev<=0: continue
    ret=portal_out=gone=0.0
    for r in prev.itertuples():
        p=r.production
        if (r.player_id,team) in pset[s]: ret+=p
        elif any((r.player_id,t2) in pset[s] for t2 in {t for (pid,t) in pset[s] if pid==r.player_id}): portal_out+=p
        else: gone+=p
    # portal in: S-1 production (any FBS team) of players on T in S who were not on T in S-1
    cur=ps[(ps.season==s)&(ps.team==team)]
    pin=0.0
    for r in cur.itertuples():
        if (r.player_id,team) not in pset[s-1]:
            pin+=sum(v for (pid,ss,t2),v in prod_prev.items() if pid==r.player_id and ss==s-1)
    # qb continuity: S-1 pass_att leader for T present on T in S
    qblead=prev[prev.att>0].sort_values('att').tail(1)
    qb_ret=1.0 if len(qblead) and (qblead.iloc[0].player_id,team) in pset[s] else 0.0
    rows.append({'team':team,'season':s,'ret_share':ret/tot_prev,'portal_out_share':portal_out/tot_prev,
                 'gone_share':gone/tot_prev,'portal_in_yds':pin,'qb_ret':qb_ret,'prev_prod':tot_prev})
churn=pd.DataFrame(rows)
print('churn rows',len(churn), 'seasons',churn.season.value_counts().to_dict())
print(churn[['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']].describe().round(3).to_string())

# ---- v1 pipeline (verbatim) ----
prior=tg.groupby(['team','season'],as_index=False).agg(
    ps_pf=('points_for','mean'),ps_pa=('points_allowed','mean'),ps_yf=('total_yds_for','mean'),ps_ya=('total_yds_allowed','mean'))
prior['season']+=1
prior=prior.rename(columns={c:'prior_'+c.split('_',1)[1] for c in ['ps_pf','ps_pa','ps_yf','ps_ya']})
tg=tg.merge(prior,on=['team','season'],how='left')
lg=tg.groupby('season')[['points_for','points_allowed','total_yds_for','total_yds_allowed']].mean()
for c,src in [('prior_pf','points_for'),('prior_pa','points_allowed'),('prior_yf','total_yds_for'),('prior_ya','total_yds_allowed')]:
    tg[c]=tg[c].fillna(tg.season.map(lg[src]))
g=tg.groupby(['team','season'],group_keys=False)
for c,new in [('points_for','pf'),('points_allowed','pa'),('total_yds_for','yf'),('total_yds_allowed','ya'),
              ('pass_yds_for','pyf'),('pass_yds_allowed','pya'),('rush_yds_for','ryf'),('rush_yds_allowed','rya'),
              ('turnovers_forced','tof'),('qb_cmp_pct','qbc'),('qb_yds','qby'),('qb_td','qbtd'),('qb_int','qbi')]:
    tg[new+'_r4']=g[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
tg['gp']=g['date'].transform(lambda x:x.shift().rolling(100,min_periods=1).count()).fillna(0)
w=(tg.gp/(tg.gp+2)).clip(0,1)
for b,cols in [('pf',('prior_pf','pf_r4')),('pa',('prior_pa','pa_r4')),('yf',('prior_yf','yf_r4')),('ya',('prior_ya','ya_r4'))]:
    tg[b+'_f']=w*tg[cols[1]].fillna(tg[cols[0]])+(1-w)*tg[cols[0]]

# join churn (preseason facts for season S, constant within season)
tg=tg.merge(churn[['team','season','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']],on=['team','season'],how='left')

JC=['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','gp',
    'ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']
h=tg[tg.home_away=='home'].set_index('event_id'); a=tg[tg.home_away=='away'].set_index('event_id')
gm=games.set_index('event_id').join(h[JC].add_prefix('h_'),how='inner').join(a[JC].add_prefix('a_'),how='inner').reset_index()

V1=[]
for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; V1.append('d_'+s)
gm['d_gp']=gm.h_gp-gm.a_gp; V1.append('d_gp')
NEW=[]
for s in ['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; NEW.append('d_'+s)

def run(feats,label):
    sub=gm.dropna(subset=feats+['margin']).copy()
    tr=sub[sub.season<=2023]; va=sub[sub.season==2024]; te=sub[sub.season==2025]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[feats],tr.margin)
    pv,pt=m.predict(va[feats]),m.predict(te[feats])
    acc=(np.sign(pt)==np.sign(te.margin)).mean()
    print(f'{label:28s} n_tr={len(tr)} va_mae={mean_absolute_error(va.margin,pv):.3f} TEST mae={mean_absolute_error(te.margin,pt):.3f} acc={acc:.3f}')
    return mean_absolute_error(te.margin,pt)

print()
run(V1,'v1 features (repro)')
run(V1+['d_ret_share'],'v2a +ret_share')
run(V1+['d_ret_share','d_qb_ret'],'v2b +ret_share +qb_ret')
run(V1+NEW,'v2c all churn')
gm.to_parquet('/tmp/training/cfb/out/v2_games_features.parquet')
churn.to_csv('/tmp/training/cfb/out/v2_churn.csv',index=False)
