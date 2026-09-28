#!/usr/bin/env python3
"""Weather-free stress test of the partial chronology repair; NOT a promotion."""
import json
from pathlib import Path
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.metrics import mean_absolute_error,accuracy_score,brier_score_loss
H=Path(__file__).resolve().parent
ref=json.loads((H/'diagnostic.json').read_text());drop={'dome','wind','cold','wind_x_dpyf'}
f=[z for z in ref['feature_order'] if z not in drop]
x=pd.read_parquet(H/'frame_lagged_2010_2025.parquet').dropna(subset=f+['margin']);tr=x[x.season<=2022];va=x[x.season==2023];te=x[x.season.isin([2024,2025])]
m=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[f],tr.margin);pv=m.predict(va[f]);pt=m.predict(te[f]);c=LogisticRegression(max_iter=1000).fit(m.predict(tr[f]).reshape(-1,1),(tr.margin>0).astype(int));pr=c.predict_proba(pt.reshape(-1,1))[:,1];y=(te.margin>0).astype(int)
result={'status':'weather_free_diagnostic_not_promoted','feature_order':f,'excluded_weather_features':sorted(drop),'validation_mae':mean_absolute_error(va.margin,pv),'test_mae':mean_absolute_error(te.margin,pt),'market_test_mae':mean_absolute_error(te.margin,te.spread_line),'test_winner_accuracy':accuracy_score(y,pt>0),'test_brier':brier_score_loss(y,pr),'caveat':'Still not fully point-in-time (injury report final labels and season roster identity sources not archived as-of). No saved Week 3 baseline feature row or Keenum-vs-Bagent feature. Worse than market.'}
assert result['test_mae']>result['market_test_mae']
(H/'weather_ablation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
