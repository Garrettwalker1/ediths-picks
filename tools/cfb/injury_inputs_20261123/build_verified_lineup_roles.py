"""Historical lineup and role facts, never prospective workload or injury point estimates."""
import os,pathlib,json,csv,gzip,re,collections,unicodedata
O=pathlib.Path(__file__).parent;B=pathlib.Path(os.environ.get('CFB_CURRENT_ROOT',str(O/'baseline')))
def norm(s):
 s=unicodedata.normalize('NFKD',s)
 if ','in s:
  a,b=s.split(',',1);s=b+' '+a
 return re.sub('[^a-z0-9]','',s.lower())
def main():
 d=json.load(open(O/'unt_official_lineup_harvest.json'));roster=json.load(gzip.open(B/'sources/rosters/249.json.gz','rt'));idx=collections.defaultdict(list)
 for g in roster['athletes']:
  for a in g['items']:idx[norm(a['displayName']),a.get('jersey')].append(a)
 rows=[];unresolved=[]
 for r in d['rows']:
  candidates=idx[norm(r['name']),r['jersey']];r=dict(r)
  if len(candidates)==1:
   a=candidates[0];r.update(espn_id=a['id'],espn_name=a['displayName'],roster_position=a.get('position',{}).get('abbreviation'),join_method='unique full normalized name plus jersey in team 249 current roster')
  else:r.update(espn_id=None,join_method='UNRESOLVED');unresolved.append(r)
  rows.append(r)
 # A source-local roster URL can bridge historical jersey changes, only after a unique
 # team/name/jersey row independently grounded that exact URL to one ESPN identity.
 by_url=collections.defaultdict(set)
 for r in rows:
  if r['athlete_source_url']and r['espn_id']:by_url[r['athlete_source_url']].add(r['espn_id'])
 unresolved=[]
 for r in rows:
  ids=by_url.get(r['athlete_source_url'],set())
  if not r['espn_id']and len(ids)==1:
   r.update(espn_id=next(iter(ids)),join_method='same exact official roster URL as uniquely name-and-jersey-matched row; historical jersey changed')
  if not r['espn_id']:unresolved.append(r)
 manifest=sorted(d['manifest'],key=lambda x:x['date_candidates'][0][6:]+x['date_candidates'][0][:5]);previous=None;changes=[];quality=[]
 for m in manifest:
  bid=m['boxscore_id'];off=[r for r in rows if r['boxscore_id']==bid and 'Offensive Starters'in r['table']];deff=[r for r in rows if r['boxscore_id']==bid and 'Defensive Starters'in r['table']];ol={r['espn_id']or r['athlete_source_url']for r in off if r['position']=='OL'}
  if previous:changes.append(dict(date=m['date_candidates'][0],boxscore_id=bid,prior_boxscore_id=previous[0],added_ol=sorted(ol-previous[1]),removed_ol=sorted(previous[1]-ol),interpretation='observed starting-five transition, no injury cause assigned'))
  previous=(bid,ol)
  if len(off)!=11 or len(deff)!=11:quality.append(dict(boxscore_id=bid,offensive_starters=len(off),defensive_starters=len(deff),status='INCOMPLETE_SOURCE_LINEUP_DO_NOT_IMPUTE_MISSING_PLAYER'))
  assert len(off)==11 and len(ol)==5
 stats=list(csv.DictReader(open(B/'current_player_games.csv')));exact=json.load(open(O/'injury_exact_baseline_reconciliation.json'));baseline=[]
 for team in ['North Texas Mean Green','Houston Cougars']:
  g=next(g for g in exact['rows']if any(s['team']==team for s in g['sides'].values()));side=next(s for s in g['sides'].values()if s['team']==team);tot=collections.defaultdict(lambda:collections.Counter())
  for r in stats:
   if r['team']==team and r['event_id']in side['history_event_ids']and r['date']<g['cutoff_date']and float(r['pass_att'])>0:
    for k in ['pass_att','pass_cmp','pass_yds','pass_td','pass_int']:tot[r['player_id'],r['player_name']][k]+=float(r[k])
  assert sum(t['pass_att']for t in tot.values())==side['totals']['pass_att']
  baseline.append(dict(team=team,forecast_event_id=g['event_id'],cutoff=g['cutoff_date'],history_event_ids=side['history_event_ids'],passing_total=side['totals']['pass_att'],passers=[dict(espn_id=k[0],name=k[1],**v,baseline_share=v['pass_att']/side['totals']['pass_att'])for k,v in tot.items()]))
 plays=[]
 with gzip.open(O/('unt_tulane_ledger_subset.jsonl.gz' if (O/'unt_tulane_ledger_subset.jsonl.gz').exists() else 'semantic_ledger.jsonl.gz'),'rt')as f:
  for l in f:
   r=json.loads(l)
   if r['event_id']=='401862835'and r['offense_id']=='249':plays.append(r)
 # Use source order. ESPN displayed clocks differ from play text and have placeholder 15:00 rows.
 boundary=next(i for i,p in enumerate(plays)if p['period']['number']==3 and '(12:15)'in p['text']);first_tyre_pass=next(i for i,p in enumerate(plays)if p['period']['number']==4 and '(03:54)'in p['text']);runphase=plays[boundary+1:first_tyre_pass];rush=[p for p in runphase if p['status']=='accept'and p['type']['text']in ['Rush','Rushing Touchdown']];assert len(rush)==29
 assert not any('pass 'in p['text'].lower()for p in runphase)
 counts=collections.Counter()
 for p in rush:
  match=re.search(r'#(\d+)\s+[A-Za-z. ]+?\s+rush',p['text'])
  counts[match[1]if match else 'UNRESOLVED']+=1
 assert sum(counts.values())==29 and 'UNRESOLVED'not in counts
 phases=dict(event_id='401862835',last_jimerson_snap_id=plays[boundary]['play_id'],last_jimerson_source_order=plays[boundary]['source_order'],boundary_play_status=plays[boundary]['status'],note='Boundary pass includes interference and is not counted as a valid pass-attempt/stat-rate observation',run_phase_play_ids=[p['play_id']for p in rush],run_phase_accepted_rushes=29,run_phase_carrier_jerseys=dict(counts),first_tyre_pass_play_id=plays[first_tyre_pass]['play_id'],ordering='source_order not clock sorting',quarterback_snap_attribution='UNKNOWN for individual RB carries; official recap confirms multiple direct snaps but does not identify all snap-takers',prospective='UNRESOLVED: do not convert emergency phase into UAB usage forecast')
 result=dict(official_lineup_rows=len(rows),espn_unique_identity_matches=len(rows)-len(unresolved),unresolved=unresolved,rows=rows,quality_flags=quality,ol_transitions=changes,baseline_passing=baseline,emergency_phase=phases,admission='DESCRIPTIVE_DATA_ONLY_NO_PRODUCTION_CHANGE',critical_role_rule='James Tyre is a roster WR who actually played emergency QB. Fixed roster-position filtering is insufficient. Use event-scoped, explicitly sourced role overrides; do not recast all WR passes as QB or preserve this emergency role as ordinary trick-play share.',limitations=d['limitations'])
 (O/'unt_verified_role_lineup_evidence.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['rows','unresolved']},indent=2));print('unresolved',unresolved[:5])
if __name__=='__main__':main()
