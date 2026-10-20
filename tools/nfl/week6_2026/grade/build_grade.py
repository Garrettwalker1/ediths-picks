#!/usr/bin/env python3
"""Grade frozen margin-Elo v1 Week 6 raw home margins (game_predictions_raw.json, unrounded) against the FanDuel Illinois spread captured Oct 13 7:12 AM CT (tools/nfl/week6_2026/fanduel_il_nfl_capture_20261013T1212Z.json). That capture is NOT a last pre-kickoff line: Thursday was 2 days later, Monday night 6 days later. Book lines never feed the model.
Usage: build_grade.py espn_scoreboard.json  (run from repo root)"""
import json,sys,datetime as dt,pathlib
R=pathlib.Path(__file__).resolve().parents[4]
AL={'LA':'LAR','WAS':'WSH'};C=lambda t:AL.get(t,t)
N={'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF','Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE','Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Miami Dolphins':'MIA','Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','San Francisco 49ers':'SF','Seattle Seahawks':'SEA','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WSH'}
cap=json.load(open(R/'tools/nfl/week6_2026/fanduel_il_nfl_capture_20261013T1212Z.json'));assert 'Illinois' in cap['footer']
book={}
for it in cap['items']:
    f=[s.strip() for s in it['text'].split('\n')];a,h=N[f[0]],N[f[1]];book[(a,h)]=-float(f[7])  # home spread -> expected home margin
assert len(book)==14
pred={(C(x['away']),C(x['home'])):x for x in json.load(open(R/'tools/nfl/week6_2026/game_predictions_raw.json'))}
ev=json.load(open(sys.argv[1]))['events'];rows=[]
for (a,h),p in sorted(pred.items(),key=lambda kv:kv[1]['game_id']):
    e=[e for e in ev if {C(c['team']['abbreviation']) for c in e['competitions'][0]['competitors']}=={a,h}];assert len(e)==1;e=e[0];assert e['status']['type']['name']=='STATUS_FINAL'
    comp=e['competitions'][0]['competitors'];H=next(c for c in comp if c['homeAway']=='home');A=next(c for c in comp if c['homeAway']=='away');assert C(H['team']['abbreviation'])==h
    model=p['raw_margin_home'];bk=book[(a,h)];act=int(H['score'])-int(A['score']);me,be=abs(model-act),abs(bk-act)
    w='model' if me<be-1e-8 else 'book' if be<me-1e-8 else 'tie'
    rows.append(dict(week=6,event=f"{a} at {h}",event_id=e['id'],game_id=p['game_id'],model_margin_home=model,book_margin_home=bk,final=f"{A['team']['abbreviation']} {A['score']}, {H['team']['abbreviation']} {H['score']}",actual_margin_home=act,model_abs_error=round(me,10),book_abs_error=round(be,10),winner=w,eligible=True,book_captured_at_ct='Tue Oct 13 7:12 AM',book_state='IL',book_source_file='tools/nfl/week6_2026/fanduel_il_nfl_capture_20261013T1212Z.json',book_source_url=None,book_line_note='Oct 13 capture only; not a last pre-kickoff line',final_source_url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week=6',lineage='margin-Elo v1, point-in-time (completed game scores only); measurement, not a validated edge'))
assert len(rows)==14
(R/'tools/nfl/week6_2026/grade/week6_grade.json').write_text(json.dumps({'label':'Margin-Elo v1 Week 6 grade (point-in-time scores-only model)','method':'Lower absolute final home-margin error versus the Oct 13 FanDuel IL home spread (captured before Thursday kickoff but not a last pre-kickoff line). book home margin = -home spread.','rows':rows},indent=2)+'\n')
tr=json.load(open(R/'model_tracking.json'));assert not any(r['week']==6 for r in tr['nfl']['grades']);tr['nfl']['grades'].extend(rows)
for r in rows:tr['nfl']['record'][r['winner'] if r['winner']!='tie' else 'ties']+=1
tr['nfl']['record']['graded']+=14;tr['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
(R/'model_tracking.json').write_text(json.dumps(tr,indent=2)+'\n')
c={k:sum(r['winner']==k for r in rows) for k in('model','book','tie')};print(c,'MAE model',round(sum(r['model_abs_error'] for r in rows)/14,3),'book',round(sum(r['book_abs_error'] for r in rows)/14,3),tr['nfl']['record'])
for r in rows:print(r['event'],r['final'],'model',r['model_margin_home'],'book',r['book_margin_home'],r['winner'])
