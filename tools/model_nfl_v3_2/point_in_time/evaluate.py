#!/usr/bin/env python3
"""Validation-first fixed-feature baseline; report failed gates, never auto-promote."""
import json,hashlib,sys
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.metrics import mean_absolute_error,accuracy_score,brier_score_loss
from build_frame import FEATURES
H=Path(__file__).resolve().parent
x=pd.read_parquet(sys.argv[1]);x=x[(x.season<=2025)&x.margin.notna()].dropna(subset=FEATURES+['spread_line']);tr=x[x.season<=2022];va=x[x.season==2023];te=x[x.season.isin([2024,2025])];assert len(te)==512 and len(va)==256
reg=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[FEATURES],tr.margin);pv=reg.predict(va[FEATURES]);pt=reg.predict(te[FEATURES]);
# Calibrate straight-up on out-of-fold prior training seasons, not in-sample.
train_preds=[];train_labels=[]
for season in sorted(tr.season.unique()):
 if season<2017:continue
 history=tr[tr.season<season];held=tr[tr.season==season]
 fold=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(history[FEATURES],history.margin)
 train_preds.extend(fold.predict(held[FEATURES]));train_labels.extend((held.margin>0).astype(int))
cal=LogisticRegression(max_iter=1000).fit(np.array(train_preds).reshape(-1,1),train_labels);pr=cal.predict_proba(pt.reshape(-1,1))[:,1];y=(te.margin>0).astype(int)
rng=np.random.default_rng(20260929);delta=np.abs(te.margin.to_numpy()-pt)-np.abs(te.margin.to_numpy()-te.spread_line.to_numpy());ci=np.percentile([delta[rng.choice(len(delta),len(delta),replace=True)].mean() for _ in range(1000)],[2.5,97.5]).tolist()
metrics={'train_count':len(tr),'validation_count':len(va),'locked_test_count':len(te),'validation_mae':mean_absolute_error(va.margin,pv),'validation_book_mae':mean_absolute_error(va.margin,va.spread_line),'test_mae':mean_absolute_error(te.margin,pt),'test_book_mae':mean_absolute_error(te.margin,te.spread_line),'test_winner_accuracy':accuracy_score(y,pt>0),'test_book_winner_accuracy':accuracy_score(y,te.spread_line>0),'test_brier':brier_score_loss(y,pr),'test_book_brier':brier_score_loss(y,np.where(te.home_moneyline<0,-te.home_moneyline/(-te.home_moneyline+100),100/(te.home_moneyline+100))),'test_mae_minus_book_ci95':ci}
# This is a comparison to the archived closing line, not to a point-in-time book quote.
pass_gate=metrics['validation_mae']<metrics['validation_book_mae'] and metrics['test_mae']<metrics['test_book_mae'] and ci[1]<0 and metrics['test_brier']<metrics['test_book_brier']
result={'status':'passes_clean_gate' if pass_gate else 'failed_clean_gate_not_promoted','features':FEATURES,'source_frame_sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'split':'train 2010-22; validation 2023; locked test 2024-25','metrics':metrics,'limitations':['Team-form features only; no same-week injuries, QB starter, weather, or roster participation','Closing spread is the test benchmark; not a feature','No Week 4 model outputs may be published from a failed candidate']}
(H/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
