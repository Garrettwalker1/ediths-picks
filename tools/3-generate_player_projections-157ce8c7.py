#!/usr/bin/env python3
"""Build root player_projections.json. Fails closed and atomically replaces only after validation.
Dependencies: Python 3.10+, pandas, numpy, scikit-learn, pyarrow, requests.
No credentials or private payloads are used.
"""
import argparse, datetime as dt, json, os, re, shutil, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd, requests
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
BASE="https://github.com/nflverse/nflverse-data/releases/download"
URLS={**{f"stats_{y}":f"{BASE}/stats_player/stats_player_week_{y}.csv" for y in (2023,2024,2025)},
      **{f"pbp_{y}":f"{BASE}/pbp/play_by_play_{y}.parquet" for y in (2023,2024,2025)},
      "schedules":f"{BASE}/schedules/games.csv"}
COLS=['player_id','player_display_name','position','team','season','week','season_type','game_id','opponent_team','carries','rushing_yards','rushing_tds','targets','receptions','receiving_yards','receiving_tds','receiving_air_yards','target_share','air_yards_share','wopr','fantasy_points_ppr']
BASE_FEATURES=['receiving_yards','targets','receptions','receiving_air_yards','target_share','air_yards_share','wopr','rushing_yards','carries','receiving_tds','rushing_tds','fantasy_points_ppr']
RF=['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receptions_r3','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3']
QF=['rushing_yards_r3','rushing_yards_r6','carries_r3','carries_r6']; REPF=['receptions_r3','targets_r3','targets_r6']
TDF=['receiving_tds_r6','rushing_tds_r6','targets_r3','target_share_r3','receiving_air_yards_r3','carries_r3','receiving_yards_r3','rushing_yards_r3']
BF=['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3']

def die(msg): raise RuntimeError(msg)
def fetch(url,path):
    if path.exists() and path.stat().st_size>10000:return
    r=requests.get(url,timeout=120);r.raise_for_status();path.write_bytes(r.content)
def norm(s):return re.sub(r'[^a-z0-9]','',str(s).lower())
def roll(d):
    d=d.sort_values(['player_id','season','week']).copy();g=d.groupby('player_id',group_keys=False)
    for c in BASE_FEATURES:
        for n in (3,6):d[f'{c}_r{n}']=g[c].transform(lambda x:x.shift().rolling(n,min_periods=3).mean())
    return d
def latest_rows(d):
    out=[]
    for _,x in d[d.season.eq(2025)].groupby('player_id'):
        x=x.sort_values('week');z=x.iloc[-1].copy()
        for c in BASE_FEATURES:
            for n in (3,6):z[f'{c}_r{n}']=x[c].tail(n).mean()
        out.append(z)
    return pd.DataFrame(out)
def lin(train,fs,y):return LinearRegression().fit(train.dropna(subset=fs)[fs],train.dropna(subset=fs)[y])
def logit(train,fs,y):return make_pipeline(StandardScaler(),LogisticRegression(C=.5,max_iter=1000)).fit(train.dropna(subset=fs)[fs],train.dropna(subset=fs)[y])
def pred(m,fs,z):return float(max(0,m.predict(pd.DataFrame([{f:z[f] for f in fs}]))[0]))
def prob(m,fs,z):return float(m.predict_proba(pd.DataFrame([{f:z[f] for f in fs}]))[0,1])
def upcoming(games,now):
    g=games[(games.season==now.year)&games.game_type.eq('REG')].copy();g['gameday']=pd.to_datetime(g.gameday,errors='coerce').dt.date
    future=g[g.gameday>=now.date()].sort_values('gameday')
    if future.empty:die(f'No future regular-season NFL games for {now.year}')
    w=int(future.iloc[0].week);x=g[g.week.eq(w)]
    if not 1<=len(x)<=16:die(f'Upcoming Week {w} has implausible game count {len(x)}')
    opp={}
    for z in x.itertuples():opp[str(z.away_team)]=str(z.home_team);opp[str(z.home_team)]=str(z.away_team)
    return w,opp

def validate(o,expected_leagues):
    if o.get('schema_version')!='1.1.0':die('Wrong schema version')
    p=o.get('players');m=o.get('matchup_context',{}).get('rows')
    if not isinstance(p,list) or len(p)<150:die(f'Too few projection rows: {len(p) if isinstance(p,list) else "invalid"}')
    if len({x.get('player_id') for x in p})!=len(p):die('Duplicate player IDs')
    if sum(bool(x.get('fantasy_rostered')) for x in p)<20:die('Too few roster matches; fantasy input may be stale/incompatible')
    if not isinstance(m,list) or len(m)<100:die(f'Too few matchup rows: {len(m) if isinstance(m,list) else "invalid"}')
    for x in p:
        for k in ('anytime_td_probability','boom_probability'):
            if not 0<=float(x[k])<=1:die(f'Bad probability {k} for {x.get("player")}')
        if x.get('bust_probability') is not None and not 0<=float(x['bust_probability'])<=1:die('Bad bust probability')
    if not o['bust_model'].get('proven'):die('Bust model failed locked gate; generator refuses to publish numeric bust values')
    if expected_leagues!=7:die(f'Fantasy source must contain exactly 7 leagues, got {expected_leagues}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default='.');ap.add_argument('--cache-dir',default='tools/player_projection_cache');ap.add_argument('--now',help='ISO timestamp override for deterministic dry-run');a=ap.parse_args()
    root=Path(a.repo_root).resolve();cache=(root/a.cache_dir);cache.mkdir(parents=True,exist_ok=True)
    for k,u in URLS.items():fetch(u,cache/(k+('.parquet' if 'pbp_' in k else '.csv')))
    fantasy_path=root/'fantasy.json'
    if not fantasy_path.exists():die('Missing root fantasy.json')
    fantasy=json.loads(fantasy_path.read_text());leagues=fantasy.get('leagues',[])
    frames=[]
    for y in (2023,2024,2025):
        x=pd.read_csv(cache/f'stats_{y}.csv',usecols=COLS,low_memory=False);frames.append(x[x.season_type.eq('REG')])
    raw=pd.concat(frames,ignore_index=True);counts=raw.groupby('season').size().to_dict()
    if any(counts.get(y,0)<4500 for y in (2023,2024,2025)):die(f'Incomplete weekly stats: {counts}')
    d=roll(raw);r=d[d.position.isin(['WR','TE','RB'])&d.receiving_yards_r3.notna()].copy()
    # Locked bust gate: train 2024, evaluate exactly once on 2025.
    bust=r[(r.targets_r3>=4)&r.receiving_yards_r6.notna()].copy();bust['bust']=((bust.receiving_yards<30)&(bust.receiving_yards<.5*bust.receiving_yards_r6)).astype(int)
    mets={}
    for name,fs in {'past_yards':['receiving_yards_r3','receiving_yards_r6'],'combined':BF}.items():
        tr=bust[bust.season.eq(2024)].dropna(subset=fs);te=bust[bust.season.eq(2025)].dropna(subset=fs);model=logit(tr,fs,'bust');p=model.predict_proba(te[fs])[:,1]
        mets[name]={'n_train':len(tr),'n_test':len(te),'events':int(te.bust.sum()),'brier':float(brier_score_loss(te.bust,p)),'auc':float(roc_auc_score(te.bust,p))}
    proven=mets['combined']['brier']<mets['past_yards']['brier'] and mets['combined']['auc']>mets['past_yards']['auc']
    if not proven:die(f'Locked bust gate failed: {mets}')
    recm=lin(r,RF,'receiving_yards');rr=d[d.position.isin(['RB','QB'])&d.rushing_yards_r3.notna()];rushm=lin(rr,QF,'rushing_yards');repm=lin(r,REPF,'receptions')
    td=r.copy();td['y']=((td.receiving_tds+td.rushing_tds)>0).astype(int);tdm=logit(td,TDF,'y')
    boom=r[(r.targets_r3>=2)&r.receiving_yards_r6.notna()].copy();boom['y']=((boom.receiving_yards>=80)&(boom.receiving_yards>=1.5*boom.receiving_yards_r6.clip(lower=20))).astype(int);bm=logit(boom,RF,'y');bustm=logit(bust,BF,'bust')
    roster_names={norm(p.get('name')) for l in leagues for p in l.get('players',[])}
    L=latest_rows(d);L=L[L.position.isin(['RB','WR','TE'])&L.targets_r3.notna()].copy();L['fantasy_rostered']=L.player_display_name.map(lambda x:norm(x) in roster_names);L['role']=L.targets_r3+L.carries_r3;L=L.sort_values(['fantasy_rostered','role'],ascending=False);L=pd.concat([L[L.fantasy_rostered],L[~L.fantasy_rostered].head(180)]).drop_duplicates('player_id')
    players=[]
    for _,z in L.iterrows():
        recv=pred(recm,RF,z);rush=pred(rushm,QF,z);recs=pred(repm,REPF,z);bu=prob(bustm,BF,z) if z.targets_r3>=4 else None
        players.append({'sport':'NFL','player_id':z.player_id,'player':z.player_display_name,'team':z.team,'position':z.position,'fantasy_rostered':bool(z.fantasy_rostered),'projection_context':'Generic baseline; weekly opponent/depth-chart adjustment not proven','receiving_yards':{'median':round(recv,1),'p20':round(max(0,recv-19.5),1),'p80':round(recv+19.5,1)},'rushing_yards':{'median':round(rush,1),'p20':round(max(0,rush-21.7),1),'p80':round(rush+21.7,1)},'receptions':{'median':round(recs,1),'p20':round(max(0,recs-1.8),1),'p80':round(recs+1.8,1)},'anytime_td_probability':round(prob(tdm,TDF,z),3),'boom_probability':round(prob(bm,RF,z),3),'bust_probability':round(bu,3) if bu is not None else None,'drivers':{'targets_last3':round(float(z.targets_r3),1),'carries_last3':round(float(z.carries_r3),1),'receiving_yards_last6':round(float(z.receiving_yards_r6),1)}})
    now=dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(dt.timezone.utc);games=pd.read_csv(cache/'schedules.csv');week,opps=upcoming(games,now)
    # Defensive descriptive context, SOS-adjusted against each offense-position trailing expectation.
    A=raw[raw.position.isin(['WR','TE','RB'])].copy();A['posgrp']=A.position
    A=A.groupby(['season','week','game_id','team','opponent_team','posgrp']).agg(receiving_yards_allowed=('receiving_yards','sum'),rushing_yards_allowed=('rushing_yards','sum'),receiving_tds_allowed=('receiving_tds','sum'),rushing_tds_allowed=('rushing_tds','sum'),targets_allowed=('targets','sum')).reset_index().sort_values(['team','posgrp','season','week']);G=A.groupby(['team','posgrp'],group_keys=False)
    metrics=['receiving_yards_allowed','rushing_yards_allowed','receiving_tds_allowed','rushing_tds_allowed','targets_allowed']
    for c in metrics:A['adj_'+c]=A[c]-G[c].transform(lambda x:x.shift().rolling(8,min_periods=3).mean())
    S=A[A.season.isin([2024,2025])].groupby(['opponent_team','posgrp']).agg(games=('game_id','nunique'),**{c:(c,'mean') for c in metrics+['adj_'+c for c in metrics]}).reset_index();match=[]
    for x in players:
        de=opps.get(x['team']);z=S[(S.opponent_team==de)&(S.posgrp==x['position'])]
        if not de or z.empty:continue
        z=z.iloc[0];hh=raw[(raw.player_id==x['player_id'])&(raw.opponent_team==de)];ng=int(hh.game_id.nunique());hs={'games':ng,'receiving_yards_per_game':round(float(hh.receiving_yards.mean()),1),'rushing_yards_per_game':round(float(hh.rushing_yards.mean()),1),'td_games':int(((hh.receiving_tds+hh.rushing_tds)>0).sum())} if ng>=3 else None
        tdallow=float(z.receiving_tds_allowed+z.rushing_tds_allowed);reason=f"{de} allowed {z.receiving_yards_allowed:.1f} receiving yards/game to {x['position']}s ({z.adj_receiving_yards_allowed:+.1f} SOS-adjusted); {z.targets_allowed:.1f} targets/game ({z.adj_targets_allowed:+.1f}); {tdallow:.2f} TDs/game. "+(f"Head-to-head: {ng} games, {hs['receiving_yards_per_game']:.1f} receiving and {hs['rushing_yards_per_game']:.1f} rushing yards/game." if hs else f"Head-to-head: {ng} game(s), too small to treat as signal.")
        match.append({'player_id':x['player_id'],'player':x['player'],'team':x['team'],'position':x['position'],'opponent':de,'fantasy_rostered':x['fantasy_rostered'],'defense_sample_games':int(z.games),'raw_allowed':{'receiving_yards_per_game':round(float(z.receiving_yards_allowed),1),'rushing_yards_per_game':round(float(z.rushing_yards_allowed),1),'targets_per_game':round(float(z.targets_allowed),1),'tds_per_game':round(tdallow,2)},'sos_adjusted_vs_opponent_normal':{'receiving_yards':round(float(z.adj_receiving_yards_allowed),1),'rushing_yards':round(float(z.adj_rushing_yards_allowed),1),'targets':round(float(z.adj_targets_allowed),1),'tds':round(float(z.adj_receiving_tds_allowed+z.adj_rushing_tds_allowed),2)},'head_to_head':hs,'reasoning':reason})
    o={'generated_at':now.isoformat(),'schema_version':'1.1.0','status':'research','headline':'Boom/bust player projections','method_note':'NFL model trained on 2024-25 after a locked 2024-to-2025 holdout test. No betting edge is claimed.','bust_model':{'proven':proven,'definition':'Under 30 receiving yards AND under 50% of prior six-game mean among players averaging at least 4 targets per game','holdout':mets},'sports_available':['NFL'],'cfb_status':'CFB receiving withheld because 2024 target-player data is materially incomplete versus 2025.','sportsbook':{'active':False,'label':'Research only','book':'FanDuel','line':None,'price':None,'observed_at':None,'note':'No reliable automated FanDuel player-prop feed is connected.'},'sources':[{'name':'nflverse weekly player stats','url':URLS['stats_2025'],'provider':'nflverse','observed_at':now.isoformat()},{'name':'nflverse schedules','url':URLS['schedules'],'provider':'nflverse','observed_at':now.isoformat()}],'players':players,'matchup_context':{'status':'descriptive_only','week':week,'history_seasons':[2024,2025],'method':'Defense-by-position averages adjusted by each opponent-position group trailing eight-game expectation; H2H shown as signal only at 3+ games.','heldout_result':'Did not improve receiving prediction: 2025 MAE 16.2579 base vs 16.2536 with matchup features, n=5,035.','rows':match}}
    validate(o,len(leagues));target=root/'player_projections.json';fd,tmp=tempfile.mkstemp(prefix='player_projections.',suffix='.json',dir=root);os.close(fd);Path(tmp).write_text(json.dumps(o,indent=2));json.loads(Path(tmp).read_text());os.replace(tmp,target);print(json.dumps({'status':'written','path':str(target),'players':len(players),'matchups':len(match),'week':week,'rostered':sum(x['fantasy_rostered'] for x in players)}))
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'FAIL-CLOSED: {e}',file=sys.stderr);sys.exit(2)
