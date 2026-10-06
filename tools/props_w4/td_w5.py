import json,re,glob,csv,numpy as np,pandas as pd
exec(open('/tmp/pm/model.py').read().split("H=[3,6,12]")[0])
va=json.load(open('/tmp/pm/validation_atd.json'));h=va['best']['h'];kk=va['best']['k']
def nm(s):
    s=s if isinstance(s,str) else ''
    return re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?','',s.lower().replace('.','').replace("'",'')).strip()
g=pd.read_csv('/tmp/games_new.csv',low_memory=False);g=g[(g.season==2026)&(g.week==5)]
opp={};ko={}
for _,r in g.iterrows():opp[r.home_team]=r.away_team;opp[r.away_team]=r.home_team;ko[r.home_team]=ko[r.away_team]=f"{r.gameday} {r.gametime} ET"
book={}
for f in sorted(glob.glob('/tmp/tdw5/td_*.json')):
    j=json.loads(json.load(open(f))['content']);L=[l.strip() for l in j['text'].split('\n')];eid=f.split('_')[-1][:-5]
    if 'ANY TIME' not in L:print('no ATD market',eid);continue
    a=L.index('ANY TIME');e=L.index('Show less',a) if 'Show less' in L[a:] else None
    seg=L[a+3:e] if e else L[a+3:]
    seg=L[a+2:e] if e else L[a+2:]
    for q in range(0,len(seg)-2,3):
        n,x,f2=seg[q:q+3]
        if re.fullmatch(r'[+-]\d+',x) and re.fullmatch(r'[+-]\d+',f2):book[nm(n)]=dict(price=x,cap=j['captured_at'],event=eid,first=f2)
print('book players',len(book))
OUT={'DOWDLE'}
rows=[]
d['key']=d.player_display_name.map(nm);d['touch']=d.carries.fillna(0)+d.targets.fillna(0)
teams=set(opp)
for k,gg in d.groupby('key'):
    gg=gg.sort_values(['season','week']);cur=gg.team.values[-1];pos=gg.position.values[-1]
    if cur not in teams or pos not in('QB','RB','WR','TE'):continue
    if (gg.season.values[-1]!=2026 or gg.week.values[-1]<2) and k not in book:continue
    v=gg.tds.values.astype(float)[-17:];n=len(v);tc=gg.touch.values[-6:].mean()
    if tc<3 and k not in book:continue
    if k in('rico dowdle',):continue
    w=0.5**(np.arange(n)[::-1]/h);lam=va['lam'].get(pos,0.28);l=((w*v).sum()+kk*lam)/(w.sum()+kk);p=1-np.exp(-l)
    b=book.get(k);o=None
    if b:
        o=int(b['price']);imp=100/(o+100) if o>0 else -o/(-o+100)
    rows.append(dict(player=gg.player_display_name.values[-1],pos=pos,team=cur,opp=opp[cur],games=n,model=round(float(p),3),book=b['price'] if b else None,book_prob=round(imp,3) if b else None,gap=round((p-imp)*100,1) if b else None,cap=b['cap'] if b else None,kick=ko[cur]))
json.dump(rows,open('/tmp/pm/td_w5_all.json','w'),indent=1)
print(len(rows),sum(1 for r in rows if r['book']))
miss=[k for k in book if not any(nm(r['player'])==k for r in rows)];print('book not modeled:',miss[:60])
