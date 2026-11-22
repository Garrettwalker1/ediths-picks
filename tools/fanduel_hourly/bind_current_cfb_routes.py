"""Bind metadata-only book routes to current source-grounded slate, exact team pair/time."""
import datetime,json,pathlib
from update import match,current_cfb_forecasts

def bind(repo,metadata):
 games=current_cfb_forecasts(repo);accepted=[];rejected=[]
 stamp=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
 for q in metadata['items']:
  found=[g for g in games if match(q['away'],g['away']) and match(q['home'],g['home'])]
  if len(found)!=1:rejected.append(dict(q,reason='ambiguous or unmatched current pair'));continue
  g=found[0]
  if stamp(q['kickoff'])!=stamp(g['date']):rejected.append(dict(q,event_id=g['event_id'],schedule_kickoff=g['date'],reason='book/schedule time conflict'));continue
  if stamp(g['date'])<=stamp(metadata['at']):rejected.append(dict(q,event_id=g['event_id'],reason='started'));continue
  accepted.append(dict(q,event_id=g['event_id'],kickoff=g['date']))
 return dict(observed_at=metadata['at'],source_url=metadata['url'],forecast_path=json.loads((pathlib.Path(repo)/'cfb_current_release.json').read_text())['forecast_path'],accepted=accepted,rejected=rejected)
