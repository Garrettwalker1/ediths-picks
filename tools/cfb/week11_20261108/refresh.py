"""No-AP Week11 research forecast. Unchanged specification, repaired summary coverage.
Preserves previous seals. No injury/QB/weather numerical adjustment; no AP feature.
"""
import pathlib,json,tempfile,sys,datetime,gzip,hashlib
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent
assert not (P/'week11_sealed_research.json').exists(),'Never overwrite a seal'
for p in R.glob('tools/**/*sealed_research.sha256'):assert hashlib.sha256(p.with_suffix('.json').read_bytes()).hexdigest()==p.read_text().split()[0]
B=pathlib.Path(tempfile.mkdtemp(prefix='cfb-week11-boxes-'));by={}
folders=['tools/cfb/boxscores','tools/cfb/current_inputs_20261016/boxscores','tools/cfb/saturday_20261107/sources']+sorted(str(p.relative_to(R))for p in (R/'tools/cfb').glob('week*_20*/boxscores'))
for folder in folders:
 for f in sorted(list((R/folder).glob('boxscore-*.json'))+list((R/folder).glob('boxscore-*.json.gz'))):
  d=json.load(gzip.open(f,'rt')if f.suffix=='.gz'else open(f));by[str(d['header']['id'])]=f
required=set(json.load(open(P/'fetch_audit.json'))['ids']);assert required==set(by),(len(required),len(by))
for eid,f in by.items():
 d=json.load(gzip.open(f,'rt')if f.suffix=='.gz'else open(f));assert d['header']['competitions'][0]['status']['type']['completed'];assert len(d['boxscore']['teams'])==2
 for t in d['boxscore']['teams']:
  names={s['name']for s in t['statistics']};assert {'totalYards','netPassingYards','rushingYards','turnovers'}<=names,(eid,names)
 (B/f'boxscore-{eid}.json').write_text(json.dumps(d))
now=datetime.datetime.now(datetime.timezone.utc);cutoff=now.isoformat();s=(R/'tools/model_cfb_v2/repair_20261011/reference_features.py').read_text();a=s.index('AP_CACHE=');b=s.index('# ---- features identical',a);s=s[:a]+"ap_snapshots={2026:[(pd.Timestamp('2026-01-01'),{})]}; tg['ap_points']=0.0\n"+s[b:];s=s.replace("REPO/'tools/cfb/boxscores'",'Path('+repr(str(B))+')').replace('2026-10-12T02:40:00Z',cutoff).replace("pd.Timestamp('2026-10-12')","pd.Timestamp('2026-11-09')")
sys.argv=['features',str(R),str(P)];ns={};exec(compile(s,'week11_noap_features','exec'),ns)
fs=[f for f in ns['FEATS']if f!='d_ap_points'];hist=ns['hist'];feat=ns['feat26'];assert set(ns['d26'].event_id.astype(str))==required;assert hist.date.max()<pd.Timestamp(now).tz_convert(None)
model=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(hist[fs],hist.margin);games=[];excluded=[];slate=json.load(open(P/'sources/week11.json'));manifest=json.load(open(P/'source_manifest.json'));capture=next(m['received_at']for m in manifest if m['file']=='sources/week11.json')
for e in slate['events']:
 c=e['competitions'][0];assert c['status']['type']['state']=='pre';assert pd.Timestamp(c['date'])>pd.Timestamp(cutoff);t={z['homeAway']:z['team']['displayName']for z in c['competitors']};h,a=t['home'],t['away']
 if h not in ns['members']or a not in ns['members']:excluded.append({'event_id':e['id'],'name':e['name'],'reason':'not FBS versus FBS'});continue
 vals={f:float(feat.loc[h,f[2:]]-feat.loc[a,f[2:]])for f in fs};assert np.isfinite(list(vals.values())).all();pred=float(model.predict(pd.DataFrame([vals])[fs])[0]);o=(c.get('odds')or[{}])[0];bl=o.get('spread');fav=(o.get('homeTeamOdds')or{}).get('favorite')
 if bl is not None and fav is not None:assert bl==0 or (float(bl)<0)==bool(fav),(e['id'],o)
 book=None if not o else {'home_line':bl,'details':o.get('details'),'over_under':o.get('overUnder'),'provider':(o.get('provider')or{}).get('name'),'captured_at':capture,'source':'ESPN scoreboard pregame snapshot, comparison only'}
 games.append({'event_id':e['id'],'home':h,'away':a,'name':e['name'],'date':c['date'],'predicted_margin_home':{'2026_no_ap':pred},'features':vals,'book':book,'neutral_site':bool(c.get('neutralSite')),'model_total':None,'injury_adjusted_margin_home':None,'weather_adjusted_margin_home':None})
protocol={'sealed_at':cutoff,'train_cutoff':cutoff,'feature_cutoff':cutoff,'purpose':'Research-only unchanged-spec no-AP refit with all 685 completed 2026 summaries. Raw-data coverage repaired; not a replacement for prior sealed forecasts. Not validated betting edge.','coverage':{'scheduled':len(slate['events']),'scored_fbs_vs_fbs':len(games),'excluded':excluded},'training_rows_by_season':{str(k):int(v)for k,v in hist.groupby('season').size().items()},'training_rows':len(hist),'raw_completed_2026_summary_count':len(by),'team_game_rows_2026':len(ns['d26']),'latest_training_game':str(hist.date.max()),'feature_columns':fs,'standard_scaler_mean':model[0].mean_.tolist(),'standard_scaler_scale':model[0].scale_.tolist(),'coefficients':model[1].coef_.tolist(),'intercept':float(model[1].intercept_),'limits':['AP research-only, not loaded or consumed.','No numerical injury/QB/weather effect, no model totals, no calibrated probabilities.','Earlier Nov5 exact replay discrepancy remains unresolved, max 0.043688 points; no exact-reproduction claim.','Book numbers frozen at capture, never input features.','Neutral-site indicator is not a fitted model input in this unchanged specification.']}
out={'protocol':protocol,'games':sorted(games,key=lambda g:g['date'])};raw=json.dumps(out,sort_keys=True,indent=2)+'\n';(P/'week11_sealed_research.json').write_text(raw);(P/'week11_sealed_research.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  week11_sealed_research.json\n');feat.to_csv(P/'current_team_features.csv');freeze={'sealed_at':cutoff,'rule':'Model winner equals book underdog at captured selection-time reference; not closing-time bucket','games':[]}
for g in games:
 pred=g['predicted_margin_home']['2026_no_ap'];bl=(g['book']or{}).get('home_line');mp=g['home']if pred>0 else g['away'];dog=None if bl is None or bl==0 else g['home']if bl>0 else g['away'];freeze['games'].append({'event_id':g['event_id'],'name':g['name'],'model_pick':mp,'model_margin_home':pred,'book_home_line':bl,'book_underdog':dog,'dog_bucket':None if dog is None else mp==dog})
(P/'week11_dog_bucket_freeze.json').write_text(json.dumps(freeze,indent=2));print('SEALED',len(games),'FIT',len(hist),hist.groupby('season').size().to_dict(),'DOG',sum(g['dog_bucket']is True for g in freeze['games']))
