#!/usr/bin/env python3
"""Grade frozen margin-Elo v1 Week 5 raw home margins (game_predictions_raw.json, unrounded) against the FanDuel Illinois spread published on the board.
The ONLY Week 5 book capture that survives is the Oct 6 6:55 AM CT Illinois capture (tools/nfl/week5_2026/fanduel_il_nfl_capture_20261006T1155Z.json). It is NOT a last pre-kickoff line: Thursday was 2 days earlier, Monday night 6 days earlier. Book lines never feed the model.
Usage: build_grade.py espn_scoreboard.json  (run from repo root)"""
import json,sys,datetime as dt,pathlib
R=pathlib.Path(__file__).resolve().parents[4]
AL={'LA':'LAR','WAS':'WSH'};C=lambda t:AL.get(t,t)
N={'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF','Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE','Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Miami Dolphins':'MIA','Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','San Francisco 49ers':'SF','Seattle Seahawks':'SEA','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WSH'}
cap=json.load(open(R/'tools/nfl/week5_2026/fanduel_il_nfl_capture_20261006T1155Z.json'));assert 'Illinois' in cap['footer']
book={}
for it in cap['items']:
    f=[s.strip() for s in it['text'].split('\n')];a,h=N[f[0]],N[f[1]];book[(a,h)]=-float(f[7])  # home spread -> expected home margin
pred={(C(x['away']),C(x['home'])):x for x in json.load(open(R/'tools/nfl/week5_2026/game_predictions_raw.json'))}
ev=json.load(open(sys.argv[1]))['events'];rows=[]
for (a,h),p in sorted(pred.items(),key=lambda kv:kv[1]['game_id']):
    e=[e for e in ev if {C(c['team']['abbreviation']) for c in e['competitions'][0]['competitors']}=={a,h}];assert len(e)==1;e=e[0];assert e['status']['type']['name']=='STATUS_FINAL'
    comp=e['competitions'][0]['competitors'];H=next(c for c in comp if c['homeAway']=='home');A=next(c for c in comp if c['homeAway']=='away');assert C(H['team']['abbreviation'])==h
    model=p['raw_margin_home'];bk=book[(a,h)];act=int(H['score'])-int(A['score']);me,be=abs(model-act),abs(bk-act)
    w='model' if me<be-1e-8 else 'book' if be<me-1e-8 else 'tie'
    rows.append(dict(week=5,event=f"{a} at {h}",event_id=e['id'],game_id=p['game_id'],model_margin_home=model,book_margin_home=bk,final=f"{A['team']['abbreviation']} {A['score']}, {H['team']['abbreviation']} {H['score']}",actual_margin_home=act,model_abs_error=round(me,10),book_abs_error=round(be,10),winner=w,eligible=True,book_captured_at_ct='Tue Oct 6 6:55 AM',book_state='IL',book_source_file='tools/nfl/week5_2026/fanduel_il_nfl_capture_20261006T1155Z.json',book_source_url=None,book_line_note='Oct 6 capture only; not a last pre-kickoff line',final_source_url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2026&seasontype=2&week=5',lineage='margin-Elo v1, point-in-time (completed game scores only); measurement, not a validated edge'))
assert len(rows)==15
(R/'tools/nfl/week5_2026/grade/week5_grade.json').write_text(json.dumps({'label':'Margin-Elo v1 Week 5 grade (point-in-time scores-only model)','method':'Lower absolute final home-margin error versus the Oct 6 FanDuel IL home spread (the only surviving Week 5 capture, not a last pre-kickoff line). book home margin = -home spread.','rows':rows},indent=2)+'\n')
tr=json.load(open(R/'model_tracking.json'));assert not any(r['week']==5 for r in tr['nfl']['grades']);tr['nfl']['grades'].extend(rows)
for r in rows:tr['nfl']['record'][r['winner'] if r['winner']!='tie' else 'ties']+=1
tr['nfl']['record']['graded']+=15;tr['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
(R/'model_tracking.json').write_text(json.dumps(tr,indent=2)+'\n')
c={k:sum(r['winner']==k for r in rows) for k in('model','book','tie')};print(c,'MAE model',round(sum(r['model_abs_error'] for r in rows)/15,3),'book',round(sum(r['book_abs_error'] for r in rows)/15,3),tr['nfl']['record'])
for r in rows:print(r['event'],r['final'],'model',r['model_margin_home'],'book',r['book_margin_home'],r['winner'])
