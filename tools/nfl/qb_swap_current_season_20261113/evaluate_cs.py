import pandas as pd,numpy as np
R=pd.read_csv('out/qbswap_cs_rows.csv'); R=R[R.core.notna()&R.d_open.notna()&R.d_last.notna()].sort_values('date').reset_index(drop=True)
print('rows',len(R),R.groupby('season').size().to_dict())
def coef(d,c): return (d[c]*d.resid).sum()/(d[c]**2).sum()
for c in ['d_open','d_last']:
    b=coef(R,c); bs=[coef(R.sample(len(R),replace=True,random_state=i),c) for i in range(2000)]
    print(c,'retrospective all-row assoc %.1f CI [%.1f,%.1f]'%(b,*np.percentile(bs,[2.5,97.5])),'| |delta|>0.02 games',(R[c].abs()>0.02).sum())
    # prospective: expanding fit on rows with date strictly earlier; evaluate 2023+ (>=2 prior seasons)
    e0=[];e1=[];bb=[]
    for dt in sorted(R.date.unique()):
        te=R[R.date==dt]
        tr=R[R.date<dt]
        if tr.season.nunique()<2 or te.season.iloc[0]<2023: continue
        beta=coef(tr,c); bb.append(beta)
        e0+=list(te.resid); e1+=list(te.resid-beta*te[c])
    e0=np.array(e0);e1=np.array(e1);n=len(e0)
    g=[(e0[i]**2).mean()-(e1[i]**2).mean() for i in [np.random.default_rng(j).integers(0,n,n) for j in range(2000)]]
    print(' prospective expanding-window 2023-26 n=%d MSE %.2f->%.2f MAE %.3f->%.3f gainCI'%(n,(e0**2).mean(),(e1**2).mean(),abs(e0).mean(),abs(e1).mean()),np.percentile(g,[2.5,50,97.5]).round(2),'coef range %.1f-%.1f'%(min(bb),max(bb)))
