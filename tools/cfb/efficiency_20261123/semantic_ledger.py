"""Auditable source-semantic ledger, development v2, no forecasts.
Every source play is retained, including exclusions. A review is a distinct
unresolved adjudication, never fixed by searching the quoted original ruling.
"""
import collections,gzip,hashlib,json,pathlib,re,os
ROOT=pathlib.Path('/tmp/edith');OUT=pathlib.Path(os.environ.get('CFB_AUDIT_OUTPUT','/tmp/deep-research/cfb-rework'));OUT.mkdir(exist_ok=True,parents=True)
PASS={'24','3','7','67','26','63','36'};RUN={'5','68'};INT={'26','63','36'}
SPECIAL={'12','14','18','32','34','37','38','52','53','59','60'}
FUMBLE={'9','29','39','69'}
def adjudicate(p,offense,teams):
 text=p.get('text','');lower=text.lower();current=re.split(r'\(original play:',lower,maxsplit=1)[0]
 original_present='(original play:' in lower
 typ=str((p.get('type')or{}).get('id'));a=p.get('start')or{};b=p.get('end')or{}
 if not isinstance(a,dict)or not isinstance(b,dict):return 'quarantine','invalid_start_end_state',None,[]
 flags=[]
 if re.search(r'\breview\b|\boverturn|\brevers|\bupheld\b|\bconfirmed\b',current):flags.append('review_annotation')
 if original_present:flags.append('original_ruling_quoted')
 if re.search(r'\bno play\b|\bnullified\b',current):flags.append('current_no_play')
 if re.search(r'\bpenalty\b',current)or p.get('isPenalty')or typ=='8':flags.append('current_penalty')
 if re.search(r'\bkneel',current):flags.append('kneel')
 if re.search(r'\bspike\b',current):flags.append('spike')
 if typ in FUMBLE or re.search(r'\bfumbl',current):flags.append('fumble')
 if typ=='20' or re.search(r'\bsafety\b',current):flags.append('safety')
 if typ in SPECIAL:flags.append('special_teams')
 # No adjudication from a superseded quote. Even clear-looking reviews are held
 # until source fixtures and score/state transitions validate their final ruling.
 if 'review_annotation'in flags:return 'quarantine','review_requires_reconciliation',None,flags
 if 'current_no_play'in flags:return 'exclude','current_no_play_or_nullified',None,flags
 if 'current_penalty'in flags:return 'quarantine','penalty_requires_adjudication',None,flags
 if 'kneel'in flags:return 'exclude','clock_kneel',None,flags
 if 'spike'in flags:return 'exclude','clock_spike',None,flags
 if 'special_teams'in flags:return 'separate','special_teams_not_offense_efficiency',None,flags
 if 'fumble'in flags:return 'quarantine','fumble_scrimmage_vs_return_yards_unresolved',None,flags
 if 'safety'in flags:return 'quarantine','safety_unit_attribution_unresolved',None,flags
 if typ not in PASS|RUN:return 'exclude','non_selected_play_type',None,flags
 if p.get('period',{}).get('number') not in [1,2,3,4]:return 'separate','overtime_or_missing_period',None,flags
 if str(a.get('team',{}).get('id',''))!=offense or offense not in teams:return 'quarantine','drive_start_possession_mismatch',None,flags
 down=a.get('down');distance=a.get('distance');gain=p.get('statYardage')
 if down not in [1,2,3,4]or not isinstance(distance,(int,float))or distance<=0 or not isinstance(gain,(int,float)):return 'quarantine','missing_down_distance_yardage',None,flags
 # A completion/run must leave the offense in possession unless it scores.
 # This catches mislabeled turnovers instead of treating return yards as offense.
 endteam=str(b.get('team',{}).get('id',''))
 if typ in RUN|{'24'} and endteam and endteam!=offense:
  # A failed fourth down is ordinary offensive failure, not missing data.
  if down==4 and gain<distance and re.search(r'turnover on downs',current):return 'accept','verified_failed_fourth_down',0,flags
  # Older feeds omit narrative turnover wording. Require a full structured
  # turnover-on-downs transition, no score, and consistent field movement.
  start_yard=a.get('yardLine');end_yard=b.get('yardLine')
  movement=(end_yard-start_yard)if isinstance(start_yard,(int,float))and isinstance(end_yard,(int,float))else None
  start_yte=a.get('yardsToEndzone');direction=None
  if isinstance(start_yard,(int,float))and isinstance(start_yte,(int,float))and start_yard!=50:
   if abs(start_yte-(100-start_yard))<1e-9:direction=1
   elif abs(start_yte-start_yard)<1e-9:direction=-1
  field_ok=movement is not None and direction is not None and abs(movement-direction*gain)<1e-9
  if down==4 and gain<distance and b.get('down')==1 and endteam in teams and p.get('scoringPlay')is False and p.get('_verified_next_drive_possession')is True and field_ok:return 'accept','structured_failed_fourth_down',0,flags
  return 'quarantine','ordinary_play_changes_possession',None,flags
 if typ=='3' and gain!=0:return 'quarantine','incompletion_nonzero_yards',None,flags
 if typ=='7' and gain>0:return 'quarantine','sack_positive_yards',None,flags
 if typ in INT|{'3','7'}:success=0
 else:success=int(gain>=(.5 if down==1 else .7 if down==2 else 1.)*distance)
 return 'accept','ordinary_regulation_scrimmage',success,flags

def resolve_duplicates(rows):
 # Revision ordering is evidence to inspect, not permission to assume latest wins.
 by=collections.defaultdict(list)
 for r in rows:by[r['play_id']].append(r)
 for pid,group in by.items():
  if not pid or pid=='None':
   for r in group:r.update(status='quarantine',reason='missing_or_invalid_play_id',success=None)
  elif len({r['play_sha256']for r in group})>1:
   for r in group:r.update(status='quarantine',reason='duplicate_conflicting_id_all_occurrences',success=None)
  elif len(group)>1:
   for r in group[1:]:r.update(status='exclude',reason='duplicate_identical_id',success=None)
 return rows

def state_score(p):return {s:p.get(s+'Score')for s in ['home','away']}
def main():
 manifest=json.load(open(os.environ.get('CFB_AUDIT_MANIFEST',str(ROOT/'tools/cfb/current_season_20261123/player_sources.json'))));
 if isinstance(manifest,dict):manifest=list(manifest.values())
 counts=collections.Counter();games=[];accepted=[];ledger=[];fixture_candidates=collections.defaultdict(list)
 for r in manifest:
  f=pathlib.Path(r['path']);raw=f.read_bytes();decoded=gzip.decompress(raw)if f.suffix=='.gz'else raw;expected=r.get('raw_sha256',r.get('sha256'));assert hashlib.sha256(decoded if 'raw_sha256'in r else raw).hexdigest()==expected;r['sha256']=expected;d=json.loads(decoded);c=d['header']['competitions'][0];eid=str(c['id']);assert eid==r['event_id'];teams={str(t['team']['id']):t['team']['displayName']for t in c['competitors']};home=next(str(t['team']['id'])for t in c['competitors']if t['homeAway']=='home');final={t['homeAway']:int(t['score'])for t in c['competitors']};pairs=[(dr,p)for dr in d.get('drives',{}).get('previous',[])for p in dr.get('plays',[])];terminal=state_score(pairs[-1][1])if pairs else{};game_hold=terminal!=final;seen={};prev={'home':0,'away':0};score_decreases=[];duplicate_conflicts=[];source_rows=[]
  for i,(dr,p)in enumerate(pairs):
   p=dict(p)
   # Cross-drive corroboration is derived from source sequence, not narrative.
   if i+1<len(pairs):
    nd,np_=pairs[i+1];endteam=str((p.get('end')or{}).get('team',{}).get('id',''));nextteam=str(nd.get('team',{}).get('id',''))
    p['_verified_next_drive_possession']=(str(nd.get('id'))!=str(dr.get('id')) and nextteam==endteam and str((np_.get('start')or{}).get('team',{}).get('id',''))==endteam)
   pid=str(p.get('id',''));ph=hashlib.sha256(json.dumps({k:v for k,v in p.items()if not k.startswith('_')},sort_keys=True).encode()).hexdigest();off=str(dr.get('team',{}).get('id',''));status,reason,success,flags=adjudicate(p,off,teams);score=state_score(p)
   if not pid:status,reason,success='quarantine','missing_play_id',None
   elif pid in seen:
    same=seen[pid]==ph;status,reason,success=('exclude','duplicate_identical_id',None)if same else('quarantine','duplicate_conflicting_id',None)
    if not same:duplicate_conflicts.append(pid)
   seen[pid]=ph
   if all(isinstance(score[s],(int,float))and isinstance(prev[s],(int,float))for s in score):
    if any(score[s]<prev[s]for s in score):score_decreases.append(pid)
   row=dict(event_id=eid,drive_id=str(dr.get('id','')),play_id=pid,source_sha256=r['sha256'],play_sha256=ph,source_path=str(f.relative_to(ROOT))if f.is_relative_to(ROOT)else str(f),source_url='https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event='+eid,source_order=i,sequence_number=p.get('sequenceNumber'),modified=p.get('modified'),wallclock=p.get('wallclock'),date=c['date'],offense_id=off,offense=teams.get(off),defense_id=next((t for t in teams if t!=off),None),start=p.get('start'),end=p.get('end'),period=p.get('period'),clock=p.get('clock'),score_before_observed=prev,score_after_observed=score,type=p.get('type'),stat_yardage=p.get('statYardage'),scoring_play=p.get('scoringPlay'),text=p.get('text'),status=status,reason=reason,flags=flags,success=success,game_quarantined=game_hold)
   row['defense']=teams.get(row['defense_id']);prev=score;source_rows.append(row)
   for flag in flags:
    if len(fixture_candidates[flag])<3:fixture_candidates[flag].append(row)
   if eid=='401856670'and pid=='401856670470':fixture_candidates['publisher_regression']=[row]
  if duplicate_conflicts:
   game_hold=True
   for row in source_rows:
    row['game_quarantined']=True
    if row['play_id']in duplicate_conflicts:row.update(status='quarantine',reason='duplicate_conflicting_id_all_occurrences',success=None)
  source_rows=resolve_duplicates(source_rows)
  for row in source_rows:
   counts[row['status']+':'+row['reason']]+=1
   if row['status']=='accept'and not row['game_quarantined']:
    st=row['start'];accepted.append(dict(event_id=eid,play_id=row['play_id'],drive_id=row['drive_id'],source_sha256=r['sha256'],date=row['date'],offense_id=row['offense_id'],offense=row['offense'],defense_id=row['defense_id'],defense=row['defense'],down=st['down'],distance=st['distance'],yards=row['stat_yardage'],success=row['success'],period=row['period']['number'],kind='pass'if str(row['type']['id'])in PASS else'rush',garbage_time_filtered=False))
  ledger.extend(source_rows);games.append(dict(event_id=eid,source_sha256=r['sha256'],source_url='https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event='+eid,terminal_score_match=terminal==final,final=final,terminal=terminal,game_quarantined=game_hold,duplicate_conflicts=duplicate_conflicts,score_decreases=score_decreases,ledger_rows=len(source_rows)))
 for name,rows in [('semantic_ledger.jsonl.gz',ledger),('raw_success_plays.jsonl.gz',accepted)]:
  with gzip.open(OUT/name,'wt')as f:
   for row in rows:f.write(json.dumps(row)+'\n')
 (OUT/'semantic_fixtures.json').write_text(json.dumps(dict(fixture_candidates),indent=2));(OUT/'game_reconciliation.json').write_text(json.dumps(games,indent=2));summary=dict(status='Research ledger, not model admission',games=len(games),ledger_rows=len(ledger),accepted_nonquarantined_plays=len(accepted),quarantined_games=sum(g['game_quarantined']for g in games),games_with_score_decrease=sum(bool(g['score_decreases'])for g in games),counts=dict(counts));(OUT/'semantic_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
