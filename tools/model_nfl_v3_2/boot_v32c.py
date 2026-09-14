import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
gm=pd.read_parquet('/tmp/training/nflv32/out/v32c_games.parquet')
V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
V32B=V1+NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']
V32C=V32B+['d_oc_new','d_dc_new']
sub=gm.dropna(subset=V32C+['margin']).copy()
tr=sub[sub.season<=2022]; va=sub[sub.season==2023]; te=sub[sub.season>=2024]
mb=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[V32B],tr.margin)
mc=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[V32C],tr.margin)
te=te.assign(pred_b=mb.predict(te[V32B]), pred_c=mc.predict(te[V32C]))
print(f'n={len(te)} v3.2b={mean_absolute_error(te.margin,te.pred_b):.3f} v3.2c={mean_absolute_error(te.margin,te.pred_c):.3f} mkt={mean_absolute_error(te.margin,te.spread_line):.3f}')
rng=np.random.default_rng(42); idx=np.arange(len(te)); B=500
for lbl,base,col in (('v3.2c-minus-mkt MAE',None,'pred_c'),('v3.2c-minus-v3.2b MAE','pred_b','pred_c')):
    if base is None:
        d=(te.margin-te[col]).abs()-(te.margin-te.spread_line).abs()
    else:
        d=(te.margin-te[col]).abs()-(te.margin-te[base]).abs()
    arr=[d.iloc[rng.choice(idx,len(idx),replace=True)].mean() for _ in range(B)]
    lo,hi=np.percentile(arr,[2.5,97.5]); print(f'  {lbl}: mean={np.mean(arr):.3f} CI95=[{lo:.3f},{hi:.3f}] (negative favors v3.2c)')
