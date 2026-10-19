import sys,json,pathlib,tempfile,hashlib,datetime
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent
src=(R/'tools/model_cfb_v2/repair_20261011/reference_features.py').read_text();sys.argv=['features',str(R),str(P)]
ns={};exec(compile(src,'sealed_reference','exec'),ns)
sealed=json.load(open(R/'tools/model_cfb_v2/repair_20261011/week7_sealed_research.json'));fs=ns['FEATS'];no=[f for f in fs if f!='d_ap_points'];models={}
for name,feats,rows in [('2026_no_ap',no,ns['hist']),('2026_ap',fs,ns['hist']),('historical_no_ap',no,ns['hist'][ns['hist'].season<2026]),('historical_ap',fs,ns['hist'][ns['hist'].season<2026])]:
 models[name]=(make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(rows[feats],rows.margin),feats)
for g in sealed['games']:
 for n,(m,f) in models.items():assert abs(float(m.predict(pd.DataFrame([g['features']])[f])[0])-g['predicted_margin_home'][n])<1e-8
print('SEALED REPRODUCED',len(sealed['games']))
B=pathlib.Path(tempfile.mkdtemp(prefix='cfb8-boxes-'));by={}
for folder in ['tools/cfb/boxscores','tools/cfb/current_inputs_20261016/boxscores','tools/cfb/week8_20261019/boxscores']:
 for f in (R/folder).glob('*.json'):
  d=json.load(open(f));by[str(d['header']['id'])]=f
for eid,f in by.items():(B/f'boxscore-{eid}.json').symlink_to(f)
now=datetime.datetime.now(datetime.timezone.utc);cutoff=now.isoformat();current=src.replace("REPO/'tools/cfb/boxscores'",'Path('+repr(str(B))+')').replace('2026-10-12T02:40:00Z',cutoff).replace("pd.Timestamp('2026-10-12')","pd.Timestamp('2026-10-19')")
current=current.replace('model=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(hist[FEATS],hist.margin)','model=SEALED_MODEL')
ns2={'SEALED_MODEL':models['2026_ap'][0]};exec(compile(current,'current_features_fixed_coefficients','exec'),ns2)
feat=ns2['feat26'];members=ns2['members'];feat.to_csv(P/'current_team_features.csv')
# Every current final must have exactly two team rows; overlay wins over stale original.
audit=json.load(open(P/'fetch_audit.json'));rows26=ns2['d26'];assert set(rows26.event_id.astype(str))==set(audit['ids']);assert len(rows26)==2*audit['finals']
slate=json.load(open(P/'sources/week8.json'));games=[];excluded=[]
for e in slate['events']:
 c=e['competitions'][0];assert c['status']['type']['state']=='pre';t={z['homeAway']:z['team']['displayName'] for z in c['competitors']};h,a=t['home'],t['away']
 if h not in members or a not in members:excluded.append({'event_id':e['id'],'name':e['name'],'reason':'not FBS versus FBS'});continue
 vals={f:float(feat.loc[h,f[2:]]-feat.loc[a,f[2:]]) for f in fs};assert np.isfinite(list(vals.values())).all()
 preds={n:float(m.predict(pd.DataFrame([vals])[f])[0]) for n,(m,f) in models.items()}
 games.append({'event_id':e['id'],'name':e['name'],'date':c['date'],'home':h,'away':a,'neutral_site':bool(c.get('neutralSite')),'predicted_margin_home':preds,'features':vals,'model_total':None,'injury_adjusted_margin_home':None,'weather_adjusted_margin_home':None,'book':None})
protocol=dict(sealed['protocol']);protocol.update({'sealed_at':now.isoformat(),'outcome_holdout':'2026 Week8, Oct20-26; every event verified pregame','purpose':'No-AP reference; AP/recency variants research-only. Fixed original coefficients, current features through Week7. No retuning against Week7 outcomes.','train_cutoff':'2026-10-12T02:40:00Z','feature_cutoff':cutoff,'coverage':{'scheduled':len(slate['events']),'scored_fbs_vs_fbs':len(games),'excluded':excluded},'source_urls':[f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week={w}&groups=80&limit=400' for w in range(1,9)],'known_data_gaps':[]})
out={'protocol':protocol,'games':sorted(games,key=lambda g:g['date'])};raw=json.dumps(out,sort_keys=True,indent=2)+'\n';(P/'week8_sealed_research.json').write_text(raw);(P/'week8_sealed_research.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  week8_sealed_research.json\n')
stand=json.load(open(P/'sources/standings.json'));teams={}
def walk(j):
 for e in j.get('standings',{}).get('entries',[]):teams[e['team']['displayName']]=e
 for c in j.get('children',[]):walk(c)
walk(stand)
X=feat.loc[sorted(members.intersection(feat.index))];assert len(X)==138
ap=next(p for p in json.load(open(R/'tools/model_cfb_v2/ap_poll/ap-2026-week8.json'))['rankings'] if p.get('type')=='ap');apr={r['team']['location']+' '+r['team']['name']:r['current'] for r in ap['ranks']}
ratings={}
for n in ['2026_no_ap','2026_ap']:
 m,f=models[n];coef=m[-1].coef_/m[0].scale_;v=X[[z[2:] for z in f]].to_numpy()@coef;ratings[n]=v-v.mean()
rr=[]
for i,t in enumerate(X.index):
 stats={s['name']:s for s in teams[t]['stats']};rec=stats.get('overall',{}).get('displayValue');rr.append({'team':t,'rating':float(ratings['2026_no_ap'][i]),'no_ap_rating':float(ratings['2026_ap'][i]),'record':rec,'ap_rank':apr.get(t),'games_used':int(X.loc[t,'gp'])})
for k,rk in [('rating','rank'),('no_ap_rating','no_ap_rank')]:
 for i,r in enumerate(sorted(rr,key=lambda z:-z[k]),1):r[rk]=i
power={'model':'CFB no-AP reference, fixed Oct11 coefficients','model_as_of':'2026-10-19','records_as_of':'2026-10-19','ap_date':ap['date'],'ap_last_updated':ap['lastUpdated'],'method':'No-AP fixed reference coefficients applied to current features, centered across 138 FBS teams. Comparison is separately fitted AP research variant, not subtraction from same fit. Neither is a validated betting edge.','sources':protocol['source_urls']+[audit['standings_url']],'teams':sorted(rr,key=lambda r:r['rank'])};(P/'power_ratings.json').write_text(json.dumps(power,indent=2));print('COMPLETE',len(games),len(rr),'TOP5',[(r['team'],r['rating'],r['record']) for r in power['teams'][:5]],'HASH',hashlib.sha256(raw.encode()).hexdigest())
