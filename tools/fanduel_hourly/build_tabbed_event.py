"""One event, six categories, rendered across official UI tabs. Each row keeps its own tab time/URL."""
import pathlib,json,datetime,tempfile,shutil,hashlib,sys
from build_player_comparison import build_event,load,stamp,R
from player_label_candidate import parse_label
P=R/'tools/fanduel_hourly/player_captures/week11-first-20261117';base='https://sportsbook.fanduel.com/football/nfl/indianapolis-colts-@-houston-texans-36305232';parts=[];raws=['td','pass','rush','rec-complete']
for name in raws:
 source=pathlib.Path('/tmp/ind-hou-'+name+'.json');blob=source.read_bytes();(P/(name+'.json')).write_bytes(blob);x=load(source);x=json.loads(x['content'])if'content'in x else x;assert x['url']==base or x['url'].startswith(base+'?tab=');assert x['state_evidence']and all('Illinois Gaming Board'in s for s in x['state_evidence']);assert all(m['expanded']=='true'and not m['show_more']and m['selections']for m in x['markets']);parts.append(x)
start=min(x['at']for x in parts);end=max(x['at']for x in parts);assert(stamp(end)-stamp(start)).total_seconds()<600
markets=[m for x in parts for m in x['markets']];index={}
for x in parts:
 for m in x['markets']:
  for v in m['selections']:
   r=parse_label(v['label'])
   if r:
    k=(r['player_name'],r['market'],r['side']);assert k not in index;index[k]=(x['at'],x['url'])
assert {k[1]for k in index}=={'anytime_td','passing_yards','passing_tds','rushing_yards','receiving_yards','receptions'}
assembled=dict(at=end,url=base,state_evidence=parts[0]['state_evidence'],markets=markets,capture_window_start=start,capture_window_end=end,note='Temporary six-category verification input; original tab snapshots retained. Outgoing rows get actual source tab time and URL, not this assembled time.')
with tempfile.TemporaryDirectory()as tmp:
 t=pathlib.Path(tmp)
 for f in ['IND.json','HOU.json','manifest.json']:shutil.copyfile(P/f,t/f)
 (t/'rendered.json').write_text(json.dumps(assembled))
 game=next(g for g in load(R/'tools/nfl/current_season_20261117/current_forecasts.json')['games']if g['event_id']=='401873066');e=build_event(t,game,base,load(R/'tools/nfl/week11_2026/td_projection_snapshot.json'),load(R/'tools/nfl/week11_2026/td_week11_primary.json'),load(R/'player_projections.json'),datetime.datetime.now(datetime.timezone.utc))
for row in e['rows']:
 vals={index[row['player_name'],row['market'],s['side']]for s in row['selections']};assert len(vals)==1;row['captured_at'],row['source_url']=vals.pop()
e.update(capture_window_start=start,capture_window_end=end,tabbed_capture=True,source_urls=sorted({x['url']for x in parts}),capture_note='Actual UI tab snapshots over a short window, not simultaneous. Each row retains its own tab capture timestamp/URL. All six standard categories observed; no alt or college props.')
(P/'rendered_combined_audit.json').write_text(json.dumps(assembled,indent=2)+'\n');(P/'event.json').write_text(json.dumps(e,indent=2)+'\n');print(json.dumps(e['coverage'],indent=2));print(start,end)
