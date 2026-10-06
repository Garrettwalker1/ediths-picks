#!/usr/bin/env python3
"""Grade frozen margin-Elo v1 Week 4 raw home margins against the last pre-kickoff FanDuel IL spread that was published on the board.
Book lines come from published_week4_book_lines_snapshot.json (the index.html rows as of the Oct 5 evening publish, each with its IL capture time).
The raw capture ledgers for Oct 2-5 were lost in the Oct 5 workspace wipe, so this snapshot is the surviving record.
Usage: build_grade.py espn_scoreboard.json  (run from repo root, clean baseline only)"""
import json,re,sys,datetime as dt,pathlib
R=pathlib.Path(__file__).resolve().parents[4]
AL={'LA':'LAR','WAS':'WSH'}
C=lambda t:AL.get(t,t)
pred={ (C(x['away']),C(x['home'])):x for x in json.load(open(R/'tools/model_nfl_v3_2/point_in_time/elo_week4_predictions.json'))}
snap=json.load(open(R/'tools/nfl/week4_2026/grade/published_week4_book_lines_snapshot.json'))
ev=json.load(open(sys.argv[1]))['events']
cap=lambda s:re.search(r'captured (.*?) CT',s).group(1)
rows=[]
for s in snap:
    a,h=[C(t) for t in s['matchup'].split(' at ')]
    e=[e for e in ev if{C(c['team']['abbreviation']) for c in e['competitions'][0]['competitors']}=={a,h}]
    assert len(e)==1,(a,h);e=e[0];assert e['status']['type']['name']=='STATUS_FINAL'
    comp=e['competitions'][0]['competitors'];H=next(c for c in comp if c['homeAway']=='home');A=next(c for c in comp if c['homeAway']=='away')
    assert C(H['team']['abbreviation'])==h
    m=re.match(r'(\w+) (-?[\d.]+)',s['market']);fav,sp=m.group(1),abs(float(m.group(2)))
    book=sp if C(fav)==h else -sp
    assert C(fav) in(a,h),s
    p=pred[(a,h)];model=p['raw_margin_home'];act=int(H['score'])-int(A['score'])
    me,be=abs(model-act),abs(book-act);w='model' if me<be-1e-8 else 'book' if be<me-1e-8 else 'tie'
    kick=dt.datetime.fromisoformat(s['kickoff'].replace('Z','+00:00'))
    rows.append(dict(week=4,event=f"{a} at {h}",event_id=e['id'],game_id=p['game_id'],model_margin_home=model,book_margin_home=book,final=f"{A['team']['abbreviation']} {A['score']}, {H['team']['abbreviation']} {H['score']}",actual_margin_home=act,model_abs_error=round(me,10),book_abs_error=round(be,10),winner=w,eligible=True,book_captured_at_ct=cap(s['book']),book_state='IL',book_source_file='tools/nfl/week4_2026/grade/published_week4_book_lines_snapshot.json',book_source_url=None,final_source_url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week=4',lineage='margin-Elo v1, point-in-time (completed game scores only); measurement, not a validated edge'))
assert len(rows)==16
out=R/'tools/nfl/week4_2026/grade/week4_grade.json'
out.write_text(json.dumps({'label':'Margin-Elo v1 Week 4 grade (point-in-time scores-only model; trails book on locked test)','method':'Lower absolute final home-margin error versus the last pre-kickoff FanDuel IL home spread published on the board; book home margin = +spread if home is favorite else -spread.','rows':rows},indent=2)+'\n')
tr=json.load(open(R/'model_tracking.json'))
assert not any(r['week']==4 for r in tr['nfl']['grades'])
tr['nfl']['grades'].extend(rows)
for r in rows:tr['nfl']['record'][r['winner'] if r['winner']!='tie' else 'ties']+=1
tr['nfl']['record']['graded']+=16
tr['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
(R/'model_tracking.json').write_text(json.dumps(tr,indent=2)+'\n')
c={k:sum(r['winner']==k for r in rows) for k in('model','book','tie')}
print(c,'MAE model',round(sum(r['model_abs_error'] for r in rows)/16,3),'book',round(sum(r['book_abs_error'] for r in rows)/16,3),'record',tr['nfl']['record'])
for r in rows:print(r['event'],r['final'],'model',r['model_margin_home'],'book',r['book_margin_home'],r['winner'],r['book_captured_at_ct'])
