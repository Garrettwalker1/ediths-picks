"""Freeze research-only forward candidates. Never updates operational board."""
import sys,json,hashlib,datetime
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
REPO=Path(sys.argv[1]);OUT=REPO/'tools/model_cfb_v2/repair_20261011';sys.argv=['seal',str(REPO),str(OUT)]
exec(compile((OUT/'reference_features.py').read_text(),'reference_features','exec'))
fs_no=[f for f in FEATS if f!='d_ap_points'];fitted={}
for name,fs,rows in [('2026_ap',FEATS,hist),('2026_no_ap',fs_no,hist),('historical_ap',FEATS,hist[hist.season<2026]),('historical_no_ap',fs_no,hist[hist.season<2026])]:fitted[name]=(make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(rows[fs],rows.margin),fs)
es={}
for p in (OUT/'week7_slate_sources').glob('*.json'):
 for e in json.load(open(p)).get('events',[]):es[e['id']]=e
pred=[];gaps=[]
for eid,e in sorted(es.items(),key=lambda kv:kv[1]['date']):
 c=e['competitions'][0];assert c['status']['type']['state']=='pre';teams={p['homeAway']:p['team']['displayName'] for p in c['competitors']};h=teams['home'];a=teams['away']
 if h not in members or a not in members or h not in feat26.index or a not in feat26.index:gaps.append({'event_id':eid,'name':e['name'],'reason':'not both current FBS teams with features'});continue
 vals={f:float(feat26.loc[h,f[2:]]-feat26.loc[a,f[2:]]) for f in FEATS}
 if not np.isfinite(list(vals.values())).all():gaps.append({'event_id':eid,'name':e['name'],'reason':'missing pre-cutoff features'});continue
 predictions={n:float(m.predict(pd.DataFrame([vals])[fs])[0]) for n,(m,fs) in fitted.items()}
 pred.append({'event_id':eid,'date':c['date'],'home':h,'away':a,'neutral_site':bool(c.get('neutralSite')),'features':vals,'predicted_margin_home':predictions,'winners':{n:h if v>0 else a for n,v in predictions.items()},'research_only':True})
now=datetime.now(ZoneInfo('UTC')).isoformat();protocol={'sealed_at':now,'outcome_holdout':'2026 Week7, Oct13-19; no outcomes played or inspected at seal','purpose':'Research only, no Week7 operational board until gates pass','models':list(fitted),'train_cutoff':'2026-10-12T02:40:00Z','training_rows':len(hist),'training_2026_rows':int(sum(hist.season==2026)),'primary_metric':'paired winner accuracy; book-favorite benchmark reported separately using pregame comparison quotes','secondary_metric':'paired margin MAE','bootstrap':'5000 resamples at game level, seed261019','adoption_gates':['Winner accuracy improvement AP vs noAP and 2026-inclusive vs historical-only must each have 95% CI lower bound above zero.','MAE increase must not be settled worse (95% CI lower bound must not exceed zero).','No market-beating or betting-edge claim without separate timestamped book benchmark and a settled interval.','Insufficient sample/zero-crossing CI means no adoption, keep candidates research-only and extend with a newly predeclared future week, never retune against Week7 outcomes.'],'coverage':{'scheduled':len(es),'scored_fbs_vs_fbs':len(pred),'excluded':gaps},'source_urls':[f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={d}&groups=80&limit=400' for d in ['20261013','20261014','20261015','20261016','20261017','20261018','20261019']],'known_data_gaps':skipped}
output={'protocol':protocol,'games':pred};raw=json.dumps(output,sort_keys=True,indent=2)+'\n';(OUT/'week7_sealed_research.json').write_text(raw);(OUT/'week7_sealed_research.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  week7_sealed_research.json\n');print('SEALED',protocol['coverage'],protocol['training_rows'],protocol['training_2026_rows'])
