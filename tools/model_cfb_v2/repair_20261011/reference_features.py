#!/usr/bin/env python3
"""Week 6 initial pregame scorer, after all Week 5 results. Preserves prior boards.
Model v2.2 uses validated AP points, point-in-time historical fit, and outcome-null
as-of rows to include each 2026 team latest completed game. Book display only.
"""
import numpy as np, pandas as pd, json, glob, sys, html, re, urllib.request, copy
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPO=Path(sys.argv[1]); OUT=Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
BOOK_CSV=Path(sys.argv[3]) if len(sys.argv)>3 else None          # e.g. tools/ledger/9-cfb_week1_fanduel_tn_*.csv
BOOK_LABEL=sys.argv[4] if len(sys.argv)>4 else None              # e.g. 'FanDuel Tennessee, captured Sat 2026-09-05 ~6:25 AM CT'
BOOK_STATE=sys.argv[5] if len(sys.argv)>5 else 'VA'
ESPN=REPO/'tools/espn'; MV2=REPO/'tools/model_cfb_v2'
SLATE_DATES=['20261006','20261007','20261008','20261009','20261010','20261011','20261012']

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

# ---- 2026 finals rows from repo boxscores (ESPN summary JSON) ----
rows=[]; skipped=[]
for f in sorted((REPO/'tools/cfb/boxscores').glob('*.json')):
    try:
        inner=json.load(open(f))
        ev=f.name.rsplit('-',1)[-1].split('.json')[0]
        hd=inner['header']['competitions'][0]; date=hd['date'][:10]
        if not hd['status']['type']['completed']: raise ValueError('Nonfinal boxscore cannot enter features')
        if pd.Timestamp(hd['date']) >= pd.Timestamp('2026-10-12T02:40:00Z'): raise ValueError('Beyond locked repair as-of')
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
                            cmp_,att=v.get('completions/passingAttempts',v.get('completions/attempts','')).split('/')
                            a=qbs.setdefault(tm,[0,0,0,0,0]); a[0]+=float(cmp_); a[1]+=float(att); a[2]+=float(v.get('passingYards',v.get('yards',0))); a[3]+=float(v.get('passingTouchdowns',v.get('touchdowns',0))); a[4]+=float(v['interceptions'])
                        except: pass
        teams=inner['boxscore']['teams']
        for t in teams:
            tm=t['team']['displayName']; opp=[x['team']['displayName'] for x in teams if x['team']['displayName']!=tm][0]
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
    except Exception as e:
        skipped.append((f.name,str(e)))
print('2026 finals rows:',len(rows),'skipped:',skipped)
d26=pd.DataFrame(rows)
m=d26.set_index(['event_id','team'])
for i,r in d26.iterrows():
    o=m.loc[(r.event_id,r.opponent)]
    d26.loc[i,['pass_yds_allowed','rush_yds_allowed','total_yds_allowed']]=o[['pass_yds_for','rush_yds_for','total_yds_for']].values
    d26.loc[i,'turnovers_forced']=o['turnovers_lost']
d26['date']=pd.to_datetime(d26['date'])
tg=pd.concat([tg,d26.drop(columns=['turnovers_lost'])],ignore_index=True)
# As-of scoring rows for each 2026 team. A completed game's feature row is
# pregame (shifted); using that row as the scoring lookup silently omits the
# game's statistics. Synthetic rows shift through every completed game, have
# no outcome, and never join the historical training games by event_id.
last_completed=tg[tg.season==2026].sort_values('date').groupby('team').tail(1).copy()
last_completed['event_id']='__ASOF__'+last_completed['team'].astype(str)
last_completed['date']=pd.Timestamp('2026-10-12')
last_completed['home_away']='asof'
for c in ['points_for','points_allowed','pass_yds_for','pass_yds_allowed','rush_yds_for','rush_yds_allowed','total_yds_for','total_yds_allowed','turnovers_forced','qb_cmp_pct','qb_yds','qb_td','qb_int']:
    last_completed[c]=np.nan
tg=pd.concat([tg,last_completed],ignore_index=True)
tg=tg.sort_values(['team','season','date']).reset_index(drop=True)

# ---- v2 context features ----
churn_hist=pd.read_csv(MV2/'features_churn_2021_2025.csv')
churn26=pd.read_csv(MV2/'churn_2026.csv'); churn26['season']=2026
churn=pd.concat([churn_hist,churn26],ignore_index=True)
tg=tg.merge(churn[['team','season','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']],on=['team','season'],how='left')
_cflags=json.load(open(MV2/'coach_flags.json'))
_dd=pd.read_csv(MV2/'features_draft_losses.csv')
tg=tg.merge(_dd[['team','season','drafted_prod']],on=['team','season'],how='left')
tg['new_coach']=tg.apply(lambda r: _cflags.get(f"{r['team']}|{r['season']}",0),axis=1)

# ---- 247Sports team talent composite (preseason-published; FCS/missing imputed at season FBS floor) ----
_tal=pd.read_csv(MV2/'talent_composite.csv')
tg=tg.merge(_tal[['team','season','talent']],on=['team','season'],how='left')
tg=tg.merge(_tal.groupby('season')['talent'].min().rename('_talfloor'),on='season',how='left')
tg['talent']=tg['talent'].fillna(tg['_talfloor']).fillna(_tal.talent.min())

# ---- AP poll points feature (validated Sunday experiment; point-in-time, strictly pre-kickoff) ----
# Historical polls are fetched from ESPN Core's free year/week archive and selected by poll date < game date.
# Unranked teams are zero. Week 6 uses the archived Oct 4 AP poll.
import urllib.error
AP_CACHE=Path('/tmp/cfb_ap_poll_cache'); AP_CACHE.mkdir(exist_ok=True)
def _ap_poll(year, week):
    cp=AP_CACHE/f'ap-{year}-week{week}.json'
    if cp.exists(): return json.load(open(cp))
    u=f'https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/types/2/weeks/{week}/rankings/1?lang=en&region=us'
    try:
        d=fetch(u) if 'fetch' in globals() else json.loads(urllib.request.urlopen(u,timeout=30).read())
        cp.write_text(json.dumps(d))
        return d
    except Exception:
        return None
ap_snapshots={}
ap_team_cache={}
def ap_team_name(t):
    # Newer site payloads embed the team; historical Core payloads provide a stable ref.
    if t.get('displayName'): return t['displayName']
    if t.get('location') and t.get('name'): return f"{t['location']} {t['name']}"
    ref=t.get('$ref')
    if not ref: return None
    if ref not in ap_team_cache:
        cp=AP_CACHE/('team-'+ref.rstrip('/').split('/')[-1].split('?')[0]+'.json')
        if cp.exists(): td=json.load(open(cp))
        else:
            td=json.loads(urllib.request.urlopen(ref.replace('http://','https://'),timeout=30).read()); cp.write_text(json.dumps(td))
        ap_team_cache[ref]=td.get('displayName') or ((td.get('location','')+' '+td.get('name','')).strip())
    return ap_team_cache[ref]
for yr in range(2020,2026):
    snaps=[]
    for wk in range(1,17):
        d=_ap_poll(yr,wk)
        if d and d.get('date') and d.get('ranks'):
            vals={ap_team_name(r['team']):float(r.get('points') or 0) for r in d['ranks']}
            snaps.append((pd.Timestamp(d['date']).tz_convert(None), {k:v for k,v in vals.items() if k}))
    ap_snapshots[yr]=sorted(snaps)
cur=json.load(open(MV2/'ap_poll/ap-2026-week6.json'))
cur_ap=next(p for p in cur['rankings'] if p.get('type')=='ap')
ap_snapshots[2026]=[]
for cp in sorted((MV2/'ap_poll').glob('ap-2026-week*.json')):
    poll=next(p for p in json.load(open(cp))['rankings'] if p.get('type')=='ap')
    # Release timestamp verified on primary AP article for newest poll. Older archived
    # polls use conservative date+18:00 UTC; same-day games never use that poll.
    release=pd.Timestamp(poll['date']).normalize()+pd.Timedelta(hours=18)
    ap_snapshots[2026].append((release.tz_convert(None),{ap_team_name(z['team']):float(z.get('points') or 0) for z in poll['ranks']}))
ap_snapshots[2026]=sorted(ap_snapshots[2026])
def ap_points(team, season, date):
    ds=pd.Timestamp(date).tz_localize(None)
    eligible=[x for x in ap_snapshots.get(int(season),[]) if x[0] < ds]
    return eligible[-1][1].get(team,0.0) if eligible else 0.0
tg['ap_points']=tg.apply(lambda r: ap_points(r['team'],r['season'],r['date']),axis=1)

# ---- features identical to score_v2.py ----
prior=tg[tg.season<=2025].groupby(['team','season'],as_index=False).agg(
    ps_pf=('points_for','mean'),ps_pa=('points_allowed','mean'),ps_yf=('total_yds_for','mean'),ps_ya=('total_yds_allowed','mean'))
prior['season']+=1
prior=prior.rename(columns={c:'prior_'+c.split('_',1)[1] for c in ['ps_pf','ps_pa','ps_yf','ps_ya']})
tg=tg.merge(prior,on=['team','season'],how='left')
lg=tg[tg.season<=2025].groupby('season')[['points_for','points_allowed','total_yds_for','total_yds_allowed']].mean()
lg2025=lg.loc[2025]
for c,src in [('prior_pf','points_for'),('prior_pa','points_allowed'),('prior_yf','total_yds_for'),('prior_ya','total_yds_allowed')]:
    tg[c]=tg[c].fillna(lg2025[src])
g=tg.groupby(['team','season'],group_keys=False)
for c,new in [('points_for','pf'),('points_allowed','pa'),('total_yds_for','yf'),('total_yds_allowed','ya'),
              ('pass_yds_for','pyf'),('pass_yds_allowed','pya'),('rush_yds_for','ryf'),('rush_yds_allowed','rya'),
              ('turnovers_forced','tof'),('qb_cmp_pct','qbc'),('qb_yds','qby'),('qb_td','qbtd'),('qb_int','qbi')]:
    tg[new+'_r4']=g[c].transform(lambda x:x.shift().rolling(4,min_periods=1).mean())
tg['gp']=g['date'].transform(lambda x:x.shift().rolling(100,min_periods=1).count()).fillna(0)
w=(tg.gp/(tg.gp+2)).clip(0,1)
for b,cols in [('pf',('prior_pf','pf_r4')),('pa',('prior_pa','pa_r4')),('yf',('prior_yf','yf_r4')),('ya',('prior_ya','ya_r4'))]:
    tg[b+'_f']=w*tg[cols[1]].fillna(tg[cols[0]])+(1-w)*tg[cols[0]]

# Add final 2026 game outcomes, keyed exactly once by provider event id.
newgames=[]
for fp in sorted((REPO/'tools/cfb/boxscores').glob('*.json')):
    d=json.load(open(fp)); c=d['header']['competitions'][0]
    if not c['status']['type']['completed']: continue
    teams={z['homeAway']:z for z in c['competitors']}
    newgames.append({'event_id':str(d['header']['id']),'season':2026,'date':pd.Timestamp(c['date']).tz_convert(None),'home_score':float(teams['home']['score']),'away_score':float(teams['away']['score']),'completed':True,'margin':float(teams['home']['score'])-float(teams['away']['score'])})
games['event_id']=games.event_id.astype(str); tg['event_id']=tg.event_id.astype(str)
games['date']=pd.to_datetime(games.date,utc=True).dt.tz_localize(None)
games=pd.concat([games,pd.DataFrame(newgames)],ignore_index=True).drop_duplicates('event_id',keep='first')
assert not games.event_id.duplicated().any()
for target,source in [('pyf_r4','pass_yds_for'),('pya_r4','pass_yds_allowed'),('ryf_r4','rush_yds_for'),('rya_r4','rush_yds_allowed'),('tof_r4','turnovers_forced'),('qbc_r4','qb_cmp_pct'),('qby_r4','qb_yds'),('qbtd_r4','qb_td'),('qbi_r4','qb_int')]:
    prior_known=tg[(tg.season==2025)&(tg.home_away!='asof')].groupby('team')[source].mean()
    ix=tg.season==2026
    tg.loc[ix,target]=tg.loc[ix,target].fillna(tg.loc[ix,'team'].map(prior_known))
h=tg[tg.home_away=='home'].set_index('event_id'); a=tg[tg.home_away=='away'].set_index('event_id')
JC=['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','gp','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']
gm=games.set_index('event_id').join(h[JC].add_prefix('h_'),how='inner').join(a[JC].add_prefix('a_'),how='inner').reset_index()
FEATS=[]
for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; FEATS.append('d_'+s)
gm['d_gp']=gm.h_gp-gm.a_gp; FEATS.append('d_gp')
members=set(json.load(open(MV2/'national_rank_variant/fbs-names.json'))['2026'])
gm=gm[(gm.season!=2026)|(gm.h_team.isin(members)&gm.a_team.isin(members))]
hist=gm.dropna(subset=FEATS+['margin'])
model=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(hist[FEATS],hist.margin)
print('refit rows',len(hist))
# Diagnostic: verify the synthetic row is one completed game ahead of the
# pregame feature for representative teams, and is absent from fit rows.
assert not gm.event_id.astype(str).str.startswith('__ASOF__').any()
for test_team in ['Liberty Flames','Coastal Carolina Chanticleers','Utah Utes','Nebraska Cornhuskers','Georgia Bulldogs','Tennessee Volunteers']:
    tr=tg[(tg.team==test_team)&(tg.season==2026)].sort_values('date')
    actual=tr[tr.home_away!='asof']
    pseudo=tr[tr.home_away=='asof']
    if len(actual) and len(pseudo):
        latest=actual.iloc[-1]; post=pseudo.iloc[0]
        print('asof-check',test_team,'played',len(actual),'pregame_gp',latest.gp,'post_gp',post.gp,
              'pregame_pf',round(latest.pf_f,3),'post_pf',round(post.pf_f,3),
              'last_pf',latest.points_for)
        assert int(post.gp)==len(actual) and int(latest.gp)==len(actual)-1
        assert np.isclose(post.pf_r4,actual.tail(4).points_for.mean())


# ---- 2026 feature lookup (same imputation as score_v2.py) ----
r4cols=['pyf','pya','ryf','rya','tof','qbc','qby','qbtd','qbi']
extra26=churn26.set_index('team')[['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret']]
s25=tg[tg.season==2025].groupby('team').agg(
    prior_pf=('points_for','mean'),prior_pa=('points_allowed','mean'),
    prior_yf=('total_yds_for','mean'),prior_ya=('total_yds_allowed','mean'),talent=('talent','mean'),
    **{c+'_r4':({'pyf':'pass_yds_for','pya':'pass_yds_allowed','ryf':'rush_yds_for','rya':'rush_yds_allowed','tof':'turnovers_forced','qbc':'qb_cmp_pct','qby':'qb_yds','qbtd':'qb_td','qbi':'qb_int'}[c],'mean') for c in r4cols}).reset_index()
s25['pf_f']=s25.prior_pf; s25['pa_f']=s25.prior_pa; s25['yf_f']=s25.prior_yf; s25['ya_f']=s25.prior_ya; s25['gp']=0.0
s25=s25.merge(extra26.reset_index(),on='team',how='left')
s25['new_coach']=s25.team.map(lambda t: _cflags.get(f'{t}|2026',0))
_dd26=_dd[_dd.season==2026].set_index('team')['drafted_prod']
s25['drafted_prod']=s25.team.map(_dd26).fillna(0)
s25['ap_points']=s25.team.map(ap_snapshots[2026][-1][1]).fillna(0)
last26=tg[tg.season==2026].sort_values('date').groupby('team').tail(1)[['team']+['pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['gp','talent']]
last26=last26.merge(extra26.reset_index(),on='team',how='left')
last26['new_coach']=last26.team.map(lambda t: _cflags.get(f'{t}|2026',0))
last26['drafted_prod']=last26.team.map(_dd26).fillna(0)
last26['ap_points']=last26.team.map(ap_snapshots[2026][-1][1]).fillna(0)
feat26=pd.concat([s25[['team','pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['gp','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']],last26],ignore_index=True)
feat26=feat26.sort_values('gp').groupby('team').tail(1)
s25i=s25.set_index('team')
for c in ['pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']:
    feat26[c]=feat26.apply(lambda r: r[c] if pd.notna(r[c]) else (s25i.loc[r.team,c] if r.team in s25i.index else np.nan),axis=1)
feat26=feat26.set_index('team')

