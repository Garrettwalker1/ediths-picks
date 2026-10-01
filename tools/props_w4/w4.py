import pandas as pd,numpy as np,json,re
exec(open('/tmp/pm/model.py').read().split("H=[3,6,12]")[0])
val=json.load(open('/tmp/pm/validation_props.json'));va=json.load(open('/tmp/pm/validation_atd.json'))
def nm(s):
    s=s if isinstance(s,str) else ''
    return re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?','',s.lower().replace('.','').replace("'",'')).strip()
d['key']=d.player_display_name.map(nm)
rows=json.load(open('/tmp/props_w4_pitcle.json'))
D2={k:g.sort_values(['season','week']) for k,g in d.groupby('key')}
STAT={'Passing Yds':'passing_yards','Passing TDs':'passing_tds','Rushing Yds':'rushing_yards','Receiving Yds':'receiving_yards','Total Receptions':'receptions','Rushing + Receiving Yds':'rr_yds'}
out=[]
for r in rows:
    k=nm(r['player']);g=D2.get(k)
    if r['market']=='Anytime TD':
        if g is None:out.append(dict(r,model=None,note='No NFL history in feed'));continue
        g=g[g.team.isin(['PIT','CLE'])|True]
        v=g.tds.values.astype(float)[-17:];n=len(v);cur=g.team.values[-1]
        if cur not in('PIT','CLE'):out.append(dict(r,model=None,note='Not on PIT/CLE in latest game'));continue
        h=va['best']['h'];kk=va['best']['k'];w=0.5**(np.arange(n)[::-1]/h)
        lam=va['lam'].get(g.position.values[-1],0.28);l=((w*v).sum()+kk*lam)/(w.sum()+kk)
        p=1-np.exp(-l);o=int(r['over_odds']);imp=100/(o+100) if o>0 else -o/(-o+100)
        out.append(dict(r,pos=g.position.values[-1],team=cur,games=n,model_prob=round(p,3),book_implied=round(imp,3),gap_pts=round((p-imp)*100,1)));continue
    stat=STAT[r['market']]
    if g is None:out.append(dict(r,model=None,note='No NFL history in feed'));continue
    cur=g.team.values[-1]
    if cur not in('PIT','CLE'):out.append(dict(r,model=None,note='Not on PIT/CLE'));continue
    v=g[stat].values.astype(float)[-17:];n=len(v);vv=val[stat]['val_best'];h,kk=vv['h'],vv['k']
    w=0.5**(np.arange(n)[::-1]/h);pmn=val[stat]['pm'].get(g.position.values[-1],np.mean(list(val[stat]['pm'].values())))
    mu=((w*v).sum()+kk*pmn)/(w.sum()+kk)
    out.append(dict(r,pos=g.position.values[-1],team=cur,games=n,model=round(float(mu),1),gap=round(float(mu)-float(r['line']),1)))
json.dump(out,open('/tmp/pm/w4_props_out.json','w'),indent=1)
for o in out:print(o['player'],o['market'],o.get('line'),o.get('over_odds'),o.get('model',o.get('model_prob')),o.get('gap',o.get('gap_pts')),o.get('games'),o.get('note',''))
