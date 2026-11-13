"""Publish only uniquely roster/ID-joined rendered player selections.
Partial event coverage is explicit. Does not change any model.
"""
import json,pathlib,collections,datetime,hashlib
from player_label_candidate import parse_label,attach_identity
R=pathlib.Path(__file__).resolve().parents[2];P=pathlib.Path(__file__).parent/'player_captures/20261113T214129161Z'
def load(f):return json.load(open(f))
x=load(P/'rendered.json');x=json.loads(x['content'])if'content'in x else x
assert 'new-england-patriots-@-detroit-lions-35605986'in x['url'];assert x['state_evidence'];assert len(x['markets'])==25
assert all(m['expanded']=='true'and not m['show_more']for m in x['markets'])
td=load(R/'tools/nfl/week10_2026/td_projection_snapshot.json');primary=load(R/'tools/nfl/week10_2026/td_week10_primary.json');generic=load(R/'player_projections.json');idx={}
for team in ['DET','NE']:
 roster=load(P/(team+'.json'));assert roster['season']['year']==2026
 for group in roster['athletes']:
  for a in group['items']:
   cross=[r for r in td['rows']if r['team']==team and str(r.get('espn_id'))==a['id']and r.get('player_id')]
   if len(cross)!=1:continue
   idx.setdefault(a['displayName'],[]).append(dict(player_id=cross[0]['player_id'],espn_id=a['id'],team_id=team))
rows=[]
for m in x['markets']:
 parsed=[parse_label(s['label'])for s in m['selections']];rows.extend(r for r in parsed if r)
assert len({(r['player_name'],r['market'],r['side'])for r in rows})==len(rows)
joined,gaps=attach_identity(rows,'401873053','2026-11-15T14:30Z','IL',x['at'],x['url'],idx)
by={};pr={r['player_id']:r for r in primary['ranked']};gp={r['player_id']:r for r in generic['players']}
for r in joined:
 key=(r['player_id'],r['market']);z=by.setdefault(key,{k:r[k]for k in ['player_id','espn_id','team_id','player_name','market','event_id','kickoff','state','captured_at','source_url']});z.setdefault('selections',[]).append(dict(side=r['side'],line=r['line'],price=r['price']))
for z in by.values():
 pid=z['player_id'];market=z['market'];z['model_value']=None;z['model_label']='Unavailable: no compatible published player projection'
 if market=='anytime_td'and pid in pr:
  r=pr[pid];assert r['team']==z['team_id']and r['opp']in ['NE','DET']and r['kick']==z['kickoff'];z.update(model_value=r['primary'],model_kind='probability',model_label='Owner-adopted Oct29 TD model; unvalidated',model_captured_at=primary['generated_at'])
 elif market in ['rushing_yards','receiving_yards','receptions']and pid in gp:
  r=gp[pid]
  if r['team']==z['team_id']:
   z.update(model_value=r[market]['median'],model_kind='median',model_label='Dated generic median, not current matchup/personnel adjusted',model_captured_at=generic['generated_at'])
 if market!='anytime_td':assert len(z['selections'])==2 and {s['side']for s in z['selections']}=={'over','under'}and len({s['line']for s in z['selections']})==1
counts=dict(collections.Counter(z['market']for z in by.values()));assert len(counts)==6,counts
out=dict(checked_at=x['at'],scope='PARTIAL: 1 of 13 upcoming NFL events. All six requested standard market categories observed on NE-DET; not full NFL recurring player-market restoration.',state='IL',event_id='401873053',matchup='New England Patriots at Detroit Lions',kickoff='2026-11-15T14:30Z',source_url=x['url'],model_inputs_changed=False,availability_note='Book listing and roster membership are not game clearance. Model figures retain their own older source times and have no new injury/workload adjustment. Book prices are comparisons only; no betting edge or current TN offer claimed.',coverage=dict(rendered_target_accordions=25,parsed_selections=len(rows),joined_selections=len(joined),unmatched_selections=len(gaps),market_player_rows=counts,other_events_not_captured=12),rows=list(by.values()),identity_gaps=gaps)
(R/'fanduel_player_comparisons.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['coverage'],indent=2))
