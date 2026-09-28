#!/usr/bin/env python3
"""Reproduce v3.2b and persist its coefficients. No book inputs.

Usage: python3 train.py [--check-only]. The input frame is built by the original
build_v32.py + build_v32b.py; see README.md for upstream reconstruction.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd,sklearn
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error,brier_score_loss
R=Path(__file__).resolve().parent;FRAME=R/'training_frame_2010_2025.parquet';OUT=R/'v32b_fit_2010_2025.json'
V1=['d_'+s for s in ['pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp']]
NEW=['d_rest','d_ret_share','d_incoming_prod','d_qb_same','d_qb_out','d_coach_new']
FEATS=V1+NEW+['d_inj_impact','dome','wind','cold','wind_x_dpyf']
def fit(frame):
 assert frame.season.max()==2025 and frame.season.min()==2010
 assert not frame.game_id.duplicated().any()
 sub=frame.dropna(subset=FEATS+['margin']).copy()
 tr=sub[sub.season<=2022];va=sub[sub.season==2023];te=sub[sub.season.isin([2024,2025])]
 assert len(tr)>2500 and len(va)>240 and len(te)==512,(len(tr),len(va),len(te))
 reference=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(tr[FEATS],tr.margin)
 metrics={'train_n':len(tr),'validation_n':len(va),'locked_test_n':len(te),'validation_mae':mean_absolute_error(va.margin,reference.predict(va[FEATS])),'locked_test_mae':mean_absolute_error(te.margin,reference.predict(te[FEATS]))}
 assert abs(metrics['validation_mae']-10.556)<0.002,metrics
 assert abs(metrics['locked_test_mae']-10.239)<0.002,metrics
 # Refit reference specification, without selecting new features from locked test.
 model=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(sub[FEATS],sub.margin)
 raw=model[-1].coef_/model[0].scale_
 # Mapping from margin to probability is a separate retrospective fit; not a
 # validated moneyline edge and not used to choose a winner model.
 scores=model.predict(sub[FEATS]);cal=LogisticRegression(max_iter=1000).fit(scores.reshape(-1,1),(sub.margin>0).astype(int))
 artifact={'schema_version':'1.0.0','model':'NFL v3.2b full-history reference refit, measurement only','training_frame_sha256':hashlib.sha256(FRAME.read_bytes()).hexdigest(),'feature_order':FEATS,'training_seasons':[2010,2025],'row_count':len(sub),'ridge_alpha':10.0,'sklearn_version':sklearn.__version__,'metrics':metrics,'scaler_mean':model[0].mean_.tolist(),'scaler_scale':model[0].scale_.tolist(),'ridge_intercept_standardized':float(model[-1].intercept_),'ridge_coefficients_standardized':model[-1].coef_.tolist(),'raw_coefficients':dict(zip(FEATS,map(float,raw))),'raw_intercept':float(model[-1].intercept_-(raw*model[0].mean_).sum()),'calibration':{'intercept':float(cal.intercept_[0]),'margin_coef':float(cal.coef_[0][0]),'caveat':'In-sample retrospective mapping. Not as-of validated; failed closing moneyline benchmark.'},'leakage_rule':'No outcomes or book values from target game enter features. Week-2026 reports must be captured as-of; missing inputs block scoring.'}
 predicted=sub[FEATS].to_numpy()@raw+artifact['raw_intercept'];assert np.max(np.abs(predicted-scores))<1e-10
 return artifact
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
 a=fit(pd.read_parquet(FRAME));print(json.dumps({'metrics':a['metrics'],'row_count':a['row_count'],'qb_out_slope':a['raw_coefficients']['d_qb_out'],'inj_impact_slope':a['raw_coefficients']['d_inj_impact']},indent=2))
 if not args.check_only:OUT.write_text(json.dumps(a,indent=2)+'\n')
