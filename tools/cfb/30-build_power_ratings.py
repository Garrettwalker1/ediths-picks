import sys,json,numpy as np,pandas as pd
from pathlib import Path
repo=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2];src=(repo/'tools/cfb/29-score_week6_initial.py').read_text().split('# ---- Week 6 full slate from ESPN scoreboards ----')[0]
sys.argv=['ratings',str(repo),'/tmp/ratings-work'];ns={};exec(compile(src,'model_feature_extract','exec'),ns)
f=ns['feat26'];feats=ns['FEATS'];model=ns['model'];coef=model[-1].coef_/model[0].scale_
X=f[[x[2:] for x in feats]].copy();valid=X.notna().all(axis=1);X=X[valid]
board=json.load(open(repo/'tools/cfb/29-cfb_board_2026_week6_initial_v2_2.json'))
for g in board['games']:
 if g.get('book_frozen_pregame'):continue
 v=(X.loc[g['home']]-X.loc[g['away']]).to_numpy();pv=float(model.predict(pd.DataFrame([v],columns=feats))[0]);assert round(pv,1)==g['predicted_margin_home'],(g['name'],pv,g['predicted_margin_home'])
# Records live separately; ratings strictly retain current Week 6 model inputs.
stand=json.load(open(repo/'tools/cfb/29-cfb_standings_20261008.json'));teams={}
def walk(j):
 for e in j.get('standings',{}).get('entries',[]):teams[e['team']['displayName']]=e
 for c in j.get('children',[]):walk(c)
walk(stand)
print('FBS standings teams',len(teams),'model teams',len(X));
# Restrict to current FBS membership rather than the historical model corpus.
X=X.loc[X.index.intersection(teams)];raw=X.to_numpy()@coef;rating=raw-raw.mean();ap_idx=feats.index('d_ap_points');noapraw=raw-X.ap_points.to_numpy()*coef[ap_idx];noap=noapraw-noapraw.mean()
ap=ns['cur_ap'];apr={ns['ap_team_name'](r['team']):r['current'] for r in ap['ranks']}
rows=[]
for i,t in enumerate(X.index):
 e=teams[t];stats={s['name']:s for s in e['stats']};record=stats.get('overall',{}).get('displayValue')
 if not record:record=f"{stats.get('wins',{}).get('value','?'):g}-{stats.get('losses',{}).get('value','?'):g}"
 rows.append({'team':t,'rating':float(rating[i]),'no_ap_rating':float(noap[i]),'record':record,'ap_rank':apr.get(t),'games_used':int(X.loc[t,'gp'])})
for field,rank in [('rating','rank'),('no_ap_rating','no_ap_rank')]:
 for i,r in enumerate(sorted(rows,key=lambda r:-r[field]),1):r[rank]=i
out={'model':'cfb-gameline-v2.2','model_as_of':'2026-10-04','records_as_of':'2026-10-08','ap_date':ap['date'],'method':'Linear team-feature contribution, centered on the mean of current FBS teams. Rating differences give model margin with the fitted home intercept removed. No-AP comparison removes only the AP points contribution from the same fitted model; it is not a separately trained or validated model.','fit_intercept':float(model[-1].intercept_-np.dot(model[0].mean_,coef)),'sources':['https://site.api.espn.com/apis/v2/sports/football/college-football/standings?season=2026&type=0&level=3'],'teams':sorted(rows,key=lambda r:r['rank'])}
(repo/'tools/cfb/29-cfb_power_ratings_2026_week6.json').write_text(json.dumps(out,indent=2)+'\n');print('TOP25',[(r['rank'],r['team'],round(r['rating'],1),r['record'],r['ap_rank']) for r in out['teams'][:25]]);print('missing FBS',set(teams)-set(X.index))
