"""Rebuild the PIT at CLE props block (model vs FanDuel IL) in index.html from fresh captures.
usage: python3 build_w4.py CAPDIR INDEX_HTML CAPTURE_LABEL   (e.g. /tmp/w4cap /tmp/pub/index.html 'Oct 1 5:40 PM CT')
Capture first with cap_w4.sh. Model data: /tmp/pm/s20YY.csv + model.py + validation_*.json (this dir)."""
import sys,json,re,html,datetime,numpy as np,pandas as pd
CAP,IDX,LABEL=sys.argv[1:4]
HERE='/tmp/pub/tools/props_w4'
exec(open(HERE+'/model.py').read().split("H=[3,6,12]")[0])
val=json.load(open(HERE+'/validation_props.json'));va=json.load(open(HERE+'/validation_atd.json'))
def nm(s):return re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?','',(s if isinstance(s,str) else '').lower().replace('.','').replace("'",'')).strip()
d['key']=d.player_display_name.map(nm);D2={k:g.sort_values(['season','week']) for k,g in d.groupby('key')}
MK=r'(Passing Yds|Passing TDs|Rushing Yds|Receiving Yds|Total Receptions|Rushing \+ Receiving Yds)'
rows=[];cap_ts=[]
for tab in ['passing-props','receiving-props','rushing-props','td-scorer-props']:
    x=json.load(open(f'{CAP}/{tab}.json'));t=x['sections'][0];cap_ts.append(x['captured_at']);assert 'Illinois' in t,tab  # same IL session; passing/receiving/td tabs also carry 'physically present in Illinois'
    t=t.split('\n')
    for i,l in enumerate(t):
        m=re.match(r'^(.+) - '+MK+'$',l)
        if m and i+6<len(t) and t[i+2].startswith('O '):
            u=t[i+6] if t[i+5].startswith('U ') else t[i+7]
            rows.append(dict(player=m.group(1),market=m.group(2),line=t[i+2][2:],over=t[i+3],under=u))
seen={};[seen.setdefault((r['player'],r['market']),r) for r in rows];rows=list(seen.values())
td=json.load(open(f'{CAP}/td-all.json'));cap_ts.append(td['captured_at']);tt=td['text'].split('\n')
i=tt.index('ANY TIME');atd=[];j=i+3
while j+3<len(tt) and re.fullmatch(r'[+-]\d+',tt[j+1]) and re.fullmatch(r'[+-]\d+',tt[j+2]) and re.fullmatch(r'[+-]\d+',tt[j+3]):
    atd.append((tt[j],int(tt[j+1])));j+=4
STAT={'Passing Yds':'passing_yards','Passing TDs':'passing_tds','Rushing Yds':'rushing_yards','Receiving Yds':'receiving_yards','Total Receptions':'receptions','Rushing + Receiving Yds':'rr_yds'}
LAB={'Passing Yds':'Pass yds','Passing TDs':'Pass TDs','Rushing Yds':'Rush yds','Receiving Yds':'Rec yds','Total Receptions':'Receptions','Rushing + Receiving Yds':'Rush+rec yds'}
ORDER=list(LAB);cards={}
for r in rows:
    g=D2.get(nm(r['player']))
    if g is None or g.team.values[-1] not in('PIT','CLE'):continue
    v=g[STAT[r['market']]].values.astype(float)[-17:];n=len(v);vv=val[STAT[r['market']]]['val_best'];h,kk=vv['h'],vv['k']
    pos=g.position.values[-1];pm_=val[STAT[r['market']]]['pm'];pmn=pm_.get(pos,np.mean(list(pm_.values())))
    w=0.5**(np.arange(n)[::-1]/h);mu=((w*v).sum()+kk*pmn)/(w.sum()+kk)
    c=cards.setdefault(r['player'],dict(team=g.team.values[-1],pos=pos,games=len(g),m={}));c['m'][r['market']]=(r['line'],r['over'],round(float(mu),1))
def sg(x):return ('+' if x>0 else '')+f'{x:.1f}'
def card(name,c):
    thin=f' <small class="muted">thin history ({c["games"]} games)</small>' if c['games']<8 else ''
    h=f"<div class='card'><h3>{html.escape(name)} <span class='tag'>{c['team']} {c['pos']}</span>{thin}</h3><div class=\"pgrid\"><div class=\"ph\"><span></span><span>Book line (over)</span><span>Model</span><span>Model - line</span></div>"
    for mk in ORDER:
        if mk in c['m']:
            ln,od,mu=c['m'][mk];gp=round(mu-float(ln),1)
            h+=f"<div class=\"pr\"><span>{LAB[mk]}</span><span>{ln} <small>({od})</small></span><span><b>{mu:.1f}</b></span><span class='{'up' if gp>0 else 'dn'}'>{sg(gp)}</span></div>"
    return h+'</div></div>'
old=open(IDX).read();a=old.index('<div id="propsW4">');b=old.index('<h3>Player lines</h3>',a)
head=old[a:b]
head=re.sub(r'captured Oct 1 [0-9:]+ [AP]M CT',f'captured {LABEL}',head)
head=re.sub(r' <b>Re-read 5:36 PM CT.*?model numbers are unchanged\.','',head,flags=re.S)
oldorder=re.findall(r'<h3>([^<]*?) <span class=.tag.>',old[b:])
names=sorted(cards,key=lambda n:(oldorder.index(n) if n in oldorder else 99,n))
cardsh=''.join(card(n,cards[n]) for n in names)
aj=old.index('<h2>Anytime touchdown: model vs book</h2>',b);ak=old.index('<div class="card"><div class="pgrid atd">',aj)
anote=old[aj:ak]
at=[]
for nme,o in atd:
    g=D2.get(nm(nme))
    if g is None or g.team.values[-1] not in('PIT','CLE'):continue
    v=g.tds.values.astype(float)[-17:];n=len(v);hh=va['best']['h'];kk=va['best']['k'];w=0.5**(np.arange(n)[::-1]/hh)
    lam=va['lam'].get(g.position.values[-1],0.28);l=((w*v).sum()+kk*lam)/(w.sum()+kk);p=1-np.exp(-l)
    imp=100/(o+100) if o>0 else -o/(-o+100);at.append((nme,g.team.values[-1],len(g),o,imp,p))
at.sort(key=lambda z:-z[4])
ah='<div class="card"><div class="pgrid atd"><div class="ph"><span>Player</span><span>Book</span><span>Book %</span><span>Model %</span><span>Gap</span></div>'
for nme,tm,gm,o,imp,p in at:
    gp=round((p-imp)*100,1);ah+=f"<div class=\"pr\"><span>{html.escape(nme)} <small class='muted'>{tm}{' · thin' if gm<8 else ''}</small></span><span>{'+' if o>0 else ''}{o}</span><span>{imp*100:.0f}%</span><span><b>{p*100:.0f}%</b></span><span class='{'up' if gp>0 else 'dn'}'>{sg(gp)}</span></div>"
ah+='</div></div><p class="muted">Defense TD lines are not modeled. Only lines FanDuel posted for this game are shown; the rest of Sunday\'s slate is next.</p></div>'
new=old[:a]+head+'<h3>Player lines</h3><div class="grid">'+cardsh+'</div>'+anote+ah+old[old.index('</div>',old.index('Defense TD lines are not modeled',aj)+30) +6:] if False else None
# find end of the propsW4 block: first "</p></div>" after 'Defense TD lines'
e=old.index('</p></div>',old.index('Defense TD lines are not modeled',aj))+len('</p></div>')
new=old[:a]+head+'<h3>Player lines</h3><div class="grid">'+cardsh+'</div>'+anote+ah+old[e:]
open(IDX,'w').write(new)
print('cards',len(names),'atd rows',len(at),'cap',min(cap_ts),max(cap_ts))
