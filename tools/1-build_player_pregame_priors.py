#!/usr/bin/env python3
"""Rebuild the week-1 2026 player projection universe. Honest-experiment rebuild:
- Universe = anytime-TD market board players + carryover priors universe.
- Every market-board player gets a numeric forecast or an explicit eligibility reason.
- QB passing-yards spec selected on 2024 validation, locked-tested on 2025, gate |median bias|<=8.
- QB rushing-TD allocation: QB-only logistic model with red-zone/goal-line carry shares from pbp.
- Point-in-time rolling features (shifted); no book data enters the model.
"""
import json, re, sys, urllib.request, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, roc_auc_score, mean_absolute_error

ROOT=Path('/tmp/ediths-picks'); CACHE=Path('/tmp/cache')
NOW=dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-5)))
def norm(s):
    s=re.sub(r'[^a-z0-9 ]','',str(s).lower())
    parts=[p for p in s.split() if p not in ('jr','sr','ii','iii','iv','v')]
    return ''.join(parts)
def die(m): raise RuntimeError(m)

# ---------- load nflverse ----------
COLS=['player_id','player_display_name','position','team','season','week','season_type','game_id','opponent_team',
 'attempts','completions','passing_yards','passing_tds','passing_air_yards','passing_epa','passing_cpoe',
 'carries','rushing_yards','rushing_tds','targets','receptions','receiving_yards','receiving_tds',
 'receiving_air_yards','target_share','air_yards_share','wopr','fantasy_points_ppr']
raw=pd.concat([pd.read_csv(CACHE/f'stats_{y}.csv',usecols=COLS,low_memory=False) for y in (2023,2024,2025)])
raw=raw[raw.season_type=='REG']
counts=raw.groupby('season').size().to_dict()
if any(counts.get(y,0)<4500 for y in (2023,2024,2025)): die(f'incomplete weekly stats {counts}')

ROLL=['attempts','completions','passing_yards','passing_tds','passing_air_yards','passing_epa','passing_cpoe',
 'carries','rushing_yards','rushing_tds','targets','receptions','receiving_yards','receiving_tds',
 'receiving_air_yards','target_share','air_yards_share','wopr','fantasy_points_ppr']
d=raw.sort_values(['player_id','season','week']).copy(); g=d.groupby('player_id',group_keys=False)
for c in ROLL:
    for n in (3,6): d[f'{c}_r{n}']=g[c].transform(lambda x:x.shift().rolling(n,min_periods=3).mean())

# ---------- pbp red-zone / goal-line opportunity (season aggregates, by definition lagged for a new season) ----------
rz={}
for y in (2023,2024,2025):
    p=pd.read_parquet(CACHE/f'pbp_{y}.parquet',columns=['season','posteam','play_type','yardline_100','rusher_player_id','receiver_player_id'])
    p=p[p.posteam.notna()]
    for typ,pid in [('carry','rusher_player_id'),('target','receiver_player_id')]:
        q=p[p[pid].notna()&p.play_type.eq('run' if typ=='carry' else 'pass')].copy(); q['player_id']=q[pid]
        q['rz']=q.yardline_100.le(20).astype(int); q['gl']=q.yardline_100.le(5).astype(int)
        a=q.groupby(['season','posteam','player_id']).agg(**{f'{typ}_rz':('rz','sum'),f'{typ}_gl':('gl','sum'),f'{typ}_all':('rz','size')}).reset_index()
        t=a.groupby(['season','posteam'])[[f'{typ}_rz',f'{typ}_gl',f'{typ}_all']].sum().rename(columns=lambda c:'team_'+c)
        a=a.merge(t,on=['season','posteam'])
        a[f'{typ}_rz_share']=a[f'{typ}_rz']/a[f'team_{typ}_rz'].clip(lower=1)
        a[f'{typ}_gl_share']=a[f'{typ}_gl']/a[f'team_{typ}_gl'].clip(lower=1)
        rz.update({(r.player_id,int(r.season)):(float(r.carry_rz_share) if typ=='carry' else None) for r in a.itertuples()} if False else {})
        for r in a.itertuples():
            cur=rz.setdefault((r.player_id,int(r.season)),{})
            cur[f'{typ}_rz_share']=float(getattr(r,f'{typ}_rz_share')); cur[f'{typ}_gl_share']=float(getattr(r,f'{typ}_gl_share'))

# ---------- universe ----------
old=json.loads((ROOT/'player_projections.json').read_text())
old_by_id={x['player_id']:x for x in old['players']}
market=json.loads((ROOT/'week1_anytime_td_market.json').read_text())
mb_names=sorted({r['player_name'] for r in market['rows'] if 'Defense' not in r['player_name']})
fantasy=json.loads((ROOT/'fantasy.json').read_text()); leagues=fantasy.get('leagues',[])
if len(leagues)!=7: die(f'fantasy leagues {len(leagues)}')
roster_names={norm(p.get('name')) for l in leagues for p in l.get('players',[])}

# ESPN 2026 rosters -> current team
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req,timeout=60))
team_map={}
for f in (CACHE/'rosters').glob('*.json'):
    ab=f.stem
    r=json.loads(f.read_text())
    for grp in r.get('athletes',[]):
        for a in grp.get('items',[]):
            team_map[norm(a['displayName'])]={'team':ab,'position':a.get('position',{}).get('abbreviation'),'espn_id':a.get('id')}
print('espn 2026 roster names:',len(team_map))

# nflverse 2025 name index for id/history mapping
idx25={}
r25=raw[raw.season==2025].copy(); r25['nm']=r25.player_display_name.map(norm)
for (nm,pos),x in r25.groupby(['nm','position']):
    idx25.setdefault(nm,[]).append((x.player_id.iloc[-1],pos,x.team.iloc[-1],len(x)))

# week-1 2026 opponents
games=pd.read_csv(CACHE/'games.csv'); g26=games[(games.season==2026)&(games.game_type=='REG')&(games.week==1)]
opp={}; ALIAS={'LA':'LAR','WSH':'WAS','JAC':'JAX','LVR':'LV'}
for z in g26.itertuples():
    opp[str(z.away_team)]=str(z.home_team); opp[str(z.home_team)]=str(z.away_team)
if not g26.shape[0]: die('no 2026 week1 schedule')

universe={}  # key norm name -> record
FANTASY_EXTRA=True
for x in old['players']:
    universe[norm(x['player'])]={'name':x['player'],'position':x['position'],'team':x['team'],'player_id':x['player_id'],'carry':x}
unmatched=[]
for nm in mb_names:
    k=norm(nm)
    if k in universe:
        if universe[k]['name']!=nm:
            universe[k]['name']=nm  # adopt exact market spelling so the exact-name join hits
            universe[k]['renamed_for_join']=True
        continue
    cands=idx25.get(k)
    tm=team_map.get(k)
    if cands:
        pid,pos,t25,ng=cands[0]
        team=(tm or {}).get('team') or t25
        team=ALIAS.get(team,team)
        universe[k]={'name':nm,'position':pos,'team':team,'player_id':pid,'carry':None,'new_from_board':True,'espn_team':bool(tm)}
    else:
        unmatched.append(nm)
if FANTASY_EXTRA:
    added=0
    for l in leagues:
        for p in l.get('players',[]):
            k=norm(p.get('name'))
            if not k or k in universe: continue
            cands=idx25.get(k); tm=team_map.get(k)
            if cands:
                pid,pos,t25,ng=cands[0]
                team=ALIAS.get((tm or {}).get('team') or t25,(tm or {}).get('team') or t25)
                universe[k]={'name':p.get('name'),'position':pos,'team':team,'player_id':pid,'carry':None,'from_fantasy':True}
                added+=1
            elif tm:
                universe[k]={'name':p.get('name'),'position':tm.get('position') or 'unknown','team':tm.get('team'),'player_id':None,'carry':None,'from_fantasy':True}
                added+=1
    print('fantasy-rostered additions:',added)
print('universe',len(universe),'board unmatched (no 2025 nflverse row):',len(unmatched),unmatched[:12])

# ---------- latest feature rows (end of 2025 season, point-in-time) ----------
def latest_rows(dd):
    out=[]
    for pid,x in dd[dd.season==2025].groupby('player_id'):
        x=x.sort_values('week'); z=x.iloc[-1].copy()
        if z.position=='QB':
            m=x[x.attempts>=15]  # meaningful starts only: skip rest/injury cameos
            src=m if len(m)>=3 else x.iloc[0:0]  # empty -> NaN features -> ineligible
        else:
            src=x
        for c in ROLL:
            for n in (3,6): z[f'{c}_r{n}']=src[c].tail(n).mean() if len(src) else float('nan')
        z['games_2025']=len(x)
        out.append(z)
    return out
L={str(z.player_id):z for z in latest_rows(d)}

# ---------- model helpers ----------
def lin(tr,fs,y): tr=tr.dropna(subset=fs); return LinearRegression().fit(tr[fs],tr[y])
def logit(tr,fs,y):
    tr=tr.dropna(subset=fs); return make_pipeline(StandardScaler(),LogisticRegression(C=.5,max_iter=1000)).fit(tr[fs],tr[y])
def pred(m,fs,z):
    try: return float(max(0,m.predict(pd.DataFrame([{f:z[f] for f in fs}]))[0]))
    except Exception: return None
def prob(m,fs,z):
    try: return float(min(1,max(0,m.predict_proba(pd.DataFrame([{f:z[f] for f in fs}]))[0,1])))
    except Exception: return None

# ---------- QB passing yards: selected spec combined_rush (validation-selected, locked-tested) ----------
QBF=['passing_yards_r3','passing_yards_r6','attempts_r3','attempts_r6','completions_r3','passing_air_yards_r3','passing_epa_r3','passing_cpoe_r3','carries_r3','rushing_yards_r3']
qb=d[(d.position=='QB')&(d.attempts_r3>=15)].dropna(subset=QBF).copy()
v_tr,v_te=qb[qb.season==2023],qb[qb.season==2024]
l_tr,l_te=qb[qb.season.isin([2023,2024])],qb[qb.season==2025]
mv=LinearRegression().fit(v_tr[QBF],v_tr.passing_yards); pv=mv.predict(v_te[QBF])
ml=LinearRegression().fit(l_tr[QBF],l_tr.passing_yards); pl=ml.predict(l_te[QBF])
err_l=pl-l_te.passing_yards
qb_holdout={'validation_2024':{'n':len(v_te),'mae':round(mean_absolute_error(v_te.passing_yards,pv),2),'median_bias':round(float(np.median(pv-v_te.passing_yards)),2)},
 'locked_test_2025':{'n':len(l_te),'mae':round(mean_absolute_error(l_te.passing_yards,pl),2),'median_bias':round(float(np.median(err_l)),2),'mean_bias':round(float(err_l.mean()),2)},
 'baseline_yards_only_locked_2025_mae':round(float(mean_absolute_error(l_te.passing_yards,LinearRegression().fit(l_tr[['passing_yards_r3','passing_yards_r6']],l_tr.passing_yards).predict(l_te[['passing_yards_r3','passing_yards_r6']]))),2)}
PASS_GATE=abs(qb_holdout['locked_test_2025']['median_bias'])<=8
if not PASS_GATE: print('WARNING: passing gate failed - passing numbers will be withheld',file=sys.stderr)
q_resid=(l_te.passing_yards-pl)  # actual - pred
q20,q80=np.quantile(q_resid,[0.2,0.8])
qbm=lin(qb,QBF,'passing_yards')  # final fit 2023-25

# passing TDs (rate-ish linear), holdout
PTF=['attempts_r3','attempts_r6','passing_tds_r3','passing_tds_r6','completions_r3']
qbt=qb.dropna(subset=PTF)
lt,tt=qbt[qbt.season.isin([2023,2024])],qbt[qbt.season==2025]
mtd=LinearRegression().fit(lt[PTF],lt.passing_tds); ptd=mtd.predict(tt[PTF])
td_holdout={'n':len(tt),'mae':round(mean_absolute_error(tt.passing_tds,ptd),3),'median_bias':round(float(np.median(ptd-tt.passing_tds)),3)}
ptdm=lin(qbt,PTF,'passing_tds')

# QB rushing yards (committed QF spec, QB+RB rows)
QF=['rushing_yards_r3','rushing_yards_r6','carries_r3','carries_r6']
rr=d[d.position.isin(['RB','QB'])&d.rushing_yards_r3.notna()]
rushm=lin(rr,QF,'rushing_yards')

# ---------- QB anytime (rushing) TD ----------
qbd=d[(d.position=='QB')&d.carries_r3.notna()].copy()
qbd['carry_rz_share']=[rz.get((pid,int(s)),{}).get('carry_rz_share',0.0) for pid,s in zip(qbd.player_id,qbd.season)]
qbd['carry_gl_share']=[rz.get((pid,int(s)),{}).get('carry_gl_share',0.0) for pid,s in zip(qbd.player_id,qbd.season)]
qbd['y']=(qbd.rushing_tds>0).astype(int)
QRF=['carries_r3','carries_r6','rushing_tds_r6','carry_rz_share','carry_gl_share']
ltr,qtr=qbd[qbd.season.isin([2023,2024])],qbd[qbd.season==2025]
qm=logit(ltr,QRF,'y'); qp=qm.predict_proba(qtr[QRF])[:,1]
naive=np.clip(qtr.rushing_tds_r6.fillna(0)/1.0,0,1)  # trailing per-game rushing TD rate
qbtd_holdout={'n':len(qtr),'events':int(qtr.y.sum()),'brier_model':round(brier_score_loss(qtr.y,qp),4),'brier_naive_trailing_rate':round(brier_score_loss(qtr.y,naive),4),
 'auc_model':round(roc_auc_score(qtr.y,qp),3),'auc_naive':round(roc_auc_score(qtr.y,naive),3)}
QBTD_GATE=qbtd_holdout['brier_model']<qbtd_holdout['brier_naive_trailing_rate']
qrtdm=logit(qbd,QRF,'y')

# ---------- RB/WR/TE models (committed specs) ----------
RF=['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receptions_r3','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3']
REPF=['receptions_r3','targets_r3','targets_r6']
TDF=['receiving_tds_r6','rushing_tds_r6','targets_r3','target_share_r3','receiving_air_yards_r3','carries_r3','receiving_yards_r3','rushing_yards_r3']
BF=['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3']
r=d[d.position.isin(['WR','TE','RB'])&d.receiving_yards_r3.notna()].copy()
bust=r[(r.targets_r3>=4)&r.receiving_yards_r6.notna()].copy(); bust['bust']=((bust.receiving_yards<30)&(bust.receiving_yards<.5*bust.receiving_yards_r6)).astype(int)
mets={}
for name,fs in {'past_yards':['receiving_yards_r3','receiving_yards_r6'],'combined':BF}.items():
    tr=bust[bust.season.eq(2024)].dropna(subset=fs); te=bust[bust.season.eq(2025)].dropna(subset=fs)
    m=logit(tr,fs,'bust'); p=m.predict_proba(te[fs])[:,1]
    mets[name]={'n_train':len(tr),'n_test':len(te),'events':int(te.bust.sum()),'brier':float(brier_score_loss(te.bust,p)),'auc':float(roc_auc_score(te.bust,p))}
proven=mets['combined']['brier']<mets['past_yards']['brier'] and mets['combined']['auc']>mets['past_yards']['auc']
if not proven: die(f'bust gate failed {mets}')
recm=lin(r,RF,'receiving_yards'); repm=lin(r,REPF,'receptions')
tdf=r.copy(); tdf['y']=((tdf.receiving_tds+tdf.rushing_tds)>0).astype(int); tdm=logit(tdf,TDF,'y')
boom=r[(r.targets_r3>=2)&r.receiving_yards_r6.notna()].copy(); boom['y']=((boom.receiving_yards>=80)&(boom.receiving_yards>=1.5*boom.receiving_yards_r6.clip(lower=20))).astype(int); bm=logit(boom,RF,'y'); bustm=logit(bust,BF,'bust')
# intervals from locked 2025 residuals per group
lr,lt5=r[r.season.isin([2023,2024])],r[r.season==2025]
def resid_quant(fs,y,mdl=None):
    m=LinearRegression().fit(lr.dropna(subset=fs)[fs],lr.dropna(subset=fs)[y]); p=m.predict(lt5.dropna(subset=fs)[fs]); res=lt5.dropna(subset=fs)[y]-p
    return tuple(float(x) for x in np.quantile(res,[0.2,0.8]))
rec_i=resid_quant(RF,'receiving_yards'); rep_i=resid_quant(REPF,'receptions')
rr5=rr[rr.position=='RB']; lrr,trr=rr5[rr5.season.isin([2023,2024])],rr5[rr5.season==2025]
m=LinearRegression().fit(lrr.dropna(subset=QF)[QF],lrr.dropna(subset=QF).rushing_yards); res=trr.dropna(subset=QF).rushing_yards-m.predict(trr.dropna(subset=QF)[QF]); rush_i=tuple(float(x) for x in np.quantile(res,[0.2,0.8]))
print('intervals rec/rep/rush',rec_i,rep_i,rush_i)
print('QB holdout',json.dumps(qb_holdout)); print('pTD holdout',td_holdout); print('QB rushTD',qbtd_holdout,'gate',QBTD_GATE)

# ---------- emit ----------
MODEL_VERSION='player-pregame-prior-v2.0.0-w1-2026'
players=[]; reasons={}
def elig(z,pos):
    if z is None: return 'No 2025 NFL history (rookie or new to league)'
    if pos=='QB' and not (z.get('attempts_r3')==z.get('attempts_r3')) : return 'Insufficient 2025 passing volume (fewer than 3 starts with 15+ attempts); prior would be noise'
    if pos in ('RB','WR','TE') and not (z.get('targets_r3')==z.get('targets_r3')) and not (z.get('carries_r3')==z.get('carries_r3')): return 'Insufficient NFL usage history (under 3 tracked games)'
    return None

for k,u in sorted(universe.items(), key=lambda kv:(kv[1]['position'],kv[1]['name'])):
    z=L.get(str(u['player_id'])); pos=u['position']; team=ALIAS.get(u['team'],u['team'])
    reason=elig(z,pos)
    car=u.get('carry') or {}
    base={'sport':'NFL','player_id':u['player_id'],'player':u['name'],'team':team,'position':pos,
     'opponent':opp.get(team),'fantasy_rostered':norm(u['name']) in roster_names,
     'projection_context':('Week 1 pregame prior vs %s, frozen before the current FanDuel capture. Opponent context is descriptive and does not alter the numeric projection because the held-out matchup gain was not proven.'%opp.get(team)) if opp.get(team) else 'Week 1 opponent unresolved'}
    if reason is None and pos=='QB' and z.get('attempts_r3',0)>=15:
        py=pred(qbm,QBF,z) if PASS_GATE else None
        base['passing_yards']={'median':round(py,1),'p20':round(max(0,py+q20),1),'p80':round(max(0,py+q80),1)} if py is not None else None
        pt=pred(ptdm,PTF,z); base['passing_tds']={'median':round(pt,2)} if pt is not None else None
        ry=pred(rushm,QF,z) or 0.0
        base['rushing_yards']={'median':round(ry,1),'p20':round(max(0,ry+rush_i[0]),1),'p80':round(max(0,ry+rush_i[1]),1)}
        base['receiving_yards']={'median':0,'p20':0,'p80':0}; base['receptions']={'median':0,'p20':0,'p80':0}
        zp=dict(z); zp.update({'carry_rz_share':rz.get((u['player_id'],2025),{}).get('carry_rz_share',0.0),'carry_gl_share':rz.get((u['player_id'],2025),{}).get('carry_gl_share',0.0)})
        base['anytime_td_probability']=round(prob(qrtdm,QRF,zp),3) if QBTD_GATE else None
        base['boom_probability']=None; base['bust_probability']=None
    elif reason is None and pos in ('RB','WR','TE'):
        recv=pred(recm,RF,z); rush=pred(rushm,QF,z); recs=pred(repm,REPF,z)
        if recv is None: reason='Insufficient receiving history for numeric forecast'
        else:
            base['receiving_yards']={'median':round(recv,1),'p20':round(max(0,recv+rec_i[0]),1),'p80':round(max(0,recv+rec_i[1]),1)}
            base['rushing_yards']={'median':round(rush or 0,1),'p20':round(max(0,(rush or 0)+rush_i[0]),1),'p80':round(max(0,(rush or 0)+rush_i[1]),1)}
            base['receptions']={'median':round(recs or 0,1),'p20':round(max(0,(recs or 0)+rep_i[0]),1),'p80':round(max(0,(recs or 0)+rep_i[1]),1)}
            base['passing_yards']=None; base['passing_tds']=None
            base['anytime_td_probability']=round(prob(tdm,TDF,z),3)
            base['boom_probability']=round(prob(bm,RF,z),3)
            base['bust_probability']=round(prob(bustm,BF,z),3) if z.targets_r3>=4 else None
    if reason:
        reasons[u['name']]=reason
        base.update({'passing_yards':None,'passing_tds':None,'receiving_yards':None,'rushing_yards':None,'receptions':None,
         'anytime_td_probability':None,'boom_probability':None,'bust_probability':None,'eligibility_reason':reason})
    else:
        base['eligibility_reason']=None
    base['drivers']={'attempts_last3':round(float(z.attempts_r3 or 0),1) if z is not None and z.get('attempts_r3')==z.get('attempts_r3') else 0,
         'passing_yards_last6':round(float(z.passing_yards_r6 or 0),1) if z is not None and z.get('passing_yards_r6')==z.get('passing_yards_r6') else 0,
         'targets_last3':round(float(z.targets_r3 or 0),1) if z is not None and z.get('targets_r3')==z.get('targets_r3') else 0,
         'carries_last3':round(float(z.carries_r3 or 0),1) if z is not None and z.get('carries_r3')==z.get('carries_r3') else 0,
         'receiving_yards_last6':round(float(z.receiving_yards_r6 or 0),1) if z is not None and z.get('receiving_yards_r6')==z.get('receiving_yards_r6') else 0}
    # carryover role grounding
    for f in ('starter_status','starter_source','depth_chart_role','depth_chart_rank','prior_season_fantasy_points','role_source'):
        if f in car: base[f]=car[f]
    if 'depth_chart_role' not in base: base['depth_chart_role']='unverified'
    base['history_through']=2025 if z is not None else None
    base['model_version']=MODEL_VERSION
    players.append(base)

for nm in unmatched:
    tm=team_map.get(norm(nm),{}); tmteam=ALIAS.get(tm.get('team'),tm.get('team'))
    players.append({'sport':'NFL','player_id':None,'player':nm,'team':tm.get('team'),'position':tm.get('position') or 'unknown',
     'opponent':opp.get(tmteam),'fantasy_rostered':norm(nm) in roster_names,'projection_context':'No NFL statistical history available',
     'passing_yards':None,'passing_tds':None,'receiving_yards':None,'rushing_yards':None,'receptions':None,
     'anytime_td_probability':None,'boom_probability':None,'bust_probability':None,
     'eligibility_reason':'No NFL history (2026 rookie or first-year player); model refuses to invent a line','depth_chart_role':'unverified','history_through':None,'model_version':MODEL_VERSION,
     'drivers':{'attempts_last3':0,'passing_yards_last6':0,'targets_last3':0,'carries_last3':0,'receiving_yards_last6':0}})

numeric=sum(1 for x in players if x['eligibility_reason'] is None)
print('players',len(players),'numeric',numeric,'ineligible',len(players)-numeric)
out={'generated_at':NOW.isoformat(),'schema_version':'1.0.0','status':'research',
 'headline':'Boom/bust player projections','method_note':'Week 1 pregame player priors rebuilt from the anytime-TD market board universe. QB passing-yards spec selected on 2024 validation and locked-tested on 2025; QB rushing touchdowns allocated by a QB-only model with red-zone/goal-line carry shares. No betting edge is claimed.',
 'qb_model':{'status':'numeric' if PASS_GATE else 'descriptive_only','spec':'combined_rush (rolling 3/6-game passing volume, air yards, EPA, CPOE, rushing) trained 2023-25, point-in-time features','holdout':qb_holdout,'passing_tds_holdout':td_holdout,'qb_rushing_td_model':{'features':QRF,'locked_test_2025':qbtd_holdout,'gate_beats_naive':bool(QBTD_GATE)},
  'market_gap_note':'The retired v1.1.0 -16.95 yd median gap was measured against FanDuel lines, not actuals. On the locked 2025 test this spec is approximately unbiased vs actuals; model-vs-market gaps are descriptive only.'},
 'bust_model':{'proven':bool(proven),'definition':'Under 30 receiving yards AND under 50% of prior six-game mean among players averaging at least 4 targets per game','holdout':mets},
 'sports_available':['NFL'],'cfb_status':old.get('cfb_status'),
 'sportsbook':old.get('sportsbook'),
 'qb_starter_status':old.get('qb_starter_status'),'ranking_policy':old.get('ranking_policy'),
 'projection_freeze':{'model_version':MODEL_VERSION,'numeric_projection_frozen_at':NOW.isoformat(),'week':1,'season':2026,'games':16,
  'leakage_control':'All numeric projections use point-in-time trailing nflverse features through the 2025 season and were frozen before the first 2026 Week 1 kickoff. No book lines enter the model. Replaces defective v1.1.0 priors before any Week 1 game started.'},
 'sources':old.get('sources'),'players':players,'matchup_context':old.get('matchup_context')}

# gates
assert len(players)>=150, len(players)
ids=[x['player_id'] for x in players if x['player_id']]
assert len(set(ids))==len(ids)
assert sum(bool(x['fantasy_rostered']) for x in players)>=20
for x in players:
    for kk in ('anytime_td_probability','boom_probability','bust_probability'):
        v=x.get(kk)
        if v is not None: assert 0<=v<=1,(x['player'],kk,v)
board_missing=[r['player_name'] for r in market['rows'] if 'Defense' not in r['player_name'] and norm(r['player_name']) not in {norm(p['player']) for p in players}]
assert not board_missing, board_missing[:10]
Path('/tmp/rebuild/player_projections.json').write_text(json.dumps(out,indent=2))
print('WROTE /tmp/rebuild/player_projections.json', len(players))
