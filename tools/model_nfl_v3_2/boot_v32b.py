import numpy as np, pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, brier_score_loss, log_loss, accuracy_score
D='/tmp/training/nflv32'
gm=pd.read_parquet(D+'/out/v32b_games.parquet')
V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
V32B=V1+NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']
sub=gm.dropna(subset=V32B+['margin']).copy()
tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
m=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[V32B],tr.margin)
te=te.assign(pred=m.predict(te[V32B]))
# Elo
K=20.0; base=1500.0; hfa=48.0; elo={}; preds=[]
for r in gm.sort_values(['season','week']).itertuples():
    eh,ea=elo.get(r.home_team,base),elo.get(r.away_team,base)
    exp=1/(1+10**(-((eh+hfa)-ea)/400)); preds.append((r.game_id,((eh+hfa)-ea)/25.0))
    mov=max(1,abs(r.margin)/20)
    elo[r.home_team]=eh+K*mov*((1 if r.margin>0 else 0)-exp); elo[r.away_team]=ea-K*mov*((1 if r.margin>0 else 0)-exp)
el=pd.DataFrame(preds,columns=['game_id','elo_pred'])
te=te.merge(el,on='game_id')
print(f'v3.2b TEST n={len(te)}: model MAE={mean_absolute_error(te.margin,te.pred):.3f} mkt MAE={mean_absolute_error(te.margin,te.spread_line):.3f} elo MAE={mean_absolute_error(te.margin,te.elo_pred):.3f}')
print(f'ATS vs close: {(np.sign(te.pred-te.spread_line)==np.sign(te.margin-te.spread_line)).mean():.3f}')
for yr in (2024,2025):
    t=te[te.season==yr]
    print(f'  {yr}: model={mean_absolute_error(t.margin,t.pred):.2f} mkt={mean_absolute_error(t.margin,t.spread_line):.2f} elo={mean_absolute_error(t.margin,t.elo_pred):.2f} ats={(np.sign(t.pred-t.spread_line)==np.sign(t.margin-t.spread_line)).mean():.3f}')
rng=np.random.default_rng(42)
d_elo=(te.margin-te.pred).abs()-(te.margin-te.elo_pred).abs()
d_mkt=(te.margin-te.pred).abs()-(te.margin-te.spread_line).abs()
idx=np.arange(len(te)); B=500
be=[d_elo.iloc[rng.choice(idx,len(idx),replace=True)].mean() for _ in range(B)]
bm=[d_mkt.iloc[rng.choice(idx,len(idx),replace=True)].mean() for _ in range(B)]
for lbl,arr in (('model-minus-elo MAE',be),('model-minus-mkt MAE',bm)):
    lo,hi=np.percentile(arr,[2.5,97.5]); print(f'  {lbl}: mean={np.mean(arr):.3f} CI95=[{lo:.3f},{hi:.3f}] (negative favors model)')
# moneyline benchmark
def ml_prob(ml):
    ml=np.asarray(ml,dtype=float); return np.where(ml<0,-ml/(-ml+100),100/(ml+100))
te=te.dropna(subset=['home_moneyline']).copy()
te=te.assign(mkt_hwp=ml_prob(te.home_moneyline))
lr=LogisticRegression(max_iter=1000).fit(tr[['d_pf_f']].assign(x=0)[['x']], (tr.margin>0).astype(int)) if False else None
lr=LogisticRegression(max_iter=1000).fit(tr.margin.values.reshape(-1,1), (tr.margin>0).astype(int))
# fit prob mapping on train predicted margins
trp=m.predict(tr[V32B]); lr=LogisticRegression(max_iter=1000).fit(trp.reshape(-1,1),(tr.margin>0).astype(int))
te=te.assign(mod_hwp=lr.predict_proba(te.pred.values.reshape(-1,1))[:,1], home_win=(te.margin>0).astype(int))
print(f'ML: model acc={accuracy_score(te.home_win,te.mod_hwp>0.5):.3f} brier={brier_score_loss(te.home_win,te.mod_hwp):.4f} logloss={log_loss(te.home_win,te.mod_hwp):.4f}')
print(f'    mkt   acc={accuracy_score(te.home_win,te.mkt_hwp>0.5):.3f} brier={brier_score_loss(te.home_win,te.mkt_hwp):.4f} logloss={log_loss(te.home_win,te.mkt_hwp):.4f}')
