import pandas as pd,numpy as np,json,itertools
Y=[2023,2024,2025,2026]
d=pd.concat([pd.read_csv(f'/tmp/pm/s{y}.csv',low_memory=False) for y in Y]);d=d[d.season_type=='REG'].copy()
for c in ['rushing_tds','receiving_tds','rushing_yards','receiving_yards','passing_yards','passing_tds','receptions']:d[c]=d[c].fillna(0)
d['rr_yds']=d.rushing_yards+d.receiving_yards
d['tds']=d.rushing_tds+d.receiving_tds;d['atd']=(d.tds>0).astype(int)
d=d.sort_values(['player_id','season','week']).reset_index(drop=True)
THR={'passing_yards':100,'passing_tds':0.5,'rushing_yards':8,'receiving_yards':15,'receptions':1.5,'rr_yds':20}
hist={pid:g for pid,g in d.groupby('player_id')}
def feats(stat,seasons,H):
    """per eligible player-game: dict of ew arrays per half-life"""
    R=[]
    for pid,g in hist.items():
        v=g[stat].values.astype(float);s=g.season.values;pos=g.position.values;wk=g.week.values
        for i in np.where(np.isin(s,seasons))[0]:
            if i<3:continue
            lo=max(0,i-17);xs=v[lo:i];b6=v[max(0,i-6):i].mean()
            if b6<THR[stat]:continue
            ages=np.arange(len(xs))[::-1];ss=v[:i][s[:i]==s[i]];sm=ss.mean() if len(ss)>=1 else b6
            row=dict(pid=pid,season=int(s[i]),week=int(wk[i]),pos=pos[i],y=v[i],b6=b6,sm=sm)
            for h in H:
                w=0.5**(ages/h);row[f'W{h}']=w.sum();row[f'E{h}']=(w*xs).sum()/w.sum()
            R.append(row)
    return pd.DataFrame(R)
H=[3,6,12];K=[0,1,2,4]
res={}
for stat in THR:
    tr=feats(stat,[2023],H);va=feats(stat,[2024],H);te=feats(stat,[2025],H)
    pm=tr.groupby('pos').y.mean().to_dict();gm=tr.y.mean()
    def mae(df,h,k):
        p=(df[f'E{h}']*df[f'W{h}']+k*df.pos.map(pm).fillna(gm))/(df[f'W{h}']+k);return (df.y-p).abs().mean()
    grid={(h,k):mae(va,h,k) for h in H for k in K}
    (bh,bk)=min(grid,key=grid.get)
    res[stat]=dict(n_val=len(va),n_test=len(te),val_best=dict(h=bh,k=bk,mae=grid[(bh,bk)]),val_b6=(va.y-va.b6).abs().mean(),val_sm=(va.y-va.sm).abs().mean(),
      test_model=mae(te,bh,bk),test_b6=(te.y-te.b6).abs().mean(),test_sm=(te.y-te.sm).abs().mean(),pm=pm)
    print(stat,{k:(round(v,3) if isinstance(v,float) else v) for k,v in res[stat].items() if k!='pm'},flush=True)
json.dump({k:{a:b for a,b in v.items()} for k,v in res.items()},open('/tmp/pm/validation_props.json','w'),default=float,indent=1)
