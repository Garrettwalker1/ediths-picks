#!/usr/bin/env python3
"""Grade immutable Week 3 raw margins against latest timestamped pre-kickoff IL quotes."""
import csv, datetime as dt, glob, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[4]
def read(p): return json.loads(pathlib.Path(p).read_text())
def stamp(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
raw=read(ROOT/'tools/nfl/week3_2026/game_predictions_raw.json')
score=read(sys.argv[1]); events=score['events']; assert len(raw)==len(events)==16
aliases={'LA':'LAR','WAS':'WSH'}
quotes=[]
for f in glob.glob(str(ROOT/'tools/ledger/*nfl_week3*csv')):
 for q in csv.DictReader(open(f,newline='')):
  if q.get('market_type')=='spread' and q.get('quote_status')=='open' and q.get('state')=='IL':
   q['file']=str(pathlib.Path(f).relative_to(ROOT));quotes.append(q)
# Monday DOM capture is a separate, preserved compact schema.
for f in glob.glob(str(ROOT/'tools/ledger/*nfl_week3*dom*csv')):
 for q in csv.DictReader(open(f,newline='')):
  assert q['state']=='IL' and q['event_name']=='Philadelphia Eagles @ Chicago Bears'
  quotes.append(dict(captured_at=q['captured_at'],event_name=q['event_name'],selection='Chicago Bears',line=q['home_spread'],file=str(pathlib.Path(f).relative_to(ROOT)),source_url=q['source_url']))
rows=[]
for g in raw:
 ids={aliases.get(g[k],g[k]) for k in ['home_team','away_team']}
 matches=[e for e in events if {c['team']['abbreviation'] for c in e['competitions'][0]['competitors']}==ids]
 assert len(matches)==1,(g['game_id'],matches)
 e=matches[0]; assert e['status']['type']['name']=='STATUS_FINAL'; comp=e['competitions'][0]['competitors']
 h=next(c for c in comp if c['homeAway']=='home'); a=next(c for c in comp if c['homeAway']=='away')
 assert h['team']['abbreviation']==aliases.get(g['home_team'],g['home_team'])
 cutoff=stamp(e['date']); matching=[q for q in quotes if q['event_name']==e['name'].replace(' at ',' @ ') and q['selection']==h['team']['displayName'] and stamp(q['captured_at'])<cutoff]
 assert matching,(e['name'],'missing pregame home spread')
 q=max(matching,key=lambda x:stamp(x['captured_at'])); assert q['line']
 # A home-team bet spread is the opposite sign of the book's projected home margin.
 m=float(g['model_margin_home_raw']); b=-float(q['line']); actual=int(h['score'])-int(a['score']); me=abs(m-actual);be=abs(b-actual)
 winner='model' if me<be-1e-8 else 'book' if be<me-1e-8 else 'tie'
 rows.append(dict(week=3,event=f"{a['team']['abbreviation']} at {h['team']['abbreviation']}",event_id=e['id'],game_id=g['game_id'],model_margin_home=m,book_margin_home=b,final=f"{a['team']['abbreviation']} {a['score']}, {h['team']['abbreviation']} {h['score']}",actual_margin_home=actual,model_abs_error=round(me,10),book_abs_error=round(be,10),winner=winner,eligible=True,book_captured_at=q['captured_at'],book_state='IL',book_source_file=q['file'],book_source_url=q.get('source_url') or None,final_source_url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week=3',lineage='frozen v3.2b; point-in-time feature leaks; not validated'))
assert len(rows)==16 and len({r['event_id'] for r in rows})==16
out=ROOT/'tools/nfl/week3_2026/grade/week3_grade.json'
out.write_text(json.dumps({'label':'Frozen v3.2b Week 3 grade (leaky lineage, not validated)', 'method':'Lower absolute final home-margin error versus latest timestamped pre-kickoff FanDuel IL home spread; book home margin = negative home-team spread. Raw model precision retained.', 'rows':rows},indent=2)+'\n')
track=read(ROOT/'model_tracking.json')
assert not any(r['week']==3 for r in track['nfl']['grades'])
track['nfl']['grades'].extend(rows)
for r in rows:track['nfl']['record'][r['winner'] if r['winner']!='tie' else 'ties']+=1
track['nfl']['record']['graded']+=len(rows)
track['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
(ROOT/'model_tracking.json').write_text(json.dumps(track,indent=2)+'\n')
print('Week 3:',{key:sum(r['winner']==key for r in rows) for key in ('model','book','tie')},'MAE',round(sum(r['model_abs_error'] for r in rows)/16,3),round(sum(r['book_abs_error'] for r in rows)/16,3))
for r in rows:print(r['event'],r['final'],'model',r['model_margin_home'],'book',r['book_margin_home'],'winner',r['winner'],r['book_source_file'])
