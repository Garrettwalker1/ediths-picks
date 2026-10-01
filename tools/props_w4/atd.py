import pandas as pd,numpy as np,json
exec(open('/tmp/pm/model.py').read().split("H=[3,6,12]")[0])
d['touch']=d.get('carries',0).fillna(0)+d.get('targets',0).fillna(0)
hist={pid:g for pid,g in d.groupby('player_id')}
H=[3,6,12];K=[0,1,2,4]
def F(seasons):
    R=[]
    for pid,g in hist.items():
        v=g.tds.values.astype(float);a=g.atd.values;s=g.season.values;tc=g.touch.values;pos=g.position.values
        for i in np.where(np.isin(s,seasons))[0]:
            if i<3:continue
            lo=max(0,i-17);xs=v[lo:i]
            if tc[max(0,i-6):i].mean()<3 or pos[i] in('K','P'):continue
            ages=np.arange(len(xs))[::-1];row=dict(pos=pos[i],y=a[i],b6=(v[max(0,i-6):i]>0).mean(),sm=((v[:i][s[:i]==s[i]])>0).mean() if (s[:i]==s[i]).any() else (v[max(0,i-6):i]>0).mean())
            for h in H:
                w=0.5**(ages/h);row[f'W{h}']=w.sum();row[f'E{h}']=(w*xs).sum()/w.sum()
            R.append(row)
    return pd.DataFrame(R)
tr,va,te=F([2023]),F([2024]),F([2025])
pm=tr.groupby("pos").y.mean().to_dict()
lam={k:-np.log(1-v) for k,v in pm.items()};gl=-np.log(1-tr.y.mean())
def p(df,h,k):
    l=(df[f'E{h}']*df[f'W{h}']+k*df.pos.map(lam).fillna(gl))/(df[f'W{h}']+k);return 1-np.exp(-l)
br=lambda pr,y:((pr-y)**2).mean()
base=lambda df,c:df[c].clip(0.03,0.9)
grid={(h,k):br(p(va,h,k),va.y) for h in H for k in K};bh,bk=min(grid,key=grid.get)
out=dict(n_val=len(va),n_test=len(te),best=dict(h=bh,k=bk),val_brier=grid[(bh,bk)],val_b6=br(base(va,'b6'),va.y),val_sm=br(base(va,'sm'),va.y),val_const=br(tr.y.mean(),va.y),
 test_brier=br(p(te,bh,bk),te.y),test_b6=br(base(te,'b6'),te.y),test_sm=br(base(te,'sm'),te.y),test_const=br(tr.y.mean(),te.y),test_rate=te.y.mean(),test_mean_pred=p(te,bh,bk).mean(),lam=lam)
print({k:(round(v,4) if isinstance(v,float) else v) for k,v in out.items()});json.dump(out,open('/tmp/pm/validation_atd.json','w'),default=float,indent=1)
