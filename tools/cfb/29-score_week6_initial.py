#!/usr/bin/env python3
"""Week 6 initial pregame scorer, after all Week 5 results. Preserves prior boards.
Model v2.2 uses validated AP points, point-in-time historical fit, and outcome-null
as-of rows to include each 2026 team latest completed game. Book display only.
"""
import numpy as np, pandas as pd, json, glob, sys, html, re, urllib.request
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
last_completed['date']=pd.Timestamp('2026-10-05')
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
ap_snapshots[2026]=[(pd.Timestamp(cur_ap['date']).tz_convert(None), {ap_team_name(r['team']):float(r.get('points') or 0) for r in cur_ap['ranks']})]
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

h=tg[tg.home_away=='home'].set_index('event_id'); a=tg[tg.home_away=='away'].set_index('event_id')
JC=['team','pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','gp','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']
gm=games.set_index('event_id').join(h[JC].add_prefix('h_'),how='inner').join(a[JC].add_prefix('a_'),how='inner').reset_index()
FEATS=[]
for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']:
    gm['d_'+s]=gm['h_'+s]-gm['a_'+s]; FEATS.append('d_'+s)
gm['d_gp']=gm.h_gp-gm.a_gp; FEATS.append('d_gp')
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
s25['ap_points']=s25.team.map(ap_snapshots[2026][0][1]).fillna(0)
last26=tg[tg.season==2026].sort_values('date').groupby('team').tail(1)[['team']+['pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['gp','talent']]
last26=last26.merge(extra26.reset_index(),on='team',how='left')
last26['new_coach']=last26.team.map(lambda t: _cflags.get(f'{t}|2026',0))
last26['drafted_prod']=last26.team.map(_dd26).fillna(0)
last26['ap_points']=last26.team.map(ap_snapshots[2026][0][1]).fillna(0)
feat26=pd.concat([s25[['team','pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['gp','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']],last26],ignore_index=True)
feat26=feat26.sort_values('gp').groupby('team').tail(1)
s25i=s25.set_index('team')
for c in ['pf_f','pa_f','yf_f','ya_f']+[c+'_r4' for c in r4cols]+['ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']:
    feat26[c]=feat26.apply(lambda r: r[c] if pd.notna(r[c]) else (s25i.loc[r.team,c] if r.team in s25i.index else np.nan),axis=1)
feat26=feat26.set_index('team')

# ---- Week 6 full slate from ESPN scoreboards ----
def fetch(u):
    import subprocess, time
    for attempt in range(3):
        r=subprocess.run(['curl','-fsSL','--max-time','30',u],capture_output=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(3)
    raise RuntimeError('fetch failed: '+u)
events={}
for d in SLATE_DATES:
    sb=fetch(f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={d}&groups=80&limit=400')
    for e in sb.get('events',[]): events[e['id']]=e
print('slate events:',len(events))
assert len(events)>=50 and all(e['status']['type']['state']=='pre' for e in events.values()), 'Week 6 slate incomplete or started; pause scoring'
board=[]; errs=[]
for eid,e in events.items():
    comp=e['competitions'][0]
    comps={c['homeAway']:c['team']['displayName'] for c in comp['competitors']}
    home,away=comps['home'],comps['away']
    neutral=bool(comp.get('neutralSite'))
    if home not in feat26.index or away not in feat26.index:
        errs.append({'event_id':eid,'name':e['name'],'date':comp['date'],'error':'team not in validated FBS corpus (FCS or new program)','week':6}); continue
    hr=feat26.loc[home]; ar=feat26.loc[away]
    fv={}
    for ss in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','tof_r4','qbc_r4','qby_r4','qbtd_r4','qbi_r4','ret_share','portal_out_share','gone_share','portal_in_yds','qb_ret','new_coach','drafted_prod','talent','ap_points']:
        fv['d_'+ss]=float(hr[ss])-float(ar[ss])
    fv['d_gp']=float(hr['gp'])-float(ar['gp'])
    if any(pd.isna(list(fv.values()))):
        errs.append({'event_id':eid,'name':e['name'],'date':comp['date'],'error':'missing features','week':6}); continue
    margin=float(model.predict(pd.DataFrame([fv])[FEATS])[0])
    board.append({'event_id':eid,'name':e['name'],'date':comp['date'],'away':away,'home':home,'neutral_site':neutral,
        'timing':'pregame','frozen_initial':False,
        'timing_note':'Week 6 pregame model score as of Oct 4 after all Week 5 FBS results; availability is a documented null feature, with no invented injury adjustment.',
        'predicted_margin_home':round(margin,1),'predicted_winner':home if margin>0 else away,
        'model_home_line':round(-margin,1)})
board.sort(key=lambda b:b['date'])
ok=board
print('scored',len(ok),'errors',len(errs))
assert len(ok)+len(errs)==len(events)
assert len(ok)>40
for b in ok: b['week']=6

# ---- optional current book capture (e.g. FanDuel TN) ----
FD_ALIAS={'miami florida':'miami hurricanes','san jose state':'san josé state','wv mountaineers':'west virginia','connecticut':'uconn','miami ohio':'miami (oh)','app state':'appalachian state',
 'appalachian state':'app state','nicholls state':'nicholls','southeast louisiana':'se louisiana',
 'sam houston state':'sam houston','fiu':'florida international','louisiana':"louisiana ragin' cajuns",'hawaii':"hawai'i",'gardner webb':'gardnerwebb'}
def norm(x):
    import re as _re
    return _re.sub(r'[^a-z0-9 ]','',x.lower()).strip()
def fd_match_team(fd_name, espn_name):
    f=norm(FD_ALIAS.get(norm(fd_name), fd_name)); e=norm(espn_name)
    ft=set(f.split()); et=set(e.split())
    return ft and ft<=et
book_rows=[]
if BOOK_CSV and BOOK_CSV.exists():
    import csv as _csv
    book_rows=list(_csv.DictReader(open(BOOK_CSV)))
    print('book rows loaded:', len(book_rows))
matched=0
for b in ok:
    bdt=datetime.fromisoformat(b['date'].replace('Z','+00:00'))
    best=None
    for r in book_rows:
        rdt=datetime.fromisoformat(r['kickoff'].replace('Z','+00:00'))
        if abs((rdt-bdt).total_seconds())>18*3600: continue
        if fd_match_team(r['away'], b['away']) and fd_match_team(r['home'], b['home']):
            best=r; break
    if best and (best['home_spread'] or best['total']):
        matched+=1
        b['book_tn']={'state':(best.get('state') or BOOK_STATE),'captured_at':best['captured_at'],
            'away_spread':float(best['away_spread']) if best['away_spread'] else None,
            'away_spread_odds':int(best['away_spread_odds']) if best['away_spread_odds'] else None,
            'home_spread':float(best['home_spread']) if best['home_spread'] else None,
            'home_spread_odds':int(best['home_spread_odds']) if best['home_spread_odds'] else None,
            'total':float(best['total']) if best['total'] else None,
            'over_odds':int(best['over_odds']) if best['over_odds'] else None,
            'under_odds':int(best['under_odds']) if best['under_odds'] else None,
            'away_ml':int(best['away_ml']) if best['away_ml'] and best['away_ml']!='None' else None,
            'home_ml':int(best['home_ml']) if best['home_ml'] and best['home_ml']!='None' else None}
# Do not carry prior-week quotes forward. A Week 6 quote must be captured for its actual event.
print('book matched to board:', matched, 'fallback:',sum(1 for b in ok if b.get('book_tn') and b['book_tn']['state']=='TN'))


now_ct=datetime.now(ZoneInfo('America/Chicago'))
gen=now_ct.strftime('%Y-%m-%dT%H:%M:%S%z')
out={'schema_version':'1.1.0','generated_at':gen,
 'model':'cfb-gameline-v2.2 (validated AP points, synthetic as-of rows)',
 'label':'MEASUREMENT ONLY - not picks. Week 6 FBS model margins vs jurisdiction-labeled FanDuel comparison where matched. Unmatched book lines are null. No model totals. Model not proven against book lines.',
 'window':'2026-10-06..2026-10-12 (Week 6, FBS)',
 'notes':['Week 6 initial pregame scores generated Oct 4 after 59 Week 5 games were final. Boxscores archived separately. As-of rows advance every 2026 team through its latest final. No retrospective changes to frozen Week 5 predictions.',
  'Book lines are comparison only, never model inputs. No current Week 6 capture is attached to this run.',
  'AP points feature validated on historical 2024 validation and 2025 locked test. Current Oct 4 AP Top 25 poll (Week 6) is archived from ESPN and published before Week 6 kickoff. Unranked is zero.',
  'Historical injury feature is null. No unsourced point adjustment was made.'],
 'sources':{'ap':'https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings',
            'scoreboard':'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=20261010&groups=80&limit=400'},
 'book_capture':{'file':str(BOOK_CSV.name) if BOOK_CSV else None,'label':BOOK_LABEL,'state':BOOK_STATE,'matched':matched},
 'games':ok,'errors':errs}
(OUT/'29-cfb_board_2026_week6_initial_v2_2.json').write_text(json.dumps(out,indent=1))

# ---- board page ----
def et(iso):
    return datetime.fromisoformat(iso.replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York'))
def et_time(dt): return dt.strftime('%a %-I:%M%p ET')
def et_day(dt): return dt.strftime('%A, %b %-d').upper()
def fmt_spread(x):
    if x is None: return 'EVEN'
    return ('+' if x>0 else '')+str(x)
def odds(x): return 'EVEN' if x is None else ('+'+str(x) if x>0 else str(x))
esc=lambda s: html.escape(str(s))

from collections import defaultdict
# ---- graded-slate results blocks (rendered when tools/cfb/*_results.json exists for a slate date) ----
RESULTS={}
for rf in sorted((REPO/'tools/cfb').glob('*_results.json')):
    try:
        r=json.load(open(rf)); r['_file']=rf.name; RESULTS[r.get('slate_date')]=r
    except Exception: pass
sec=defaultdict(list); last_day=None
for b in ok:
    away,home,margin=b['away'],b['home'],b['predicted_margin_home']
    fav=home if margin>0 else away
    display_margin=round(abs(float(margin))*2)/2
    display_margin_text=f'{display_margin:.0f}' if display_margin.is_integer() else f'{display_margin:.1f}'
    ml=f"{fav} -{display_margin_text}"
    bv=b.get('book_tn') or b.get('book_va')
    bv_state=(b['book_tn'].get('state') or 'TN') if b.get('book_tn') else ('VA' if b.get('book_va') else '')
    dt=et(b['date'])
    day=et_day(dt)
    if day!=last_day:
        sec[b['week']].append(f'<div class=day-label>{day}</div>'); last_day=day
        rk=dt.date().isoformat()
        if rk in RESULTS:
            r=RESULTS[rk]; v=r['v2']; ats=v['ats_vs_tn_closing']; sbs=r.get('v1_side_by_side')
            sbs_txt=(f" v1 side-by-side: MAE {sbs['mae']}, winner {sbs['winner_correct']}/{r['games_graded']} - {esc(sbs['note'])}" if sbs else '')
            sec[b['week']].append(
              f"<div class=note-card><b>Saturday results</b> - frozen v2 numbers vs finals ({r['games_graded']} games): winner {v['winner_correct']}/{r['games_graded']} ({v['winner_accuracy']*100:.1f}%) - MAE {v['mae']:.1f} pts - RMSE {v['rmse']:.1f} - ATS vs TN closing {ats['wins']}-{ats['losses']} of {ats['graded']} graded.{sbs_txt} {esc(r['honest_read'])} <a href=\"https://github.com/Garrettwalker1/ediths-picks/blob/main/tools/cfb/{r['_file']}\">Full results JSON</a></div>")
    chips=[]
    if b.get('neutral_site'): chips.append('<span class="chip chip-muted">NEUTRAL</span>')
    if b['timing']=='post_kickoff': chips.append('<span class="chip chip-flag">POST-KICKOFF</span>')
    elif b.get('frozen_initial'): chips.append('<span class="chip chip-muted">ORIGINAL PREGAME</span>')
    else: chips.append('<span class="chip chip-neutral">INITIAL OCT 4</span>')
    if bv and bv.get('home_spread') is not None:
        hs=bv['home_spread']
        _as=bv.get('away_spread'); _fav=home if (_as is None or hs<_as) else (away if _as<hs else None); _fv=hs if _fav==home else (_as if _fav==away else 0)
        bk=f"{esc(_fav)} -{abs(_fv):g}" if _fav else f"{esc(home)} PK"
        table=(f"<table><tr><th></th><th>Spread</th><th>Total</th><th>Moneyline</th></tr>"
          f"<tr><td>{esc(away)}</td><td>{fmt_spread(bv.get('away_spread'))} ({odds(bv.get('away_spread_odds'))})</td><td>O {bv.get('total')} ({odds(bv.get('over_odds'))})</td><td>{odds(bv.get('away_ml'))}</td></tr>"
          f"<tr><td>{esc(home)}</td><td>{fmt_spread(bv.get('home_spread'))} ({odds(bv.get('home_spread_odds'))})</td><td>U {bv.get('total')} ({odds(bv.get('under_odds'))})</td><td>{odds(bv.get('home_ml'))}</td></tr></table>")
        book_margin=-hs
        diff=margin-book_margin
        gap=f"Book-implied home margin {book_margin:+.1f} - model {abs(diff):.1f} pts {'higher' if diff>0 else 'lower'} on {esc(home)} than the book."
    else:
        table=''
        if b['timing']=='post_kickoff':
            bk='<span class=dimtxt>closed - not captured</span>'
            gap='No pre-kickoff book capture exists for this game.'
        else:
            bk='<span class=dimtxt>no matched book line</span>'
            gap='No FanDuel Week 6 price matched for this game. This is not a betting recommendation.'
    sec[b['week']].append(
      f'<details class=game><summary><div class=bmatch>{esc(away)} at {esc(home)}</div>'
      f'<div class=bmeta>{et_time(dt)}{"".join(chips)}</div>'
      f'<div class=bgrid><span class=bg-lab>MODEL</span><span class=bnum>{esc(ml)}</span></div>'
      f'<div class=bgrid><span class=bg-lab>{("BOOK "+bv_state).strip()}</span><span class="bnum dim">{bk if bk.startswith("<") else esc(bk)}</span></div></summary>'
      f'<div class=bfoot>{table}<div class=news>Model margin (home) {margin:+.1f} - predicted winner {esc(b["predicted_winner"])}. {gap}</div>'
      f'<div class=news>{esc(b["timing_note"])}</div></div></details>')

n_post=sum(1 for b in ok if b['timing']=='post_kickoff')
n_bk=sum(1 for b in ok if b.get('book_tn') or b.get('book_va'))
for x in errs:
    sec[x.get('week',1)].append(f'<div class=board-note>Not scored: {esc(x["name"])} ({esc(x["error"])})</div>')
wk_buttons=''.join(f'<button data-w="{w}"{ " class=on" if w==6 else ""}>WEEK {w}</button>' for w in sorted(sec, reverse=True))
wk_sections=''.join(f'<section data-week="{w}"{ "" if w==6 else " hidden"}>'+''.join(sec[w])+'</section>' for w in sorted(sec, reverse=True))
gen_label=now_ct.strftime('%Y-%m-%d %-I:%M %p CT')
page=f'''<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>E.D.I.T.H. CFB model board - Week 6, 2026</title>
<style>
:root {{--bg:#07090d;--panel:#10141d;--panel2:#171d29;--line:#1c2230;--line2:#2a3247;--txt:#eef1f7;--dim:#8a92a6;--dim2:#5b6478;--green:#2ee06e;--red:#ff5c5c;--gold:#f5c542;}}
* {{margin:0;padding:0;box-sizing:border-box}}
html {{background:var(--bg)}}
body {{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}}
.wrap {{max-width:720px;margin:0 auto;padding:0 14px 90px}}
header {{display:flex;flex-direction:column;align-items:flex-start;gap:8px;padding:28px 2px 16px}}
h1 {{font-size:26px;letter-spacing:4px;font-weight:900;line-height:1}}
h1 span {{color:var(--green)}}
#updated {{color:var(--dim2);font-size:11px;font-family:ui-monospace,Menlo,monospace;padding-bottom:2px;white-space:normal;line-height:1.5;max-width:100%}}
.league-label {{color:var(--dim2);font-size:11px;letter-spacing:2.5px;font-weight:800;margin:22px 2px 10px}}
nav {{display:flex;gap:6px;position:sticky;top:0;z-index:20;background:rgba(7,9,13,.88);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);padding:10px 0 12px;margin-bottom:14px}}
nav button {{flex:1;background:transparent;border:1px solid transparent;color:var(--dim);font-size:12px;font-weight:800;letter-spacing:1.6px;padding:10px 0;cursor:pointer;border-radius:10px}}
nav button.on {{color:var(--txt);background:var(--panel2);border-color:var(--line2)}}
section[hidden] {{display:none}}
.day-label {{color:var(--dim);font-size:12px;font-weight:700;margin:18px 2px 8px}}
.banner {{background:rgba(255,92,92,.09);border:1px solid rgba(255,92,92,.35);color:#ffb3b3;border-radius:14px;padding:14px 16px;font-size:13px;font-weight:700;line-height:1.5;margin-bottom:12px}}
.note-card {{background:linear-gradient(180deg,#131824,#0e121b);border:1px solid var(--line);border-radius:14px;padding:12px 16px;color:var(--dim);font-size:12px;line-height:1.6;margin-bottom:12px}}
.note-card b {{color:var(--txt)}}
#teamSearch {{width:100%;box-sizing:border-box;margin:8px 0 6px;padding:12px 14px;background:var(--panel);border:1px solid var(--line2);border-radius:12px;color:var(--txt);font-size:14px;outline:none}}
#teamSearch::placeholder {{color:var(--dim2)}}
#teamSearch:focus {{border-color:var(--green)}}
details.game {{background:linear-gradient(180deg,#131824,#0e121b);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:12px;box-shadow:0 10px 28px rgba(0,0,0,.35)}}
details.game>summary {{cursor:pointer;list-style:none}}
details.game>summary::-webkit-details-marker {{display:none}}
details.game[open]>summary {{border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:10px}}
.bmatch {{font-weight:800;font-size:16px;line-height:1.3}}
.bmeta {{display:flex;align-items:center;gap:8px;margin-top:6px;color:var(--dim2);font-size:12px;font-family:ui-monospace,Menlo,monospace}}
.bgrid {{display:grid;grid-template-columns:74px 1fr 1fr;gap:4px 10px;margin-top:10px;align-items:baseline}}
.bg-lab {{color:var(--dim2);font-size:10px;letter-spacing:1.5px;font-weight:800}}
.bnum {{color:var(--txt);font-family:ui-monospace,Menlo,monospace;font-size:13px;white-space:nowrap}}
.bnum.dim,.dimtxt {{color:var(--dim2)}}
.chip {{font-size:10px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:999px;white-space:nowrap;font-family:inherit}}
.chip-flag {{background:rgba(245,197,66,.1);color:var(--gold)}}
.chip-neutral {{background:rgba(46,224,110,.13);color:var(--green)}}
.chip-muted {{background:rgba(138,146,166,.13);color:var(--dim)}}
.bfoot table {{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px}}
.bfoot th {{text-align:left;color:var(--dim2);font-size:10px;letter-spacing:1.5px;font-weight:800;padding:8px 6px 6px;border-bottom:1px solid var(--line2)}}
.bfoot td {{padding:8px 6px;border-bottom:1px solid var(--line);font-family:ui-monospace,Menlo,monospace;font-size:12px}}
.bfoot td:first-child,.bfoot th:first-child {{font-family:inherit}}
.news {{margin-top:8px;font-size:11px;color:var(--dim2);line-height:1.5}}
.board-note {{color:var(--dim2);font-size:11px;margin:6px 2px 10px;line-height:1.6}}
footer {{margin-top:36px;color:var(--dim2);font-size:11px;line-height:1.8;border-top:1px solid var(--line);padding-top:16px}}
a {{color:#58a6ff}}
@media(max-width:560px){{h1{{font-size:21px;letter-spacing:3px}}.bgrid{{grid-template-columns:64px 1fr 1fr}}}}
</style></head><body><div class=wrap>
<header><h1>E.D.I.T.H. <span>CFB</span> BOARD</h1><div id=updated>Week 6, 2026 - initial model + book comparison{(' - '+esc(BOOK_LABEL)) if BOOK_LABEL else ' (no current capture)'} - updated {esc(gen_label)}</div></header>
<div class=banner>MEASUREMENT ONLY - NOT PICKS. This model has not been proven against book lines. It exists to measure whether the model\'s margins track reality.</div>
<div class=note-card><b>Book lines:</b> {esc(BOOK_LABEL) if BOOK_LABEL else 'no current Week 6 capture; every book price is null'} - labeled comparison display, never a model input. MODEL display lines round to the nearest 0.5 point; underlying model outputs and grading precision are unchanged. Initial Week 5 model numbers use completed Week 4 results and the Sep 27 AP poll. The supplied jurisdiction-labeled book comparison is shown where matched; unmatched games have null book prices. Comparison tracked, not a pick. CFB uses FBS sides/totals only, no college props.</div>
<div class=note-card><b>Coverage:</b> {len(ok)} of {len(ok)+len(errs)} FBS-scheduled Week 6 games (Oct 6-12). Unscored games are listed below; FCS opponents are outside the model corpus.</div>
<div class=note-card><b>Model:</b> cfb-gameline-v2.2 uses 2026 finals through Week 5 and the archived Oct 4 AP Top 25 points, published before kickoff. AP validation protocol: train 2020-23, validation 2024, locked test 2025; validation MAE 13.504 vs 13.589 base, locked-test MAE 13.116 vs 13.360, bootstrap delta 95% CI -0.453 to -0.040. Unranked teams get zero AP points. Injury impact remains unmodeled. <a href="https://github.com/Garrettwalker1/ediths-picks/blob/main/tools/cfb/29-cfb_board_2026_week6_initial_v2_2.json">Raw Week 6 board</a> - <a href="https://github.com/Garrettwalker1/ediths-picks/blob/main/tools/model_cfb_v2/ap_poll_experiment.json">AP validation</a>.</div>
<input id=teamSearch placeholder="Filter teams">
<nav>{wk_buttons}</nav>
{wk_sections}
<footer>E.D.I.T.H.\'s Picks - cfb-gameline-v2.2 - measurement, not picks. Book lines display-only, never model inputs.</footer>
</div><script>document.getElementById('teamSearch').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('details.game').forEach(d=>{{d.style.display=d.textContent.toLowerCase().includes(q)?'':'none'}})}});
document.querySelectorAll('nav button').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('nav button').forEach(b=>b.classList.remove('on'));btn.classList.add('on');document.querySelectorAll('section[data-week]').forEach(sc=>{{sc.hidden=sc.dataset.week!==btn.dataset.w}})}}))</script>
</body></html>'''
(OUT/'cfb-board-2026-week6.html').write_text(page)
print('page bytes:',len(page.encode()))
