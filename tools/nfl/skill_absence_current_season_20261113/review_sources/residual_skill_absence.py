"""Core-residual skill-absence component: chronological-refit residual contract (2026-11-13).
Contract (mirrors the publisher's QB residual builder as described by Main):
- For each game g in training_features.json (1416 rows, publisher past-only same-season features,
  min 3 earlier games each team), the core prediction comes from a REFIT on training rows with
  date strictly earlier than g's date (chronology preserved; min 200 training rows, unmirrored
  count). Fit mechanics exactly as publisher build.py: mirrored sample (X,-X),(y,-y),
  StandardScaler (mean 0, ddof=0 std) + Ridge alpha=10, no intercept. Reimplemented in numpy
  (sklearn unavailable here); prediction is invariant to feature column order.
- residual r_g = actual margin_g - chronological core prediction. NOT full-fit in-sample residuals.
- Reference contract, explicit: the core's reference is the mixed realized full-season history
  (publisher, 3:51: continuing absences and replacement production are embedded in realized
  history; no healthy baseline, no personnel projection). The absence coefficient is therefore
  the average residual margin per share unit of same-week Out established skill absence RELATIVE
  TO THAT MIXED REFERENCE - a baseline-relative contrast, not a healthy-baseline effect, and not
  scalar season-share attenuation. Long-IR absences outside same-week Out designations are part
  of the reference, not the event. OBSERVATIONAL. No current-week application.
- Event definition: strict_nfl_game_panel.csv (strict_absence_build.py) - same-week Out only,
  no Doubtful, no carry-forward, no future-team info; undesignated bucket = uncertain events.
Spec: r ~ const + d_injOut_SKILL + d_injOut_QB(control) + d_undes_SKILL + d_undes_QB(control)
+ season indicators (core has no season intercepts; absorb chronological drift).
Two-way cluster-robust SEs, CGM V1+V2-V12 by home/away team.
"""
import json
import pandas as pd, numpy as np

tf=pd.DataFrame(json.load(open('/tmp/inj/nfl/training_features.json')))
tf['date']=pd.to_datetime(tf['date'])
fs=['d_pf','d_pa','d_yf','d_ya','d_completion_rate','d_pass_ypa','d_pass_td_rate','d_pass_int_rate',
    'd_rush_ypa','d_rush_td_rate','d_rec_ypc','d_rec_td_rate','d_record_strength','d_schedule_strength',
    'd_opponent_score_rating','home_field']
tf=tf.sort_values(['date','game_id']).reset_index(drop=True)
X=tf[fs].to_numpy(float); y=tf.margin.to_numpy(float); dates=tf.date.values

def ridge_fit_predict(Xtr,ytr,Xte,alpha=10.0):
    X2=np.vstack([Xtr,-Xtr]); y2=np.r_[ytr,-ytr]
    scale=X2.std(axis=0,ddof=0); scale[scale==0]=1.0
    Xs=X2/scale
    coef=np.linalg.solve(Xs.T@Xs+alpha*np.eye(Xs.shape[1]),Xs.T@y2)
    return (Xte/scale)@coef

resid=np.full(len(tf),np.nan)
for d in np.unique(dates):
    te=dates==d; tr=dates<d
    if tr.sum()<200: continue
    resid[te]=y[te]-ridge_fit_predict(X[tr],y[tr],X[te])
tf['resid']=resid
print('residual rows:',int(tf.resid.notna().sum()),'of',len(tf),'| dropped (first <200-training dates):',int(tf.resid.isna().sum()))

G=pd.read_csv('/tmp/inj/overlay/strict_nfl_game_panel.csv')
M=tf[['game_id','date','resid']].merge(G,on='game_id',how='inner')
M=M[M.resid.notna()].copy()
print('fit rows (residual x strict panel):',len(M))
cnt={'fit_rows':int(len(M)),
 'injOut_skill_events_in_sample':int(M.s_n_injOut_skill_events.sum()),
 'undes_skill_events_in_sample':int(M.s_n_undes_skill_events.sum()),
 'games_with_injOut_skill_share':int((M.s_injOut_SKILL>0).sum())}
json.dump(cnt,open('/tmp/inj/overlay/residual_counts.json','w'),indent=1)
print(json.dumps(cnt,indent=1))
M.to_csv('/tmp/inj/overlay/strict_nfl_residual_panel.csv',index=False)

yv=M.resid.values
Xcols=['d_injOut_SKILL','d_injOut_QB','d_undes_SKILL','d_undes_QB']
sdum=pd.get_dummies(M.season,drop_first=True).astype(float)
Xm=np.hstack([np.ones((len(M),1)),M[Xcols].values,sdum.values])
names=['const']+Xcols+['season_'+str(c) for c in sdum.columns]
n,k=Xm.shape; XtX_inv=np.linalg.inv(Xm.T@Xm); b=XtX_inv@Xm.T@yv; u=yv-Xm@b
def bread(cl):
    B=np.zeros((k,k))
    for _,idx in M.groupby(cl).indices.items():
        Xc=Xm[list(idx)]; uc=u[list(idx)]; B+=Xc.T@np.outer(uc,uc)@Xc
    return B
B=bread('home_team')+bread('away_team')-bread(M.home_team+'@'+M.away_team)
nc=M.home_team.nunique()
V=XtX_inv@B@XtX_inv*(nc/(nc-1))*((n-1)/(n-k))
se=np.sqrt(np.maximum(np.diag(V),0))
out=pd.DataFrame({'term':names,'coef':b.round(4),'se':se.round(4),'t':(b/se).round(2)})
out.to_csv('/tmp/inj/overlay/residual_coefs.csv',index=False)
print(out.to_string(index=False))
print('R2',round(1-u@u/((yv-yv.mean())@(yv-yv.mean())),4),'n',n)
