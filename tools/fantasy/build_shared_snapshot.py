#!/usr/bin/env python3
"""Build shared-player coverage from the current verified fantasy snapshot."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[2]
f=json.loads((root/'fantasy.json').read_text()); rows={}
def key(s):return re.sub('[^a-z]','',re.sub(r'\b(jr|sr|ii|iii|iv)\b','',s.lower()))
for l in f['leagues']:
 for p in l['players']:
  k=key(p['name']);r=rows.setdefault(k,{'player_id':k,'player_name':p['name'],'team':p.get('nfl_team'),'position':p.get('position'),'leagues':[],'rostered_league_names':[],'rostered_player_names':[],'injury_status':None,'practice_status':None,'game_status':None,'headline':'No injury flag in current ESPN Fantasy status','detail':None,'source_name':'ESPN Fantasy status; current ESPN/Sleeper rosters','source_url':p.get('source_url'),'source_published_at':None,'observed_at':f['updated_at'],'stale':False})
  if l['id'] not in [x['id'] for x in r['leagues']]:r['leagues'].append({'id':l['id'],'name':l['league_name'],'team_name':l['team']['name']});r['rostered_league_names'].append(l['league_name'])
  if p['name'] not in r['rostered_player_names']:r['rostered_player_names'].append(p['name'])
  if p.get('injury_status'):r.update(injury_status=p['injury_status'],headline='ESPN Fantasy status: '+p['injury_status'],detail=p.get('injury_detail'),source_name=p.get('injury_source'),source_url=p.get('injury_source_url'),source_published_at=p.get('injury_provider_updated_at'))
for r in rows.values():r['roster_count']=len(r['leagues'])
out={'schema_version':'1.0.0','generated_at':f['updated_at'],'week':max(l.get('week') or 0 for l in f['leagues']),'coverage':{'league_count':len(f['leagues']),'rostered_player_count':len(rows),'source_status':'partial_x_unavailable','source_snapshot_at':f['updated_at'],'x_note':'Public X unavailable; X coverage partial.'},'sources':[{'name':f['injury_check']['source'],'url':f['injury_check']['source_url'],'observed_at':f['updated_at']}],'players':list(rows.values())}
(root/'fantasy_rostered_injuries.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(len(rows),'players;',sum(r['roster_count']>1 for r in rows.values()),'shared')
