#!/usr/bin/env python3
"""Evaluate leakage-reduced reference feature subset. Diagnostic, NOT promoted."""
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.metrics import mean_absolute_error,accuracy_score,brier_score_loss,log_loss
HERE=Path(__file__).resolve().parent
FRAME=HERE/'frame_lagged_2010_2025.parquet'
BASE=json.loads((HERE.parent/'v32b_fit_2010_2025.json').read_text())
F=[x for x in BASE['feature_order'] if x not in ('d_ret_share','d_incoming_prod','d_qb_same')]
x=pd.read_parquet(FRAME).dropna(subset=F+['margin'])
tr=x[x.season<=2022];va=x[x.season==2023];te=x[x.season.isin([2024,2025])]
assert (len(tr),len(va),len(te))==(2623,256,512)
m=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[F],tr.margin)
pv=m.predict(va[F]);pt=m.predict(te[F]);cal=LogisticRegression(max_iter=1000).fit(m.predict(tr[F]).reshape(-1,1),(tr.margin>0).astype(int))
y=(te.margin>0).astype(int);pr=cal.predict_proba(pt.reshape(-1,1))[:,1]
metrics={'validation_2023_mae':mean_absolute_error(va.margin,pv),'locked_2024_25_mae':mean_absolute_error(te.margin,pt),'closing_spread_mae':mean_absolute_error(te.margin,te.spread_line),'winner_accuracy':accuracy_score(y,(pt>0).astype(int)),'winner_brier':brier_score_loss(y,pr),'winner_logloss':log_loss(y,pr)}
# No promotion: candidate loses validation benchmark (10.556) and market test.
assert metrics['validation_2023_mae']>BASE['metrics']['validation_mae'] and metrics['locked_2024_25_mae']>metrics['closing_spread_mae']
sub=x;final=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(sub[F],sub.margin)
raw=final[-1].coef_/final[0].scale_;intercept=float(final[-1].intercept_-(raw*final[0].mean_).sum())
a={'status':'forensic_diagnostic_not_adopted','reasons':['Selected 23 features lose 2023 validation against archived v3.2b, which itself contains leaks','Locked test worse than closing spread','Same-week weather in source is observed weather, not archived pregame forecast; not a fully point-in-time training frame','No saved Week 3 as-of input row or QB-starter effect'],'frame_sha256':hashlib.sha256(FRAME.read_bytes()).hexdigest(),'feature_order':F,'metrics':metrics,'training_counts':[len(tr),len(va),len(te)],'fit_2010_25':{'ridge_alpha':10,'scaler_mean':final[0].mean_.tolist(),'scaler_scale':final[0].scale_.tolist(),'ridge_intercept_standardized':float(final[-1].intercept_),'ridge_coefficients_standardized':final[-1].coef_.tolist(),'raw_intercept':intercept,'raw_coefficients':dict(zip(F,map(float,raw)))}}
(HERE/'diagnostic.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'status':a['status'],'metrics':metrics},indent=2))
