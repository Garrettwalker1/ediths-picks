#!/usr/bin/env python3
"""Week 7 anytime-TD board - IDENTITY FIX (Oct 23): identical to build_td_w7_thu.py except rows are keyed by player_id instead of normalized display name. The pre-fix build merged same-name players (MIN WR Justin Jefferson with CLE LB Justin Jefferson, whose trailing LB row dropped the WR from the board). Model spec unchanged: recency-weighted TD rate through Week 6 2026, shrunk to locked per-position average (h=12, k=4, tools/props_w4/validation_atd.json). Pre-fix artifact preserved as week7_anytime_td_prefix_namecollision_20261023.json (and in git history). Verified: regeneration changes only the addition of the Jefferson MIN row; all other rows byte-identical."""
import json,re,numpy as np,pandas as pd,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[3]
va=json.load(open(R/'tools/props_w4/validation_atd.json'));h=va['best']['h'];kk=va['best']['k'];LAM=va['lam']
def nm(s):
    s=s if isinstance(s,str) else ''
    return re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?','',s.lower().replace('.','').replace("'",'')).strip()
pred=json.load(open(R/'tools/nfl/week7_2026/game_predictions_raw.json'))
fix={'LAR':'LA','WAS':'WSH'}
opp={};ko={}
for p in pred:
    a=fix.get(p['away'],p['away']);hm=fix.get(p['home'],p['home'])
    opp[a]=hm;opp[hm]=a;ko[a]=ko[hm]=f"{p['date']} {p['time_et']} ET"
frames=[]
for y in (2023,2024,2025,2026):
    x=pd.read_csv(R/f'tools/player_projection_cache/stats_{y}.csv',usecols=['player_id','player_display_name','position','team','season','week','season_type','carries','targets','rushing_tds','receiving_tds'],low_memory=False)
    frames.append(x[x.season_type=='REG'])
d=pd.concat(frames,ignore_index=True);d['tds']=d.rushing_tds.fillna(0)+d.receiving_tds.fillna(0);d['touch']=d.carries.fillna(0)+d.targets.fillna(0)
cap=json.load(open(R/'tools/nfl/week7_2026/fanduel_il_atd_ne_chi_20261022.json'))
L=[l.strip() for l in cap['text'].split('\n')]
book={}
for q in range(2,len(L)-2,3):
    n,x,f2=L[q:q+3]
    if re.fullmatch(r'[+-]\d+',x) and re.fullmatch(r'[+-]\d+',f2) and 'Defense' not in n:book[nm(n)]=dict(price=x,cap=cap['captured_at'])
teams=set(opp);rows=[]
for pid,gg in d.groupby('player_id'):
    gg=gg.sort_values(['season','week']);cur=gg.team.values[-1];pos=gg.position.values[-1]
    if cur not in teams or pos not in ('QB','RB','WR','TE'):continue
    k=nm(gg.player_display_name.values[-1])
    if (gg.season.values[-1]!=2026 or gg.week.values[-1]<2) and k not in book:continue
    tc=gg.touch.values[-6:].mean()
    if tc<3 and k not in book:continue
    v=gg.tds.values.astype(float)[-17:];n=len(v)
    w=0.5**(np.arange(n)[::-1]/h);lam=LAM.get(pos,0.28);l=((w*v).sum()+kk*lam)/(w.sum()+kk);p=1-np.exp(-l)
    b=book.get(k);o=None
    if b:
        o=int(b['price']);imp=100/(o+100) if o>0 else -o/(-o+100)
    rows.append(dict(player=gg.player_display_name.values[-1],pos=pos,team=cur,opp=opp[cur],games=n,model=round(float(p),3),book=b['price'] if b else None,book_prob=round(imp,3) if b else None,gap=round((p-imp)*100,1) if b else None,cap=b['cap'] if b else None,kick=ko[cur]))
out=dict(week=7,season=2026,captured_from=cap['captured_at'],captured_to=cap['captured_at'],state='IL',note='FanDuel Illinois anytime TD prices, Thursday NE at CHI prices refreshed Oct 22 ~5:29 PM CT pre-game; other games blank = not posted yet. Model = recency-weighted TD rate through Week 6 2026, shrunk to locked per-position average (h=12, k=4, tools/props_w4/validation_atd.json). IR/Out zeroing applies on display via injury_adjustments.json. IDENTITY FIX Oct 23: rows are now keyed by player_id instead of normalized name - the pre-fix build merged same-name players (dropped MIN WR Justin Jefferson via CLE LB Justin Jefferson); pre-fix artifact preserved as week7_anytime_td_prefix_namecollision_20261023.json. Model spec unchanged.',rows=sorted(rows,key=lambda r:(r['kick'],-r['model'])))
json.dump(out,open(R/'week7_anytime_td.json','w'),indent=1)
print('rows:',len(rows))
