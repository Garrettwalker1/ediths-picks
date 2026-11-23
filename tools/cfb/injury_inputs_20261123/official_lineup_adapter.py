"""Reusable official lineup adapter with strict identity and data-quality gates."""
import os,json,gzip,pathlib,re,collections,unicodedata
O=pathlib.Path(__file__).parent;B=pathlib.Path(os.environ.get('CFB_CURRENT_ROOT',str(O/'baseline')))
def norm(s):
 if ','in s:
  a,b=s.split(',',1);s=b+' '+a
 return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).lower())
def role_for_attempt(roster_position,team_id,event_id,player_id,role_overrides):
 """No implicit permanent conversion of WR into QB; verified event role wins."""
 return role_overrides.get((str(team_id),str(event_id),str(player_id)),roster_position)
def join_lineup(data,team_id):
 roster=json.load(gzip.open(B/f'sources/rosters/{team_id}.json.gz','rt'));idx=collections.defaultdict(list)
 for g in roster['athletes']:
  for a in g['items']:idx[norm(a['displayName']),a.get('jersey')].append(a)
 rows=[]
 for r in data['rows']:
  r=dict(r);a=idx[norm(r['name']),r['jersey']];r['espn_id']=a[0]['id']if len(a)==1 else None;r['join_method']='unique team/full-name/jersey'if r['espn_id']else'UNRESOLVED';rows.append(r)
 bridges=collections.defaultdict(set)
 for r in rows:
  if r['athlete_source_url']and r['espn_id']:bridges[r['athlete_source_url']].add(r['espn_id'])
 for r in rows:
  ids=bridges.get(r['athlete_source_url'],set())
  if not r['espn_id']and len(ids)==1:r.update(espn_id=next(iter(ids)),join_method='exact official roster URL bridge across jersey change')
 quality=[];transitions=[];previous=None
 for m in sorted(data['manifest'],key=lambda x:x['date_candidates'][0][6:]+x['date_candidates'][0][:5]):
  local=[r for r in rows if r['boxscore_id']==m['boxscore_id']];off=[r for r in local if'Offensive Starters'in r['table']];deff=[r for r in local if'Defensive Starters'in r['table']];ol={r['espn_id']or r['athlete_source_url']for r in off if r['position']=='OL'}
  if len(off)!=11 or len(deff)!=11:quality.append(dict(boxscore_id=m['boxscore_id'],off_count=len(off),def_count=len(deff),admit_complete_unit_state=False))
  if len(ol)==5:
   if previous:transitions.append(dict(date=m['date_candidates'][0],boxscore_id=m['boxscore_id'],prior_boxscore_id=previous[0],added=sorted(ol-previous[1]),removed=sorted(previous[1]-ol)))
   previous=m['boxscore_id'],ol
  else:previous=None
 return dict(team_id=team_id,rows=rows,quality_flags=quality,ol_transitions=transitions,unique_matches=sum(r['espn_id']is not None for r in rows),total_rows=len(rows),limitations=['Observed starts are not snap counts, injury causes or prospective role probabilities','Current roster identity bridge is retrospective, not proof of pregame availability'])
def main():
 outputs=[]
 for slug,tid in [('unt','249'),('houston','248')]:
  data=json.load(open(O/f'{slug}_official_lineup_harvest.json'));out=join_lineup(data,tid);outputs.append(out)
 overrides={('249','401862835','5159360'):'QB_EMERGENCY'}
 assert role_for_attempt('WR','249','401862835','5159360',overrides)=='QB_EMERGENCY'
 assert role_for_attempt('WR','249','OTHER','5159360',overrides)=='WR'
 assert role_for_attempt('WR','OTHER','401862835','5159360',overrides)=='WR'
 assert role_for_attempt('QB','249','401862835','5175092',overrides)=='QB'
 assert len({r['boxscore_id']for r in outputs[0]['rows']})==11
 assert len({r['boxscore_id']for r in outputs[1]['rows']})==11
 assert any(f['boxscore_id']=='7208'and f['def_count']==10 for f in outputs[0]['quality_flags'])
 assert next(t for t in outputs[1]['ol_transitions']if t['boxscore_id']=='16252')['added']==[]
 assert all(r['espn_id']for r in outputs[0]['rows'])
 (O/'two_team_official_lineup_adapter.json').write_text(json.dumps(dict(teams=outputs,role_overrides=[dict(team_id=k[0],event_id=k[1],athlete_id=k[2],role=v,source_url='https://meangreensports.com/news/2026/11/21/football-mean-green-drop-heartbreaker-at-tulane')for k,v in overrides.items()],checks='9 explicit assertions passed; not nine independent unit tests',admission='DESCRIPTIVE_ONLY_NOT_DEPLOYED'),indent=2));print([(x['team_id'],x['total_rows'],x['unique_matches'],x['quality_flags'])for x in outputs]);print('9 assertions passed')
if __name__=='__main__':main()
