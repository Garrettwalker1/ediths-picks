"""Fixed adopted Oct29 TD inference. No refit, book inputs or injury redistribution."""
import pathlib,json,datetime,hashlib,gzip
import pandas as pd,numpy as np,joblib
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).parent;S=R/'tools/nfl/current_season_20261124/sources';A={'WAS':'WSH','LAR':'LA','OAK':'LV','SD':'LAC','STL':'LA'};W=12
frames=[pd.read_csv(R/f'tools/player_projection_cache/stats_{y}.csv',low_memory=False)for y in [2023,2024,2025]]+[pd.read_csv(S/'player_stats_2026.csv',low_memory=False)]
d=pd.concat(frames,ignore_index=True);d=d[(d.season_type=='REG')&d.position.isin(['QB','RB','WR','TE'])&((d.season<2026)|(d.week<W))].copy();d.team=d.team.replace(A);d.opponent_team=d.opponent_team.replace(A);assert not d.duplicated(['player_id','season','week']).any()
p=pd.read_parquet(S/'pbp_2026.parquet',columns=['game_id','season','week','season_type','posteam','defteam','yardline_100','play_type','rusher_player_id','receiver_player_id','epa','rush_touchdown','pass_touchdown','two_point_attempt']);p=p[(p.season_type=='REG')&(p.week<W)&p.play_type.isin(['run','pass'])&(p.two_point_attempt!=1)].copy();p.posteam=p.posteam.replace(A);p.defteam=p.defteam.replace(A)
g=pd.read_csv(S/'games.csv');prior=g[(g.season==2026)&(g.game_type=='REG')&(g.week<W)];assert len(prior)==163 and prior.home_score.notna().all();assert set(p.game_id)==set(prior.game_id)
rzs=[]
for typ,pid,play in [('carry','rusher_player_id','run'),('target','receiver_player_id','pass')]:
 z=p[(p.play_type==play)&p[pid].notna()].copy();z['rz']=z.yardline_100.le(20).astype(int);z['gl']=z.yardline_100.le(5).astype(int);rzs.append(z.groupby(['game_id',pid]).agg(**{typ+'_rz':('rz','sum'),typ+'_gl':('gl','sum')}).reset_index().rename(columns={pid:'player_id'}))
rz=pd.concat(rzs).groupby(['game_id','player_id'],as_index=False).sum(numeric_only=True);d=d.merge(rz,on=['game_id','player_id'],how='left');rzcols=['carry_rz','carry_gl','target_rz','target_gl'];d[rzcols]=d[rzcols].fillna(0);d['tds']=d.rushing_tds.fillna(0)+d.receiving_tds.fillna(0);d['touch']=d.carries.fillna(0)+d.targets.fillna(0)
team=p.groupby(['game_id','posteam','defteam'],as_index=False).agg(plays=('epa','size'),epa=('epa','sum'),rush_td=('rush_touchdown','sum'),pass_td=('pass_touchdown','sum'));tf={}
off=team.groupby('posteam').agg(epa=('epa','sum'),plays=('plays','sum'),rush_td=('rush_td','sum'),pass_td=('pass_td','sum'),gp=('game_id','nunique'));de=team.groupby('defteam').agg(epa=('epa','sum'),plays=('plays','sum'),rush_td=('rush_td','sum'),pass_td=('pass_td','sum'),gp=('game_id','nunique'))
for f in [off,de]:f['epa_rate']=f.epa/f.plays;f['rush_rate']=f.rush_td/f.gp;f['pass_rate']=f.pass_td/f.gp
for t in off.index:tf[t]={**{'off_'+c:float(off[c].rank(pct=True)[t])for c in ['epa_rate','rush_rate','pass_rate']},**{'def_'+c:float(de[c].rank(pct=True)[t])for c in ['epa_rate','rush_rate','pass_rate']}}
ev=json.load(open(S/'week12.json'));games={}
for e in ev['events']:
 c=e['competitions'][0];assert c['status']['type']['state']=='pre';t={z['homeAway']:A.get(z['team']['abbreviation'],z['team']['abbreviation'])for z in c['competitors']};h,a=t['home'],t['away'];games[a]=dict(opp=h,home=0,date=c['date'],event_id=e['id']);games[h]=dict(opp=a,home=1,date=c['date'],event_id=e['id'])
master=pd.read_csv(S/'players.csv',dtype={'espn_id':str,'gsis_id':str},low_memory=False);master.espn_id=master.espn_id.str.replace('.0','',regex=False);xwalk=master.groupby('espn_id').gsis_id.apply(lambda x:sorted(set(x.dropna())))
lam=json.load(open(R/'tools/props_w4/validation_atd.json'))['lam'];rows=[];null=[];now=datetime.datetime.now(datetime.timezone.utc).isoformat();rosters={}
for t in games:
 rosters[t]=json.load(gzip.open(P/'current_rosters.json.gz','rt'))[t]
 for group in rosters[t]['athletes']:
  for a in group.get('items',[]):
   pos=a.get('position',{}).get('abbreviation');status=a.get('status',{}).get('type')
   if pos not in ['QB','RB','WR','TE']or status=='practice-squad':continue
   ids=xwalk.get(str(a['id']),[]);pid=ids[0]if len(ids)==1 else None;h=d[d.player_id==pid].sort_values(['season','week']);base=dict(player=a['fullName'],player_id=pid,espn_id=str(a['id']),pos=pos,team=t,opp=games[t]['opp'],kick=games[t]['date'],roster_status=status,availability_note='Current roster membership only. Week12 game clearance not verified; Week11 OUTs not carried forward.',book=None,book_prob=None,gap=None,cap=None)
   if h.empty:null.append(dict(base,reason='No uniquely crosswalked ESPN-to-GSIS regular-season history'));continue
   v=h.tds.tail(17).to_numpy();w=.5**(np.arange(len(v))[::-1]/12);pr=1-np.exp(-((w*v).sum()+4*lam.get(pos,.28))/(w.sum()+4));rows.append(dict(base,games=len(v),model=round(float(pr),3),last_season=int(h.season.iloc[-1]),last_week=int(h.week.iloc[-1]),model_note='Locked h12/k4 historical TD-rate baseline; no injury/QB/teammate adjustment.'))
baseline=dict(week=W,season=2026,generated_at=now,captured_from=None,captured_to=None,state=None,note='Stats throughWeek11, all26playingteams current roster; exactESPN-GSIScrosswalk. No injury/QB/workload/bookinputs; statusnotgameclearance.',coverage=dict(playing_teams=len(games),modeled_players=len(rows),unranked_no_history=null,injury_report_week11_rows=0),rows=sorted(rows,key=lambda r:(r['kick'],-r['model'])))
(P/'td_projection_snapshot.json').write_text(json.dumps(baseline,indent=1)+'\n')
m=joblib.load(R/'tools/nfl/td_matchup_20261029/candidate.joblib');features=json.load(open(R/'tools/nfl/td_matchup_20261029/diagnostics.json'))['features'];rank=[];unrank=[];hist={pid:h.sort_values(['season','week'])for pid,h in d.groupby('player_id')};allcur={t:h for t,h in d[d.season==2026].groupby('team')}
for b in rows:
 t=b['team'];h=hist[b['player_id']];cur=h[(h.season==2026)&(h.team==t)];reason='fewer than 3 career games in 2023+ window'if len(h)<3 else'recent touch volume below model gate'if h.touch.tail(6).mean()<3 else'fewer than 2 current-season games with this team'if len(cur)<2 else None
 rec=dict(player=b['player'],player_id=b['player_id'],pos=b['pos'],team=t,opp=b['opp'],home=bool(games[t]['home']),kick=b['kick'],baseline=b['model'],report_status=None,practice_status=None)
 if reason:unrank.append(dict(rec,primary=None,unranked_reason=reason));continue
 v=h.tds.tail(17).to_numpy();w=.5**(np.arange(len(v))[::-1]/12);bs=1-np.exp(-((w*v).sum()+4*lam.get(h.position.iloc[-1],.28))/(w.sum()+4));x=dict(baseline_logit=float(np.log(np.clip(bs,1e-6,1-1e-6)/(1-np.clip(bs,1e-6,1-1e-6)))),is_home=games[t]['home']);allc=allcur[t]
 for c in ['targets','carries']+rzcols:x[c+'_share']=float(cur[c].sum()/max(1,allc[c].sum()))
 for c in ['targets','carries']:x[c+'_recent4']=float(cur[c].tail(4).mean())
 for c in ['epa_rate','rush_rate','pass_rate']:x['off_'+c]=tf[t]['off_'+c];x['opp_'+c]=tf[b['opp']]['def_'+c]
 for pos in ['QB','RB','TE']:x['pos_'+pos]=int(h.position.iloc[-1]==pos)
 rec.update(primary=float(m.predict_proba(pd.DataFrame([x])[features])[0,1]),features=x);rank.append(rec)
for b in null:unrank.append(dict(b,primary=None,baseline=None,unranked_reason=b['reason']))
old=json.load(open(R/'tools/nfl/week11_2026/td_week11_primary.json'));out={k:v for k,v in old.items()if k not in ['ranked','unranked','excluded','generated_at','week','season','excluded_confirmed_out','current_personnel_warning']};out.update(generated_at=now,week=W,season=2026,stats_through='2026 Week11 finals; all163completedgameIDs verified in freshPBP and stats; noWeek12plays.',baseline='Locked historical h12/k4 baseline throughWeek11 kept beside primary.',ranked=sorted(rank,key=lambda r:-r['primary']),unranked=unrank,excluded=[],coverage_note='Current roster membership is not Week12 game clearance. No prior-week formal OUT carried forward. Workload/QB/teammate redistribution not modeled.',model_sha256=hashlib.sha256((R/'tools/nfl/td_matchup_20261029/candidate.joblib').read_bytes()).hexdigest());(P/'td_week12_primary.json').write_text(json.dumps(out,indent=1)+'\n');print('baseline',len(rows),'ranked',len(rank),'unranked',len(unrank),'completePBP',len(set(p.game_id)))

held=json.load(open(P/'confirmed_unavailable.json'));out['confirmed_unavailable']=held;out['excluded']=held;out['current_roster_injury_tags']=json.load(open(P/'roster_injury_tags.json'));(P/'td_week12_primary.json').write_text(json.dumps(out,indent=1)+'\n')
