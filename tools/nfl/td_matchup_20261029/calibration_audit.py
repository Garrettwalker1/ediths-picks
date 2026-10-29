import pandas as pd,numpy as np,json,joblib,pathlib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,log_loss
P=pathlib.Path('/tmp/td-matchup/out');d=pd.read_pickle(P/'dataset.pkl');tr=d.season<=2023;va=d.season==2024;te=d.season==2025;res={}
for name,feat in [('calibrated_history_only',['baseline_logit']),('history_plus_position',['baseline_logit','pos_QB','pos_RB','pos_TE'])]:
 choices=[]
 for c in [.01,.1,1]:
  m=make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=1000)).fit(d.loc[tr,feat],d.loc[tr,'y']);choices.append((log_loss(d.loc[va,'y'],m.predict_proba(d.loc[va,feat])[:,1]),c,m))
 _,c,m=min(choices,key=lambda x:x[0]);res[name]={'C':c}
 for n,mask in [('validation2024',va),('seen2025',te)]:
  p=m.predict_proba(d.loc[mask,feat])[:,1];res[name][n]={'brier':brier_score_loss(d.loc[mask,'y'],p),'logloss':log_loss(d.loc[mask,'y'],p)}
p=json.load(open(P/'diagnostics.json'));p['calibration_ablation_audit']=res;p['interpretation']='Research-only. Cohort excludes inactive zeros; current role/availability conditioning not validated.2025seen. Need prospective comparison.';json.dump(p,open(P/'diagnostics.json','w'),indent=2);print(json.dumps(res,indent=2))
