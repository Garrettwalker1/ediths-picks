import pathlib,json,tempfile,sys,datetime,gzip
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent;B=pathlib.Path(tempfile.mkdtemp(prefix='cfb-sat-boxes-'));by={}
for folder in ['tools/cfb/boxscores','tools/cfb/current_inputs_20261016/boxscores','tools/cfb/week8_20261019/boxscores','tools/cfb/week9_20261026/boxscores','tools/cfb/week10_20261101/boxscores','tools/cfb/saturday_20261107/sources']:
 for f in list((R/folder).glob('boxscore-*.json'))+list((R/folder).glob('boxscore-*.json.gz')):
  d=json.load(gzip.open(f,'rt') if f.suffix=='.gz' else open(f));by[str(d['header']['id'])]=f
for eid,f in by.items():
 if f.suffix=='.gz':(B/f'boxscore-{eid}.json').write_bytes(gzip.decompress(f.read_bytes()))
 else:(B/f'boxscore-{eid}.json').symlink_to(f)
s=(R/'tools/model_cfb_v2/repair_20261011/reference_features.py').read_text()
a=s.index('AP_CACHE=');b=s.index('# ---- features identical',a)
s=s[:a]+"ap_snapshots={2026:[(pd.Timestamp('2026-01-01'),{})]}; tg['ap_points']=0.0\n"+s[b:]
s=s.replace("REPO/'tools/cfb/boxscores'",'Path('+repr(str(B))+')').replace('2026-10-12T02:40:00Z',datetime.datetime.now(datetime.timezone.utc).isoformat()).replace("pd.Timestamp('2026-10-12')","pd.Timestamp('2026-11-07')")
sys.argv=['features',str(R),str(P)];ns={};exec(compile(s,'saturday_features','exec'),ns)
fs=[f for f in ns['FEATS'] if f!='d_ap_points'];hist=ns['hist'];feat=ns['feat26'];model=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(hist[fs],hist.margin)
slate=json.load(open(P/'sources/saturday_book_snapshot.json'));prior={g['event_id']:g for g in json.load(open(R/'tools/cfb/week10_20261101/weekend_refresh_20261105.json'))['games']};games=[]
for e in slate['data']['events']:
 c=e['competitions'][0];t={z['homeAway']:z['team']['displayName'] for z in c['competitors']};h,a=t['home'],t['away']
 if h not in ns['members'] or a not in ns['members']:continue
 vals={f:float(feat.loc[h,f[2:]]-feat.loc[a,f[2:]]) for f in fs};pred=float(model.predict(pd.DataFrame([vals])[fs])[0]);od=(c.get('odds')or[{}])[0]
 games.append({'event_id':e['id'],'home':h,'away':a,'date':e['date'],'model_margin_home':pred,'nov5_margin_home':prior.get(e['id'],{}).get('pred_home_margin'),'book':od,'features':vals,'state':e['status']['type']['state']})
out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'training_rows_by_season':{str(k):int(v) for k,v in hist.groupby('season').size().items()},'completed_summary_ids':sorted(by),'team_game_rows_2026':len(ns['d26']),'training_rows':len(hist),'latest_training_game':str(hist.date.max()),'model':'Unchanged-spec no-AP Ridge alpha10, refit after 12 Week10 finals. No injury/weather adjustment. No AP column consumed; AP loading disabled only to avoid irrelevant calls.','feature_columns':fs,'standard_scaler_mean':model[0].mean_.tolist(),'standard_scaler_scale':model[0].scale_.tolist(),'coefficients':model[1].coef_.tolist(),'intercept':float(model[1].intercept_),'games':games,'book_source':slate['url'],'book_captured_at':slate['fetched_at'],'warnings':['Research model, no calibrated win/ATS/joint probabilities or proven edge.','Historical seals unchanged. Book prices never input features.','No injury numeric adjustments; no validated weather margin adjustment.']}
(P/'saturday_research_refresh.json').write_text(json.dumps(out,indent=2));feat.to_csv(P/'saturday_team_features.csv');print('RESULT',len(hist),hist.date.max(),len(games))
# Outputs are research-only and require review before any publication.
