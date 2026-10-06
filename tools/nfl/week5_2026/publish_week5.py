#!/usr/bin/env python3
"""Patch index.html with the Week 5 NFL board (frozen raw predictions + FanDuel IL capture, comparison only) and add Week 5 score projections to model_tracking.json."""
import json,re,sys,datetime as dt,pathlib
R=pathlib.Path(__file__).resolve().parents[3]
cap=json.load(open(R/'tools/nfl/week5_2026/fanduel_il_nfl_capture_20261006T1155Z.json'))
assert 'physically present in Illinois' in cap['footer'] or 'Illinois' in cap['footer']
pred=json.load(open(R/'tools/nfl/week5_2026/game_predictions_raw.json'))
N={'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF','Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE','Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LA','Miami Dolphins':'MIA','Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','San Francisco 49ers':'SF','Seattle Seahawks':'SEA','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WSH'}
bk={}
for it in cap['items']:
    f=[s.strip() for s in it['text'].split('\n')]
    a,h=N[f[0]],N[f[1]]
    # away spread, odds, away ML, O total, odds, home spread, odds, home ML, U total, odds, time
    asp,aml,tot,hsp,hml=float(f[2]),f[4],float(f[5][2:]),float(f[7]),f[9]
    assert asp==-hsp and f[5][0]=='O'
    bk[(a,h)]=dict(asp=asp,hsp=hsp,aml=aml,hml=hml,tot=tot,when=f[-3] if 'More' in f[-1] else f[-2])
cdt=dt.datetime.fromisoformat(cap['captured_at'].replace('Z','+00:00')).astimezone(dt.timezone(dt.timedelta(hours=-5)))
stamp=cdt.strftime('%a %b %-d at %-I:%M %p CT')
fix={'LAR':'LA'}
rows=[];proj=[]
for p in pred:
    a,h=fix.get(p['away'],p['away']),fix.get(p['home'],p['home']);a='WSH' if a=='WAS' else a;h='WSH' if h=='WAS' else h
    b=bk[(a,h)];m=p['raw_margin_home']
    if abs(m)<0.25:model='PK'
    else:
        fav,sp=(h,m) if m>0 else (a,-m);model=f"{fav} -{sp:.2f}"
    if b['hsp']<0:fav,s,fml,dml,dn=h,b['hsp'],b['hml'],b['aml'],a
    elif b['asp']<0:fav,s,fml,dml,dn=a,b['asp'],b['aml'],b['hml'],h
    else:fav,s,fml,dml,dn=h,0,b['hml'],b['aml'],a
    mk=(f"PK" if s==0 else f"{fav} {s:g}")+f" · O/U {b['tot']:g} · ML {fav} {fml} / {dn} {dml}"
    ko=dt.datetime.strptime(p['date']+' '+p['time_et'],'%Y-%m-%d %H:%M')+dt.timedelta(hours=4)
    rows.append(dict(sport='NFL',matchup=f"{a} at {h}",book=f"FanDuel IL · captured {stamp} · interim non-TN",market=mk,model=model,edge=None,pick=None,home_win=round(p['home_win_prob']*100,1),approved=False,line_only=True,kickoff=ko.strftime('%Y-%m-%dT%H:%MZ'),model_note=f"Margin-Elo v1 (game scores only, no injury/QB/weather adjustment). Raw home margin {m}."))
    proj.append(dict(event=f"{a} at {h}",kickoff=ko.strftime('%Y-%m-%dT%H:%M:00Z'),model_margin_home=m,model_total=p['model_total'],away_score=p['away_score'],home_score=p['home_score'],note='margin-Elo v1 split around trained totals ridge; beats the average-total baseline, trails the closing total',method='margin-Elo v1 split around totals ridge (Oct 6); scores-only inputs, no injury/QB/weather'))
h=open(R/'index.html').read()
i=h.find('const D=');D,end=json.JSONDecoder().raw_decode(h[i+8:])
assert all(x['sport']=='NFL' for x in D['current'])
D['current']=rows;D['weather']=[]
h=h[:i+8]+json.dumps(D,ensure_ascii=False)+h[i+8+end:]
def sub(old,new,cnt=1):
    global h;assert h.count(old)>=1,old[:60];h=h.replace(old,new,cnt)
sub('<h2>Week 4 NFL book lines</h2>','<h2>Week 5 NFL book lines</h2>')
a0=h.find('Book column is FanDuel Illinois captured Oct 4 at 5:40 PM CT');a1=h.find('</p>',a0)
h=h[:a0]+f"Book column is FanDuel Illinois captured {stamp}, not Tennessee prices and never a model input. Week 4 final grade is in the forward record above. Injuries are not in the model; current availability news is listed under Breaking availability (display only). Thursday TB at DAL is Oct 8; the rest of the slate is Sunday and Monday Oct 11 and 12."+h[a1:]
sub('<b>Week 4 model: unavailable</b><small>Quarantined; frozen Week 3 historical grade below</small>','<b>Week 5 model: margin-Elo v1</b><small>Completed game scores only · no injury, QB or weather input · trails the closing line</small>')
sub('<small>Oct 4, 5:40 PM CT · spread · total · moneyline · not Tennessee</small>',f'<small>{stamp} · spread · total · moneyline · not Tennessee</small>')
sub('Week 3 and earlier eligible finals.','Week 4 and earlier eligible finals.')
sub("<div class='card note'><b>Final-score projections.</b>","<div class='card note'><b>Week 4: ${n.grades.filter(g=>g.week===4&&g.winner==='model').length}-${n.grades.filter(g=>g.week===4&&g.winner==='book').length}-${n.grades.filter(g=>g.week===4&&g.winner==='tie').length} margin-Elo v1 vs book.</b><p>16 final games, model mean error ${(n.grades.filter(g=>g.week===4).reduce((s,g)=>s+g.model_abs_error,0)/16).toFixed(2)} pts vs book ${(n.grades.filter(g=>g.week===4).reduce((s,g)=>s+g.book_abs_error,0)/16).toFixed(2)}. The model uses only completed prior game scores; its locked 2024-25 test still trails the book, and book lines here are the last pre-kickoff FanDuel IL spreads published on this board (raw capture files for Oct 2-5 were lost in a workspace reset). Measurement only. <a href='tools/nfl/week4_2026/grade/week4_grade.json'>See graded rows</a>.</p></div><div class='card note'><b>Final-score projections.</b>")
sub('The Week 4 numbers come from a new','The Week 5 numbers come from a new')
sub('Week 4 scores come from the margin-Elo model','Week 5 scores come from the margin-Elo model')
sub('No Week 4 projection','No Week 5 projection')
w0=h.find('Week 4 stadium forecasts at kickoff');w1=h.find('</p>',w0)
h=h[:w0]+'Week 5 stadium forecasts are not pulled yet (most kickoffs are outside the free forecast range), so this section is blank rather than showing last week\'s numbers. Weather does not feed the model numbers.'+h[w1:]
open(R/'index.html','w').write(h)
t=json.load(open(R/'model_tracking.json'));t['nfl']['score_projections']=[x for x in t['nfl']['score_projections'] if not x['event'] in {p['event'] for p in proj}]+proj
t['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
open(R/'model_tracking.json','w').write(json.dumps(t,indent=2)+'\n')
print(stamp,len(rows));[print(r['matchup'],'|',r['model'],'|',r['market'],'|',r['kickoff']) for r in rows]
