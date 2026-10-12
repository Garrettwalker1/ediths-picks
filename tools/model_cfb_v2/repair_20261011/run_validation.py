"""Historical diagnostic plus locked future Week7 protocol. No publication mutation."""
import sys,json,numpy as np,pandas as pd,hashlib,datetime
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
REPO=Path(sys.argv[1]);OUT=REPO/'tools/model_cfb_v2/repair_20261011';sys.argv=['reference',str(REPO),str(OUT)]
exec(compile((OUT/'reference_features.py').read_text(),'reference_features','exec'))
base=[f for f in FEATS if f!='d_ap_points'];sub=gm.dropna(subset=FEATS+['margin']).copy();tr=sub[sub.season<=2023];va=sub[sub.season==2024];past=sub[sub.season==2025]
def metric(y,p):return {'n':len(y),'mae':float(np.mean(abs(y-p))),'winner_correct':int(np.sum(np.sign(y)==np.sign(p))),'winner_accuracy':float(np.mean(np.sign(y)==np.sign(p)))}
res={};models={}
for n,fs in [('full_no_ap',base),('full_ap_points',FEATS)]:
 m=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[fs],tr.margin);v=m.predict(va[fs]);p=m.predict(past[fs]);res[n]={'features':fs,'validation2024':metric(va.margin.to_numpy(),v),'previously_examined2025':metric(past.margin.to_numpy(),p)};models[n]=(m,fs);past[n]=p
# Winner-first validation gate; MAE secondary. No adoption from examined 2025.
selected=max(res,key=lambda n:(res[n]['validation2024']['winner_accuracy'],-res[n]['validation2024']['mae']))
rng=np.random.default_rng(261011);y=past.margin.to_numpy();diff=abs(y-past.full_ap_points.to_numpy())-abs(y-past.full_no_ap.to_numpy());wd=(np.sign(y)==np.sign(past.full_ap_points.to_numpy())).astype(int)-(np.sign(y)==np.sign(past.full_no_ap.to_numpy())).astype(int)
b=np.array([[diff[ix].mean(),wd[ix].mean()] for ix in [rng.integers(len(diff),size=len(diff)) for _ in range(5000)]]);res['diagnostic_delta_ap_vs_no_ap']={'mae':float(diff.mean()),'mae_ci95':np.quantile(b[:,0],[.025,.975]).tolist(),'winner_accuracy':float(wd.mean()),'winner_ci95':np.quantile(b[:,1],[.025,.975]).tolist()}
assert not hist.event_id.astype(str).str.startswith('__ASOF__').any();counts=hist.groupby('season').size().to_dict();assert counts[2026]>200;res['refit_rows_by_season']={str(k):int(v) for k,v in counts.items()};res['selected_validation_only']=selected;res['adopted']=False;res['fresh_holdout']='2026 Week7 outcomes, not yet played, Oct13-19. All historical 2025 and Week1-6 2026 are already examined.';res['limits']=['No historical set is being relabeled untouched.','Historical preseason churn derived from season participation, historical neutral sites not flagged, and prior imputation remain incumbent limitations.','AP omitted archives before Week4 2026 cause zero AP feature for those earlier games; excluded from new forward holdout evaluation only, not hidden.','Totals remain null; no book inputs.'];json.dump(res,open(OUT/'validation_diagnostic.json','w'),indent=2)
print(json.dumps(res,indent=2))
