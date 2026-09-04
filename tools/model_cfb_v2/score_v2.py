#!/usr/bin/env python3
"""Score the 2026-09-05 FBS slate with frozen CFB game-line model v1 (ridge, alpha=10, StandardScaler).
Deployment refit on ALL 2020-2025 games (features/algorithm/hyperparameters frozen from v1).
2026 pre-Saturday finals incorporated from ESPN summaries (GT/Colorado excluded - stuck ESPN feed).
"""
import numpy as np, pandas as pd, json, glob
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ESPN=Path('/tmp/ediths-picks/tools/espn'); OUT=Path('/tmp/training/cfb/out')

games=pd.concat([pd.read_csv(p) for p in ESPN.glob('games/*cfb_*_games.csv')],ignore_index=True)
games=games[games.completed==True].copy()
games['margin']=games.home_score-games.away_score; games['total']=games.home_score+games.away_score
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

# ---- 2026 pre-Saturday rows from summaries ----
rows=[]
for f in glob.glob('/tmp/training/cfb/sum_*.json'):
    inner=json.loads(json.load(open(f))[0]['text'])
    ev=f.split('sum_')[1].split('.json')[0]
    hd=inner['header']['competitions'][0]; date=hd['date'][:10]
    scores={c['homeAway']:float(c['score']) for c in hd['competitors']}
    qbs={}
    for pl in inner['boxscore'].get('players',[]):
        tm=pl['team']['displayName']
        for st in pl.get('statistics',[]):
            if st.get('name')=='passing':
                keys=st['keys']
                for ath in st.get('athletes',[]):
                    v=dict(zip(keys,ath['stats']))
                    try:
                        cmp_,att=v['completions/attempts'].split('/')
                        a=qbs.setdefault(tm,[0,0,0,0,0]); a[0]+=float(cmp_); a[1]+=float(att); a[2]+=float(v['yards']); a[3]+=float(v['touchdowns']); a[4]+=float(v['interceptions'])
                    except: pass
    for t in inner['boxscore']['teams']:
        tm=t['team']['displayName']; opp=[x['team']['displayName'] for x in inner['boxscore']['teams'] if x['team']['displayName']!=tm][0]
        stats={s['name']:s['displayValue'] for s in t['statistics']}
        ha=t['homeAway']; pf=scores[ha]; pa=scores['away' if ha=='home' else 'home']
        ty=float(stats.get('totalYards',0)); py=float(stats.get('netPassingYards',0)); ry=float(stats.get('rushingYards',0)); to=float(stats.get('turnovers',0))
        qc=qbs.get(tm,[0,0,0,0,0])
        rows.append({'event_id':ev,'league':'CFB','season':2026,'date':date,'team':tm,'opponent':opp,'home_away':ha,
            'points_allowed':pa,'pass_yds_allowed':0.0,'rush_yds_allowed':0.0,'total_yds_allowed':0.0,
            'interceptions_forced':0.0,'fumbles_forced':0.0,'turnovers_forced':0.0,
            'points_for':pf,'pass_yds_for':py,'rush_yds_for':ry,'total_yds_for':ty,
            'qb_cmp_pct':(qc[0]/qc[1] if qc[1] else np.nan),'qb_yds':qc[2],'qb_td':qc[3],'qb_int':qc[4],
            'turnovers_lost':to})
# defense stats for 2026 rows: opponent's offense line
d26=pd.DataFrame(rows)
m=d26.set_index(['event_id','team'])
for i,r in d26.iterrows():
    o=m.loc[(r.event_id,r.opponent)]
    d26.loc[i,['pass_yds_allowed','rush_yds_allowed','total_yds_allowed']]=o[['pass_yds_for','rush_yds_for','total_yds_for']].values
    d26.loc[i,'turnovers_forced']=o['turnovers_lost']
d26['date']=pd.to_datetime(d26['date'])
tg=pd.concat([tg,d26.drop(columns=['turnovers_lost'])],ignore_index=True)
tg=tg.sort_values(['team','season','date']).reset_index(drop=True)


# ---- v2 context features (preseason facts per team-season) ----
churn_hist=pd.read_csv('/tmp/training/cfb/out/v2_churn.csv')  # 2021-2025 training churn
churn26=pd.read_csv('/tmp/training/cfb/out/v2_churn_2026.csv')  # 2026 from ESPN rosters
churn=pd.concat([churn_hist,churn26],ignore_index=True)
tg=tg.merge(churn[['team','season','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']],on=['team','season'],how='left')
import json as _json
_cflags=_json.load(open('/tmp/training/cfb/coach_flags.json'))
_dd=pd.read_csv('/tmp/training/cfb/out/v2_draft_losses.csv')
tg=tg.merge(_dd[['team','season','drafted_prod']],on=['team','season'],how='left')
tg['new_coach']=tg.apply(lambda r: _cflags.get(f"{r['team']}|{r['season']}",0),axis=1)

# ---- features identical to train_cfb.py ----
prior=tg[tg.season<=2025].groupby(['team','season'],as_index=False).agg(
    ps_pf=('points_for','mean'),ps_pa=('points_allowed','mean'),ps_yf=('total_yds_for','mean'),ps_ya=('total_yds_allowed','mean'))
prior['season']+=1
prior=prior.rename(columns={c:'prior_'+c.split('_',1)[1] for c in ['ps_pf','ps_pa','ps_yf','ps_ya']})
tg=tg.merge(prior,on=['team','season'],how='left')
lg=tg[tg.season<=2025].groupby('season')[['points_for','points_allowed','total_yds_for','total_yds_allowed']].mean()
lg2025=lg.loc[2025]
for c,src in [('prior_pf','points_for'),('prior_pa','points_allowed'),('prior_yf','total_yds_for'),('prior_ya','total_yds_allowed')]:
    tg[c]=tg[c].fillna(lg2025[src] if (tg.season==2026).any() else tg.season.map(lg[src]))
g=tg.groupby(['team','season'],group_keys=False)
for c,new in [('points_for','pf'),('points_allowed','pa'),('total_yds_for','yf'),('total_yds_allowed','ya'),
              ('pass_yds_for','pyf'),('pass_yds_allowed','pya'),('rush_yds_for','ryf'),('rush_yds_allowed','rya'),
              ('turnovers_forced','tof'),('qb_cmp_pct','qbc'),('qb_yds','qby'),('qb_td','qbtd'),('qb_int','qbi')]:
    tg[new+'_r4']=g[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
tg['gp']=g['date'].transform(lambda x:x.shift().rolling(100,min_periods=1).count()).fillna(0)
w=(tg.gp/(tg.gp+2)).clip(0,1)
for b,cols in [('pf',('prior_pf','pf_r4')),('pa',('prior_pa','pa_r4')),('yf',('prior_yf','yf_r4')),('ya',('prior_ya','ya_r4'))]:
    tg[b+'_f']=w*tg[cols[1]].fillna(tg[cols[0]])+(1-w)*tg[cols[0]]

h=tg[tg.home_away=='home'].set_index('event_id'); a=tg[tg.home_away=='away'].set_index('event_id')
JC=['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','gp','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod']
gm=games.set_index('event_id').join(h[JC].add_prefix('h_'),how='inner').join(a[JC].add_prefix('a_'),how='inner').reset_index()
FEATS=[]
for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; FEATS.append('d_'+s)
gm['d_gp']=gm.h_gp-gm.a_gp; FEATS.append('d_gp')
hist=gm.dropna(subset=FEATS+['margin'])
model=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(hist[FEATS],hist.margin)
print('refit rows',len(hist))

# ---- Saturday slate ----
# 2026 feature lookup: teams with no 2026 games fall back to 2025 season means for every feature
# (deployment-side imputation for Week 1; model artifact untouched; documented on the board).
r4cols=['pyf','pya','ryf','rya','tof','qbc','qby','qbtd','qbi']
extra26=churn26.set_index('team')[['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']]
s25=tg[tg.season==2025].groupby('team').agg(
    prior_pf=('points_for','mean'),prior_pa=('points_allowed','mean'),
    prior_yf=('total_yds_for','mean'),prior_ya=('total_yds_allowed','mean'),
    **{c+'_r4':({'pyf':'pass_yds_for','pya':'pass_yds_allowed','ryf':'rush_yds_for','rya':'rush_yds_allowed','tof':'turnovers_forced','qbc':'qb_cmp_pct','qby':'qb_yds','qbtd':'qb_td','qbi':'qb_int'}[c],'mean') for c in r4cols}).reset_index()
s25['pf_f']=s25.prior_pf; s25['pa_f']=s25.prior_pa; s25['yf_f']=s25.prior_yf; s25['ya_f']=s25.prior_ya; s25['gp']=0.0
s25=s25.merge(extra26.reset_index(),on='team',how='left')
s25['new_coach']=s25.team.map(lambda t: _cflags.get(f'{t}|2026',0))
_dd26=_dd[_dd.season==2026].set_index('team')['drafted_prod']
s25['drafted_prod']=s25.team.map(_dd26).fillna(0)
last26=tg[tg.season==2026].sort_values('date').groupby('team').tail(1)[['team']+['pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['gp']]
last26=last26.merge(extra26.reset_index(),on='team',how='left')
last26['new_coach']=last26.team.map(lambda t: _cflags.get(f'{t}|2026',0))
last26['drafted_prod']=last26.team.map(_dd26).fillna(0)
feat26=pd.concat([s25[['team','pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['gp','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod']],last26],ignore_index=True)
feat26=feat26.sort_values('gp').groupby('team').tail(1)
s25i=s25.set_index('team')
for c in ['pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod']:
    feat26[c]=feat26.apply(lambda r: r[c] if pd.notna(r[c]) else (s25i.loc[r.team,c] if r.team in s25i.index else np.nan),axis=1)
feat26=feat26.set_index('team')
sb=json.load(open('/tmp/training/cfb/sb_raw.json'))
board=[]
for e in sb['events']:
    comp=e['competitions'][0]
    comps={c['homeAway']:c['team']['displayName'] for c in comp['competitors']}
    home,away=comps['home'],comps['away']
    neutral=bool(comp.get('neutralSite'))
    if home not in feat26.index or away not in feat26.index:
        board.append({'event_id':e['id'],'name':e['name'],'error':'team not in FBS corpus (FCS or new program)'}); continue
    hr=feat26.loc[home]; ar=feat26.loc[away]
    fv={}
    for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod']:
        fv['d_'+s]=float(hr[s])-float(ar[s])
    fv['d_gp']=float(hr['gp'])-float(ar['gp'])
    if any(pd.isna(list(fv.values()))):
        board.append({'event_id':e['id'],'name':e['name'],'error':'missing features'}); continue
    margin=float(model.predict(pd.DataFrame([fv])[FEATS])[0])
    board.append({'event_id':e['id'],'name':e['name'],'date':comp['date'],'away':away,'home':home,'neutral_site':neutral,
        'predicted_margin_home':round(margin,1),
        'predicted_winner':home if margin>0 else away,
        'model_home_line':round(-margin,1)})
ok=[b for b in board if 'predicted_margin_home' in b]; err=[b for b in board if 'error' in b]
print('scored',len(ok),'errors',len(err))
for b in err: print('ERR',b['name'],b['error'])
out={'schema_version':'1.0.0','generated_at':'2026-09-04T12:52:00-05:00','model':'cfb-gameline-v2 (churn+coach+draft context)','label':'MEASUREMENT ONLY - not picks. Model has not been tested against book lines. Totals side is a null and is omitted.','slate_date':'2026-09-05','games':ok,'errors':err}
(OUT/'cfb_board_2026-09-05_v2.json').write_text(json.dumps(out,indent=1))
print(json.dumps(ok[:3],indent=1))
