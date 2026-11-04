"""Current-input engine using the preserved fixed fitted specification."""
import json,re,importlib.util
from pathlib import Path
import pandas as pd,numpy as np
from fixed_inference import load_models
R=Path(__file__).resolve().parents[3]
import features as m
def build(raw,rost,fantasy,opp,season,week):
 models=load_models()
 norm=lambda s:re.sub('[^a-z0-9]','',re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?','',str(s).lower()));raw['key']=raw.player_display_name.map(norm)
 roster={}
 for t,j in rost.items():
  assert 'athletes' in j,t
  for gr in j['athletes']:
   for a in gr.get('items',[]):
    if a.get('position',{}).get('abbreviation') in ['RB','WR','TE'] and a.get('status',{}).get('type')!='practice-squad':
     key=norm(a['fullName'])
     if key in roster:raise ValueError('Ambiguous current roster identity: '+a['fullName'])
     roster[key]=(t,a)
 fn={norm(x['name']) for l in fantasy['leagues'] for x in l.get('players',[])};players=[];omitted=[]
 for key,(team,a) in roster.items():
  g=raw[raw.key.eq(key)].sort_values(['season','week']);ids=g.player_id.unique()
  if len(g)<3 or len(ids)!=1:omitted.append({'player':a['fullName'],'team':team,'reason':'fewer than3NFLregular-seasonhistoryrows or ambiguousID','history_rows':len(g),'fantasy_snapshot_rostered':key in fn});continue
  z=g.iloc[-1].copy()
  for c in m.BASE_FEATURES:
   for n in [3,6]:z[f'{c}_r{n}']=g[c].tail(n).mean()
  if not np.isfinite([z[f] for f in set(m.RF+m.QF+m.REPF+m.TDF+m.BF)]).all():omitted.append({'player':a['fullName'],'team':team,'reason':'nonfinite required historicalfeature'});continue
  recv=m.pred(models['recv'],m.RF,z);rush=m.pred(models['rush'],m.QF,z);recs=m.pred(models['recs'],m.REPF,z);bu=m.prob(models['bust'],m.BF,z) if z.targets_r3>=4 else None
  players.append({'sport':'NFL','player_id':str(ids[0]),'player':a['fullName'],'team':team,'position':a['position']['abbreviation'],'fantasy_rostered':key in fn,'projection_context':'Generic fitted model, history through completed prior week where available. No injury, workload, QB or opponent adjustment. Roster status is not game clearance.','receiving_yards':{'median':round(recv,1),'p20':round(max(0,recv-19.5),1),'p80':round(recv+19.5,1)},'rushing_yards':{'median':round(rush,1),'p20':round(max(0,rush-21.7),1),'p80':round(rush+21.7,1)},'receptions':{'median':round(recs,1),'p20':round(max(0,recs-1.8),1),'p80':round(recs+1.8,1)},'anytime_td_probability':round(m.prob(models['td'],m.TDF,z),3),'boom_probability':round(m.prob(models['boom'],m.RF,z),3),'bust_probability':round(bu,3) if bu is not None else None,'drivers':{'targets_last3':round(float(z.targets_r3),1),'carries_last3':round(float(z.carries_r3),1),'receiving_yards_last6':round(float(z.receiving_yards_r6),1)},'input_history':{'last_season':int(g.season.iloc[-1]),'last_week':int(g.week.iloc[-1]),'rows':len(g),'roster_status':a.get('status',{}).get('type'),'fantasy_snapshot_at':fantasy.get('updated_at')},'model_probability_note':'Generic usage TD logit, not the separate h12/k4 TD board. Fixed interval widths are not calibrated current-matchup intervals.'})
 # Retain same2024-25 defense-by-position descriptive calculation; no change to predictions.
 A=raw[raw.position.isin(['WR','TE','RB'])].copy();A['posgrp']=A.position;A=A.groupby(['season','week','game_id','team','opponent_team','posgrp']).agg(receiving_yards_allowed=('receiving_yards','sum'),rushing_yards_allowed=('rushing_yards','sum'),receiving_tds_allowed=('receiving_tds','sum'),rushing_tds_allowed=('rushing_tds','sum'),targets_allowed=('targets','sum')).reset_index().sort_values(['team','posgrp','season','week']);G=A.groupby(['team','posgrp'],group_keys=False);metrics=['receiving_yards_allowed','rushing_yards_allowed','receiving_tds_allowed','rushing_tds_allowed','targets_allowed']
 for c in metrics:A['adj_'+c]=A[c]-G[c].transform(lambda x:x.shift().rolling(8,min_periods=3).mean())
 S=A[A.season.eq(season)].groupby(['opponent_team','posgrp']).agg(games=('game_id','nunique'),**{c:(c,'mean') for c in metrics+['adj_'+c for c in metrics]}).reset_index()
 match=[]
 for x in players:
  de=opp.get(x['team']);z=S[(S.opponent_team.replace({'WAS':'WSH','LAR':'LA'})==de)&(S.posgrp==x['position'])]
  if not de or z.empty:continue
  z=z.iloc[0];hh=raw[(raw.player_id==x['player_id'])&(raw.opponent_team.replace({'WAS':'WSH','LAR':'LA'})==de)];ng=int(hh.game_id.nunique());hs={'games':ng,'receiving_yards_per_game':round(float(hh.receiving_yards.mean()),1),'rushing_yards_per_game':round(float(hh.rushing_yards.mean()),1),'td_games':int(((hh.receiving_tds+hh.rushing_tds)>0).sum())} if ng>=3 else None;tdallow=float(z.receiving_tds_allowed+z.rushing_tds_allowed)
  match.append({'player_id':x['player_id'],'player':x['player'],'team':x['team'],'position':x['position'],'opponent':de,'fantasy_rostered':x['fantasy_rostered'],'defense_sample_games':int(z.games),'raw_allowed':{'receiving_yards_per_game':round(float(z.receiving_yards_allowed),1),'rushing_yards_per_game':round(float(z.rushing_yards_allowed),1),'targets_per_game':round(float(z.targets_allowed),1),'tds_per_game':round(tdallow,2)},'sos_adjusted_vs_opponent_normal':{'receiving_yards':round(float(z.adj_receiving_yards_allowed),1),'rushing_yards':round(float(z.adj_rushing_yards_allowed),1),'targets':round(float(z.adj_targets_allowed),1),'tds':round(float(z.adj_receiving_tds_allowed+z.adj_rushing_tds_allowed),2)},'head_to_head':hs,'reasoning':f'Week {week} opponent {de}. {season} defense by position through Week {week-1}: {z.receiving_yards_allowed:.1f} receiving yards and {z.targets_allowed:.1f} targets per game to {x["position"]}s. Descriptive only, not used in predictions. Head-to-head history is a small sample.'})
 return players,omitted,match
