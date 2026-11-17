"""Build a factual Week11 IND-HOU companion. No numeric injury application."""
import datetime, gzip, hashlib, json, pathlib, re
import pandas as pd
from bs4 import BeautifulSoup
P=pathlib.Path(__file__).resolve().parent
R=P.parents[2]
C=R/'tools/nfl/current_season_20261117'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'sources/manifest.json').read_text())
meta=pd.read_csv(C/'sources/players.csv',dtype={'espn_id':str},low_memory=False)
D=pd.read_csv(C/'sources/player_stats_2026.csv',low_memory=False)
G=pd.read_csv(C/'sources/games.csv',low_memory=False)
prior=G[(G.season==2026)&(G.game_type=='REG')&(G.gameday<'2026-11-17')&G.home_score.notna()&G.away_score.notna()]
D=D[(D.season==2026)&(D.season_type=='REG')&D.game_id.isin(prior.game_id)].copy()
assert not D.duplicated(['team','player_id','game_id']).any()
D['volume']=D[['attempts','carries','receptions']].fillna(0).sum(axis=1)
rosters={tm:json.load(gzip.open(P/f'sources/roster_{tm}.json.gz')) for tm in ['IND','HOU']}
athletes={tm:[a for g in v['athletes'] for a in g['items']] for tm,v in rosters.items()}
# Aliases are explicitly confirmed by exact ESPN ID in the players crosswalk.
aliases={'Ahmad Gardner':'4427250','Andrew Ogletree':'4722908','Jacob Hummel':'4241250'}
def identity(team,name):
 a=[a for a in athletes[team] if name in [a.get('displayName'),a.get('fullName')]]
 if not a and name in aliases:a=[a for a in athletes[team] if a['id']==aliases[name]]
 assert len(a)==1,(team,name,len(a))
 a=a[0]; mm=meta[meta.espn_id.str.replace(r'\.0$','',regex=True)==a['id']]
 assert len(mm)==1,(team,name,a['id'],len(mm))
 m=mm.iloc[0]
 return a,m

def player(team,name):
 a,m=identity(team,name);rows=D[(D.team==team)&(D.player_id==m.gsis_id)].sort_values('week')
 tm=D[D.team==team];vol=float(rows.volume.sum());total=float(tm.volume.sum())
 out={'name':a['displayName'],'reported_name':name,'team':team,'position':a['position']['abbreviation'],'espn_id':a['id'],'gsis_id':m.gsis_id,'identity_basis':'Exact roster ESPN ID to preserved players.csv ESPN/GSIS crosswalk; explicit source aliases only.','roster_status':a.get('status'), 'roster_injury_tags':a.get('injuries',[]),'stat_row_appearances':len(rows),'trailing_volume':vol,'team_trailing_volume':total,'trailing_share':vol/total if total else None,'established_skill_volume_gate':bool(m.position in ['RB','WR','TE'] and len(rows)>=2 and total>0 and vol/total>=.02),'last_stat_row':None,'numeric_injury_adjustment':None,'future_workload_share':None}
 if len(rows):
  last=rows.iloc[-1];out['last_stat_row']={k:(int(last[k]) if k=='week' else float(last[k]) if k not in ['game_id'] else last[k]) for k in ['game_id','week','attempts','carries','rushing_yards','receptions','targets','receiving_yards']}
  positive=rows[rows.volume>0]
  out['last_positive_volume_week']=int(positive.week.max()) if len(positive) else None
 return out

soup=BeautifulSoup(gzip.open(P/'sources/0.html.gz','rb').read(),'html.parser')
register=[]
for team,table in zip(['HOU','IND'],soup.find_all('table')):
 for tr in table.find_all('tr')[1:]:
  c=[c.get_text(' ',strip=True) for c in tr.find_all(['th','td'])]
  assert len(c)==4,c
  pos,name,inj,practice=c
  r=player(team,name)
  r.update(injury=inj,practice_estimate=practice,practice_date='2026-11-16',practice_is_estimate=True,game_status=None,status_source_url=manifest[0]['url'],status_checked_at=manifest[0]['checked_at'],eligibility_reason='No formal Week11 Out designation in this source. Practice nonparticipation or roster tag is not a game-status designation.')
  if team=='IND':
   r['source_context_url']=manifest[2]['url']
   if name in ['Ahmad Gardner','Charvarius Ward','Bernhard Raimann']:r['absence_timing']='New Week10 in-game exit per owning Monday notebook; upcoming participation unknown.'
   elif name in ['Jaylon Carlies','Will Mallory','Jalen Travis','Luke Rhodes','Jerry Tillery']:r['absence_timing']='Missed Week10 per owning Monday notebook; upcoming participation unknown.'
   else:r['absence_timing']='Not established by the checked source.'
  else:r['absence_timing']='Not established by the checked Week11 practice report.'
  register.append(r)

roles=[]
for absent,replacement,position in [('Mo Alie-Cox','Drew Ogletree','TE'),('Akeem Davis-Gaither','CJ Allen','LB')]:
 a=player('IND',absent);b=player('IND',replacement)
 a.update(game_status=None,availability='Injured Reserve confirmed by owning Week11 depth-chart article',status_source_url=manifest[1]['url'],status_checked_at=manifest[1]['checked_at'],numeric_eligibility=False,eligibility_reason='IR-only absence outside existing same-week formally Out skill contract.' if position=='TE' else 'Linebacker outside the existing skill contract.')
 register.append(a)
 roles.append({'absent_player':a['gsis_id'],'replacement':b,'role_evidence':'Moves up one TE depth-chart place, not named starting TE and not a workload allocation.' if position=='TE' else 'Named MLB1 after prior player IR; depth chart is explicitly unofficial.','source_url':manifest[1]['url'],'checked_at':manifest[1]['checked_at'],'replacement_point_effect':None,'replacement_workload_prediction':None})

# Dated owning Nov17 transactions supersede Monday participation context, not the original estimates.
for team,name,source_index in [('HOU','Azeez Al-Shaair',7),('IND','Jaylon Carlies',8)]:
 r=next(r for r in register if r['team']==team and r['reported_name']==name)
 r.update(availability='Reserve/Injured confirmed by owning Nov17 transaction',availability_source_url=manifest[source_index]['url'],availability_checked_at=manifest[source_index]['checked_at'],numeric_eligibility=False,eligibility_reason='Linebacker and IR absence outside the existing skill-only numerical contract; effect unknown, not zero.')
 r['absence_timing']+=' Subsequent owning Nov17 transaction confirms Reserve/Injured.'
 if team=='IND':r['source_date_caveat']='Article headline/subtitle and publication identify Tuesday Nov17; final boilerplate says Monday. IR placement itself is stated explicitly in the transaction body; exact transaction day not independently resolved.'

# Available return candidates are facts, not a cleared or projected replacement assignment.
mont=next(r for r in register if r['reported_name']=='David Montgomery')
mont['absence_timing']='Owning Nov14 transaction ruled him out for Week10; current FP estimate is not Week11 clearance.'
mont['source_context_url']=manifest[4]['url']
return_context={'player':mont['gsis_id'],'owning_player_log_url':manifest[3]['url'],'owning_player_log_last_rushing_week':5,'candidate_replacement_for':next(r['gsis_id'] for r in register if r['reported_name']=='Woody Marks'),'role_status':'Conditional return candidate only. Neither start nor share confirmed by checked owning sources.','numeric_point_effect':None,'future_workload_share':None}
core=json.loads((C/'current_forecasts.json').read_text());event=next(g for g in core['games'] if g['event_id']=='401873066')
assert event['game_id']=='2026_11_IND_HOU'
assert len(register)==27
out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Week11 IND-HOU only. 25 Monday practice-estimate entries plus 2 owning-source IR entries. Not a league-wide injury clearance.','event_id':event['event_id'],'game_id':event['game_id'],'kickoff':event['date'],'baseline':{k:event[k] for k in ['raw_margin_home','display_margin_home','injury_numeric_adjustment']},'forecast_mutated':False,'numeric_scenarios':[],'register':register,'replacement_role_evidence':roles,'conditional_return_context':return_context,'limits':['No formal current-week skill-Out event established by the checked practice report. Two later linebacker IR transactions are factual updates, not numerical skill scenarios.','DNP does not mean Out; FP does not mean cleared.','IR-only, OL, defense and special teams are outside the existing numerical skill contract, not zero effects.','No numeric replacement or return-workload model.','Existing skill coefficient is observational and its coefficient-only interval includes zero; no QB stacking.','Mixed realized-history reference already includes continuing absences and replacements.','Roster injury tags may conflict with fresher owning sources; owning dated statements govern the factual register.','No QB-to-individual-stat pipeline.'],'provenance':{'core_path':str((C/'current_forecasts.json').relative_to(R)),'core_sha256':sha(C/'current_forecasts.json'),'stats_sha256':sha(C/'sources/player_stats_2026.csv'),'players_sha256':sha(C/'sources/players.csv'),'games_sha256':sha(C/'sources/games.csv'),'stats_source_url':'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv','stats_observed_at':'2026-11-17T13:11:24.949989+00:00','cutoff':'2026-11-17','completed_2026_reg_games':len(prior),'sources':manifest}}
(P/'companion.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(json.dumps({'entries':len(register),'role_pairs':len(roles),'unresolved_ids':0,'numeric_scenarios':0,'core_unchanged':sha(C/'current_forecasts.json')==out['provenance']['core_sha256'],'baseline':out['baseline'],'volume_gates':[(r['name'],r['trailing_share']) for r in register if r['established_skill_volume_gate']]},indent=2))
