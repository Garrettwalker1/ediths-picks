#!/usr/bin/env python3
"""NFL model v3.2: CFB-style margin model with feature fusion (Garrett 9/14):
injuries, history, player/career stats (talent composite), coaches, roster turnover.
Protocol: train <=2022, val 2023 (selection), LOCKED test 2024-2025 reported separately.
Point-in-time only: every feature is shifted/pregame. Book lines (spread_line/moneyline
in games.csv) are the BENCHMARK ONLY, never model inputs.
"""
import numpy as np, pandas as pd, json
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error

D=Path('/tmp/training/nflv32')
games=pd.read_csv(D/'games.csv')
games=games[(games.season>=2010)&(games.season<=2025)&(games.game_type=='REG')].copy()
games['margin']=games.home_score-games.away_score
games['date']=pd.to_datetime(games.gameday)

# ---- team-game stats from stats_player weekly ----
sp=pd.concat([pd.read_csv(D/f'spw_{y}.csv') for y in range(2010,2026)],ignore_index=True)
sp=sp[sp.season_type=='REG']
agg=sp.groupby(['season','week','team','opponent_team'],as_index=False).agg(
    pass_yds=('passing_yards','sum'), rush_yds=('rushing_yards','sum'),
    ints_thrown=('passing_interceptions','sum'), fum_lost=('fumbles_lost_total','sum'),
    sacks_taken=('sacks_suffered','sum'), pass_att=('attempts','sum'), pass_cmp=('completions','sum'),
    pass_td=('passing_tds','sum'), rush_att=('carries','sum'),
    def_sacks=('def_sacks','sum'), def_int=('def_interceptions','sum'), fum_rec_opp=('fumble_recovery_opp','sum'))
tg=agg.copy()
tg['total_yds_for']=tg.pass_yds+tg.rush_yds
tg['giveaways']=tg.ints_thrown+tg.fum_lost
tg['takeaways']=tg.def_int+tg.fum_rec_opp
tg['sacks_made']=tg.def_sacks
# defensive view: opponent's offense is this team's defense
dv=agg.rename(columns={'team':'_t','opponent_team':'team'})[['season','week','team','_t','pass_yds','rush_yds']]
dv=dv.rename(columns={'_t':'opponent_team','pass_yds':'pass_yds_allowed','rush_yds':'rush_yds_allowed'})
tg=tg.merge(dv,on=['season','week','team','opponent_team'],how='left')
tg['total_yds_allowed']=tg.pass_yds_allowed+tg.rush_yds_allowed
tg['cmp_pct']=tg.pass_cmp/tg.pass_att.replace(0,np.nan)

# ---- season priors ----
prior=tg.groupby(['team','season'],as_index=False).agg(ps_yf=('total_yds_for','mean'),ps_ya=('total_yds_allowed','mean'))
prior['season']+=1
prior=prior.rename(columns={'ps_yf':'prior_yf','ps_ya':'prior_ya'})
tg=tg.merge(prior,on=['team','season'],how='left')
lg=tg.groupby('season')[['total_yds_for','total_yds_allowed']].mean()
for c,src in [('prior_yf','total_yds_for'),('prior_ya','total_yds_allowed')]:
    tg[c]=tg[c].fillna(tg.season.map(lg[src]))

# ---- rolling r4 form (shifted) ----
tg=tg.sort_values(['team','season','week']).reset_index(drop=True)
g=tg.groupby(['team','season'],group_keys=False)
for c,new in [('total_yds_for','yf'),('total_yds_allowed','ya'),('pass_yds','pyf'),('pass_yds_allowed','pya'),
              ('rush_yds','ryf'),('rush_yds_allowed','rya'),('giveaways','gv'),('takeaways','tk'),
              ('sacks_taken','skt'),('sacks_made','skm'),('cmp_pct','qbc'),('pass_td','ptd')]:
    tg[new+'_r4']=g[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
tg['gp']=g['week'].transform(lambda x:x.shift().rolling(100,min_periods=1).count()).fillna(0)
w=(tg.gp/(tg.gp+2)).clip(0,1)
for b,cols in [('yf',('prior_yf','yf_r4')),('ya',('prior_ya','ya_r4'))]:
    tg[b+'_f']=w*tg[cols[1]].fillna(tg[cols[0]])+(1-w)*tg[cols[0]]

# ---- points for/against from games.csv (map team-game to game_id) ----
h=games[['game_id','season','week','home_team','home_score','away_score']].rename(columns={'home_team':'team','home_score':'points_for','away_score':'points_allowed'})
a=games[['game_id','season','week','away_team','away_score','home_score']].rename(columns={'away_team':'team','away_score':'points_for','home_score':'points_allowed'})
pts=pd.concat([h,a])
tg=tg.merge(pts,on=['season','week','team'],how='left')
tg=tg.sort_values(['team','season','week']).reset_index(drop=True)
g2=tg.groupby(['team','season'],group_keys=False)
tg['pf_r4']=g2['points_for'].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
tg['pa_r4']=g2['points_allowed'].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
# season priors for points
pp=tg.groupby(['team','season'],as_index=False).agg(ps_pf=('points_for','mean'),ps_pa=('points_allowed','mean'))
pp['season']+=1; pp=pp.rename(columns={'ps_pf':'prior_pf','ps_pa':'prior_pa'})
tg=tg.merge(pp,on=['team','season'],how='left')
lgp=tg.groupby('season')[['points_for','points_allowed']].mean()
tg['prior_pf']=tg['prior_pf'].fillna(tg.season.map(lgp['points_for']))
tg['prior_pa']=tg['prior_pa'].fillna(tg.season.map(lgp['points_allowed']))
tg['pf_f']=w*tg['pf_r4'].fillna(tg['prior_pf'])+(1-w)*tg['prior_pf']
tg['pa_f']=w*tg['pa_r4'].fillna(tg['prior_pa'])+(1-w)*tg['prior_pa']

# ---- roster turnover / talent composite (returning + incoming career production) ----
sp['prod']=sp[['passing_yards','rushing_yards','receiving_yards']].fillna(0).sum(axis=1)
ps=sp.groupby(['player_id','season','team'],as_index=False).agg(production=('prod','sum'))
pset={s:set(zip(q.player_id,q.team)) for s,q in ps.groupby('season')}
rows=[]
for (team,s),grp in ps.groupby(['team','season']):
    if s==2010: continue
    prev=ps[(ps.season==s-1)&(ps.team==team)]
    tot=prev.production.sum()
    if tot<=0: continue
    ret=sum(r.production for r in prev.itertuples() if (r.player_id,team) in pset[s])
    # incoming production: production last season (any team) of players on this team this season but not last
    cur=ps[(ps.season==s)&(ps.team==team)]
    inc=0.0
    for r in cur.itertuples():
        if (r.player_id,team) not in pset[s-1]:
            inc+=ps[(ps.season==s-1)&(ps.player_id==r.player_id)].production.sum()
    rows.append({'team':team,'season':s,'ret_share':ret/tot,'incoming_prod':inc,'prev_prod':tot})
churn=pd.DataFrame(rows)
tg=tg.merge(churn[['team','season','ret_share','incoming_prod']],on=['team','season'],how='left')

# ---- QB continuity ----
qb=sp[sp.attempts.fillna(0)>0].groupby(['season','week','team'],as_index=False).apply(lambda x:x.loc[x.attempts.idxmax()])[['season','week','team','player_id']]
qb=qb.rename(columns={'player_id':'qb_id'})
tg=tg.merge(qb,on=['season','week','team'],how='left')
tg=tg.sort_values(['team','season','week']).reset_index(drop=True)
g3=tg.groupby('team',group_keys=False)
tg['qb_same']= (tg['qb_id']==g3['qb_id'].shift()).astype(float)

# ---- injuries (pregame report, shifted week is same-week pregame: released before games) ----
inj=pd.concat([pd.read_parquet(D/f'inj_{y}.parquet').assign(season=y) for y in range(2010,2026)],ignore_index=True)
inj['out_pts']=inj.report_status.map({'Out':1.0,'Doubtful':0.75,'Questionable':0.25}).fillna(0.0)
iw=inj.groupby(['season','week','team'],as_index=False).agg(inj_pts=('out_pts','sum'))
qb_out=inj[(inj.position=='QB')&(inj.report_status.isin(['Out','Doubtful']))].groupby(['season','week','team'],as_index=False).size().rename(columns={'size':'qb_out'})
iw=iw.merge(qb_out,on=['season','week','team'],how='left').fillna({'qb_out':0})
tg=tg.merge(iw,on=['season','week','team'],how='left').fillna({'inj_pts':0.0,'qb_out':0})

# ---- coaches + rest ----
hc=games[['game_id','home_team','away_team','home_coach','away_coach','home_rest','away_rest']].copy()
tg=tg.merge(pd.concat([
    hc[['game_id','home_team','home_coach','home_rest']].rename(columns={'home_team':'team','home_coach':'coach','home_rest':'rest'}),
    hc[['game_id','away_team','away_coach','away_rest']].rename(columns={'away_team':'team','away_coach':'coach','away_rest':'rest'})]),
    on=['game_id','team'],how='left')
tg=tg.sort_values(['team','date' if 'date' in tg else 'week']).reset_index(drop=True)
pco=tg.groupby(['team','season'])['coach'].first().reset_index().rename(columns={'coach':'coach_first'})
pco['season']+=1; pco=pco.rename(columns={'coach_first':'prev_coach'})
tg=tg.merge(pco,on=['team','season'],how='left')
tg['coach_new']=(tg.coach!=tg.prev_coach).astype(float)

# ---- assemble game frame ----
JC=['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp',
    'ret_share','incoming_prod','qb_same','inj_pts','qb_out','coach_new','rest']
hh=tg[tg.team==tg.game_id.map(games.set_index('game_id').home_team)].set_index('game_id')
aa=tg[tg.team==tg.game_id.map(games.set_index('game_id').away_team)].set_index('game_id')
gm=games.set_index('game_id').join(hh[JC].add_prefix('h_'),how='inner').join(aa[JC].add_prefix('a_'),how='inner').reset_index()
gm['d_rest']=gm.h_rest-gm.a_rest

V1=[]; 
for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; V1.append('d_'+s)
NEW=['d_rest']
for s in ['ret_share','incoming_prod','qb_same','inj_pts','qb_out','coach_new']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; NEW.append('d_'+s)

def run(feats,label):
    sub=gm.dropna(subset=feats+['margin']).copy()
    tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[feats],tr.margin)
    pv,pt=m.predict(va[feats]),m.predict(te[feats])
    acc=(np.sign(pt)==np.sign(te.margin)).mean()
    # vs closing spread benchmark on test
    te2=te.assign(pred=pt)
    mkt_mae=mean_absolute_error(te2.margin,te2.spread_line)
    mdl_mae=mean_absolute_error(te2.margin,pt)
    ats=(np.sign(pt-te2.spread_line)==np.sign(te2.margin-te2.spread_line)).mean()
    print(f'{label:26s} va={mean_absolute_error(va.margin,pv):.2f} TEST mae={mdl_mae:.2f} (mkt {mkt_mae:.2f}) acc={acc:.3f} ATS-vs-close={ats:.3f} n_te={len(te)}')
    return mdl_mae

print('games:',len(gm),'seasons',gm.season.min(),'-',gm.season.max())
run(V1,'v3.2 base (form+priors)')
run(V1+['d_rest'],'+rest')
run(V1+['d_ret_share','d_incoming_prod'],'+roster turnover')
run(V1+['d_qb_same','d_qb_out'],'+QB facts')
run(V1+['d_inj_pts'],'+injuries')
run(V1+['d_coach_new'],'+coach change')
run(V1+NEW,'v3.2 full fusion')

# ---- Elo baseline ----
K=20.0; base=1500.0; hfa=48.0
elo={}
preds=[]
for r in gm.sort_values(['season','week']).itertuples():
    eh,ea=elo.get(r.home_team,base),elo.get(r.away_team,base)
    exp=1/(1+10**(-((eh+hfa)-ea)/400))
    pred_margin=( (eh+hfa)-ea )/25.0
    preds.append((r.game_id,pred_margin))
    mov=max(1,abs(r.margin)/20)
    elo[r.home_team]=eh+K*mov*((1 if r.margin>0 else 0)-exp)
    elo[r.away_team]=ea-K*mov*((1 if r.margin>0 else 0)-exp)
el=pd.DataFrame(preds,columns=['game_id','elo_pred'])
gm2=gm.merge(el,on='game_id')
te=gm2[gm2.season>=2024]
print(f'Elo baseline:           TEST mae={mean_absolute_error(te.margin,te.elo_pred):.2f} acc={(np.sign(te.elo_pred)==np.sign(te.margin)).mean():.3f}')
tr=gm2[gm2.season<=2022]; va=gm2[gm2.season==2023]
print(f'Elo val mae={mean_absolute_error(va.margin,va.elo_pred):.2f} train mae={mean_absolute_error(tr.margin,tr.elo_pred):.2f}')

# ---- full-fusion detailed validation ----
FEATS=V1+NEW
sub=gm.dropna(subset=FEATS+['margin']).copy()
tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[FEATS],tr.margin)
sub=sub.assign(pred=m.predict(sub[FEATS]))
te=sub[sub.season>=2024].merge(el,on='game_id')
for yr in (2024,2025):
    t=te[te.season==yr]
    print(f'  {yr}: model mae={mean_absolute_error(t.margin,t.pred):.2f} elo={mean_absolute_error(t.margin,t.elo_pred):.2f} mkt={mean_absolute_error(t.margin,t.spread_line):.2f} ats={(np.sign(t.pred-t.spread_line)==np.sign(t.margin-t.spread_line)).mean():.3f} n={len(t)}')
# bootstrap game-cluster CI on deltas (test)
rng=np.random.default_rng(42)
d_elo=(te.margin-te.pred).abs()-(te.margin-te.elo_pred).abs()
d_mkt=(te.margin-te.pred).abs()-(te.margin-te.spread_line).abs()
idx=np.arange(len(te))
B=500
be=[]; bm=[]
for _ in range(B):
    s2=rng.choice(idx,size=len(idx),replace=True)
    be.append(d_elo.iloc[s2].mean()); bm.append(d_mkt.iloc[s2].mean())
import numpy as np
for lbl,arr in (('model-minus-elo MAE',be),('model-minus-mkt MAE',bm)):
    lo,hi=np.percentile(arr,[2.5,97.5]); print(f'  {lbl}: mean={np.mean(arr):.3f} CI95=[{lo:.3f},{hi:.3f}] (negative favors model)')
# moneyline benchmark (test): closing ML home win prob vs model P(home win) via margin dist
def ml_prob(ml):
    ml=np.asarray(ml,dtype=float)
    return np.where(ml<0, -ml/(-ml+100), 100/(ml+100))
te=te.assign(mkt_hwp=ml_prob(te.home_moneyline))
# model home-win prob: logistic on predicted margin (fit on train residuals)
from sklearn.linear_model import LogisticRegression
tr2=sub[sub.season<=2022].assign(pred=m.predict(sub[sub.season<=2022][FEATS]))
lr=LogisticRegression().fit(tr2[['pred']],(tr2.margin>0).astype(int))
te=te.assign(mdl_hwp=lr.predict_proba(te[['pred']])[:,1])
from sklearn.metrics import log_loss, brier_score_loss
y=(te.margin>0).astype(int)
print(f'  ML test: model acc={(lr.predict(te[["pred"]])==y).mean():.3f} mkt acc={( (te.mkt_hwp>0.5).astype(int)==y).mean():.3f}')
print(f'  ML test: model brier={brier_score_loss(y,te.mdl_hwp):.4f} mkt brier={brier_score_loss(y,te.mkt_hwp):.4f}')
print(f'  ML test: model logloss={log_loss(y,te.mdl_hwp):.4f} mkt logloss={log_loss(y,te.mkt_hwp):.4f}')
gm.to_parquet(D/'out/v32_games.parquet')
churn.to_csv(D/'out/v32_churn.csv',index=False)
