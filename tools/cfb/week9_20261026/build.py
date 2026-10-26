import sys,json,pathlib,tempfile,hashlib,datetime
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent
src=(R/'tools/model_cfb_v2/repair_20261011/reference_features.py').read_text();sys.argv=['features',str(R),str(P)]
# Prior seals must be intact before a new seal is issued.
for wk in ['week7_sealed_research','week8_sealed_research']:
 d=R/'tools/model_cfb_v2/repair_20261011' if wk.startswith('week7') else R/'tools/cfb/week8_20261019'
 raw=(d/f'{wk}.json').read_text();expect=(d/f'{wk}.sha256').read_text().split()[0]
 assert hashlib.sha256(raw.encode()).hexdigest()==expect, f'{wk} seal broken'
print('PRIOR SEALS INTACT')
B=pathlib.Path(tempfile.mkdtemp(prefix='cfb9-boxes-'));by={}
for folder in ['tools/cfb/boxscores','tools/cfb/current_inputs_20261016/boxscores','tools/cfb/week8_20261019/boxscores','tools/cfb/week9_20261026/boxscores']:
 for f in (R/folder).glob('*.json'):
  d=json.load(open(f));by[str(d['header']['id'])]=f
for eid,f in by.items():(B/f'boxscore-{eid}.json').symlink_to(f)
now=datetime.datetime.now(datetime.timezone.utc);cutoff=now.isoformat()
current=src.replace("REPO/'tools/cfb/boxscores'",'Path('+repr(str(B))+')').replace('2026-10-12T02:40:00Z',cutoff).replace("pd.Timestamp('2026-10-12')","pd.Timestamp('2026-10-26')")
ns2={};exec(compile(current,'current_features_refit','exec'),ns2)
feat=ns2['feat26'];members=ns2['members'];hist=ns2['hist'];fs=ns2['FEATS'];no=[f for f in fs if f!='d_ap_points'];feat.to_csv(P/'current_team_features.csv')
audit=json.load(open(P/'fetch_audit.json'));rows26=ns2['d26'];assert set(rows26.event_id.astype(str))==set(audit['ids']);assert len(rows26)==2*audit['finals']
assert hist[hist.season==2026].date.max()>=pd.Timestamp('2026-10-24'),'refit hist missing Week8 finals'
models={}
for name,feats,rows in [('2026_no_ap',no,hist),('2026_ap',fs,hist),('historical_no_ap',no,hist[hist.season<2026]),('historical_ap',fs,hist[hist.season<2026])]:
 models[name]=(make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(rows[feats],rows.margin),feats)
slate=json.load(open(P/'sources/week9.json'));games=[];excluded=[]
for e in slate['events']:
 c=e['competitions'][0];assert c['status']['type']['state']=='pre';t={z['homeAway']:z['team']['displayName'] for z in c['competitors']};h,a=t['home'],t['away']
 if h not in members or a not in members:excluded.append({'event_id':e['id'],'name':e['name'],'reason':'not FBS versus FBS'});continue
 vals={f:float(feat.loc[h,f[2:]]-feat.loc[a,f[2:]]) for f in fs};assert np.isfinite(list(vals.values())).all()
 preds={n:float(m.predict(pd.DataFrame([vals])[f])[0]) for n,(m,f) in models.items()}
 book=None
 if c.get('odds'):
  o=c['odds'][0];ho=(o.get('homeTeamOdds') or {});ao=(o.get('awayTeamOdds') or {})
  home_line=None
  if o.get('spread') is not None:
   home_line=float(o['spread'])
   home_fav=ho.get('favorite')
   if home_fav is not None: assert (home_line<0)==bool(home_fav) or home_line==0, f'spread/favorite mismatch {e["name"]}'
  book={'provider':(o.get('provider') or {}).get('name'),'details':o.get('details'),'home_line':home_line,'over_under':o.get('overUnder'),'captured_at':cutoff,'source':'ESPN scoreboard pregame odds at seal time'}
 games.append({'event_id':e['id'],'name':e['name'],'date':c['date'],'home':h,'away':a,'neutral_site':bool(c.get('neutralSite')),'predicted_margin_home':preds,'features':vals,'model_total':None,'injury_adjusted_margin_home':None,'weather_adjusted_margin_home':None,'book':book})
base=json.load(open(R/'tools/model_cfb_v2/repair_20261011/week7_sealed_research.json'))
protocol=dict(base['protocol']);protocol.update({'sealed_at':cutoff,'outcome_holdout':'2026 Week9, Oct27-Nov1; every event verified pregame','purpose':'No-AP reference refit on all completed finals through 2026-10-25 (Week8); AP/recency variants research-only. Specification unchanged; coefficients refit, not retuned against outcomes.','train_cutoff':cutoff,'feature_cutoff':cutoff,'coverage':{'scheduled':len(slate['events']),'scored_fbs_vs_fbs':len(games),'excluded':excluded},'source_urls':[f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week={w}&groups=80&limit=400' for w in range(1,10)],'known_data_gaps':[]})
out={'protocol':protocol,'games':sorted(games,key=lambda g:g['date'])};raw=json.dumps(out,sort_keys=True,indent=2)+'\n';(P/'week9_sealed_research.json').write_text(raw);(P/'week9_sealed_research.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  week9_sealed_research.json\n')
# Selection-time dog-bucket freeze: model side vs book underdog at seal-time line.
freeze={'sealed_at':cutoff,'rule':'bucket hit when model pick equals the selection-time book underdog; derivation-only until prospective grading; closing lines captured later','games':[]}
for g in games:
 pred=g['predicted_margin_home']['2026_no_ap'];mp=g['home'] if pred>0 else g['away']
 bl=(g['book'] or {}).get('home_line');dog=None;hit=None
 if bl is not None and bl!=0:
  dog=g['away'] if bl<0 else g['home'];hit=(mp==dog)
 freeze['games'].append({'event_id':g['event_id'],'name':g['name'],'date':g['date'],'model_pick':mp,'model_margin_home':pred,'book_home_line':bl,'book_underdog':dog,'dog_bucket':hit})
(P/'week9_dog_bucket_freeze.json').write_text(json.dumps(freeze,indent=2))
stand=json.load(open(P/'sources/standings.json'));teams={}
def walk(j):
 for e in j.get('standings',{}).get('entries',[]):teams[e['team']['displayName']]=e
 for c in j.get('children',[]):walk(c)
walk(stand)
X=feat.loc[sorted(members.intersection(feat.index))];assert len(X)==138
ap=next(p for p in json.load(open(R/'tools/model_cfb_v2/ap_poll/ap-2026-week9.json'))['rankings'] if p.get('type')=='ap');apr={r['team']['location']+' '+r['team']['name']:r['current'] for r in ap['ranks']}
ratings={}
for n in ['2026_no_ap','2026_ap']:
 m,f=models[n];coef=m[-1].coef_/m[0].scale_;v=X[[z[2:] for z in f]].to_numpy()@coef;ratings[n]=v-v.mean()
rr=[]
for i,t in enumerate(X.index):
 stats={s['name']:s for s in teams[t]['stats']};rec=stats.get('overall',{}).get('displayValue');rr.append({'team':t,'rating':float(ratings['2026_no_ap'][i]),'ap_model_rating':float(ratings['2026_ap'][i]),'record':rec,'ap_rank':apr.get(t),'games_used':int(X.loc[t,'gp'])})
for k,rk in [('rating','rank'),('ap_model_rating','ap_model_rank')]:
 for i,r in enumerate(sorted(rr,key=lambda z:-z[k]),1):r[rk]=i
power={'model':'CFB no-AP reference, refit on finals through Week8 (2026-10-25)','model_as_of':'2026-10-26','records_as_of':'2026-10-26','ap_date':ap['date'],'ap_last_updated':ap['lastUpdated'],'method':'No-AP reference specification refit on all completed finals through Week8, centered across 138 FBS teams. Comparison is separately fitted AP research variant, not subtraction from same fit. Neither is a validated betting edge.','sources':protocol['source_urls']+[audit['standings_url']],'teams':sorted(rr,key=lambda r:r['rank'])};(P/'power_ratings.json').write_text(json.dumps(power,indent=2));print('COMPLETE',len(games),len(rr),'TOP5',[(r['team'],round(r['rating'],3),r['record']) for r in power['teams'][:5]],'HASH',hashlib.sha256(raw.encode()).hexdigest())
