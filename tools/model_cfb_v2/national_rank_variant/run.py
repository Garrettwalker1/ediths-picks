from pathlib import Path
import sys,json,numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
REPO=Path(sys.argv[1]);OUT=Path(sys.argv[2]);OUT.mkdir(exist_ok=True,parents=True);sys.argv=['candidate',str(REPO),str(OUT)]
source=(REPO/'tools/cfb/29-score_week6_initial.py').read_text().split('# ---- Week 6 full slate')[0]
exec(compile(source,'v2.2setup','exec'))
# Statistical national ranks are reconstructed from the free game corpus, not copied from end-season tables.
# Use season-specific FBS membership and only games before that date. Competition ranks allow ties.
fbs={int(k):v for k,v in json.load(open(OUT/'fbs-names.json')).items()}
raw=tg[tg.home_away!='asof'].copy()
opp=raw[['event_id','team','turnovers_forced']].rename(columns={'team':'opponent','turnovers_forced':'turnovers_lost'})
raw=raw.merge(opp,on=['event_id','opponent'],how='left');raw['turnover_margin']=raw.turnovers_forced-raw.turnovers_lost
cols={'pass_off':('pass_yds_for',False),'rush_off':('rush_yds_for',False),'pass_def':('pass_yds_allowed',True),'rush_def':('rush_yds_allowed',True),'turnover_margin':('turnover_margin',False),'score_off':('points_for',False),'score_def':('points_allowed',True),'total_off':('total_yds_for',False),'total_def':('total_yds_allowed',True)}
# Exclude known missing-stat zero rows from rank calculation; never treat missing as elite defense.
raw=raw[(raw.total_yds_for>0)&(raw.total_yds_allowed>0)]
snap=[]
for yr in range(2022,2027):
 dat=raw[raw.season==yr];members=fbs[yr];dates=sorted(set(tg[tg.season==yr].date))
 for dt in dates:
  q=dat[dat.date<dt].groupby('team').agg(**{k:(v[0],'mean') for k,v in cols.items()},gp=('event_id','size'))
  q=q.reindex(members);n=q.gp.notna().sum()
  for k,(_,asc) in cols.items():
   q[k+'_rank']=q[k].rank(method='min',ascending=asc)
   q[k+'_pct']=(n-q[k+'_rank'])/max(1,n-1)
  q['rank_date']=dt;q['season']=yr;q['rank_universe']=n;q['team']=q.index
  snap.append(q.reset_index(drop=True))
ranks=pd.concat(snap,ignore_index=True);ranks.to_csv(OUT/'national_rank_snapshots.csv',index=False)
# Match exact game-day pregame snapshot. Missing current-season ranks at openers remain null.
rcols=[k+'_pct' for k in cols]
rr=ranks.rename(columns={'rank_date':'date'})[['team','date','season']+rcols]
gmrank=gm.copy();gmrank['date']=pd.to_datetime(gmrank.date,utc=True).dt.tz_localize(None).dt.normalize()
for side in ['h','a']:
 r=rr.rename(columns={'team':side+'_team',**{c:side+'_'+c for c in rcols}})
 gmrank=gmrank.merge(r,on=[side+'_team','date','season'],how='left',validate='many_to_one')
for c in rcols:gmrank['d_'+c]=gmrank['h_'+c]-gmrank['a_'+c]
allrank=['d_'+c for c in rcols]
sub=gmrank[gmrank.season.between(2022,2025)].dropna(subset=FEATS+allrank+['margin']).copy();tr=sub[sub.season<=2023];va=sub[sub.season==2024];te=sub[sub.season==2025]
print('same row train/val/test',len(tr),len(va),len(te))
def metrics(y,p):return {'mae':float(np.mean(abs(y-p))),'rmse':float(np.sqrt(np.mean((y-p)**2))),'winner_accuracy':float(np.mean(np.sign(y)==np.sign(p))),'n':len(y)}
sets={'v2.2':[], 'pass_def':['pass_def'],'rush_def':['rush_def'],'turnover_margin':['turnover_margin'],'pass_off':['pass_off'],'rush_off':['rush_off'],'requested_five':['pass_def','rush_def','turnover_margin','pass_off','rush_off'],'all_nine':list(cols)}
results={};models={};vp={}
for name,cs in sets.items():
 fs=FEATS+['d_'+c+'_pct' for c in cs];m=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(tr[fs],tr.margin);models[name]=(m,fs);v=m.predict(va[fs]);vp[name]=v;results[name]={'features_added':cs,'validation':metrics(va.margin.to_numpy(),v)}
# Choose only on validation, before looking at 2025. Primary MAE, winners secondary.
selected=min(sets,key=lambda k:results[k]['validation']['mae']);print('selected on validation',selected);json.dump({'selected':selected,'results':results},open(OUT/'validation_selection.json','w'),indent=2)
for name,(m,fs) in models.items():
 t=m.predict(te[fs]);results[name]['historical_2025']=metrics(te.margin.to_numpy(),t);te[name]=t
base=te['v2.2'].to_numpy();rng=np.random.default_rng(60109)
for name in sets:
 d=abs(te.margin.to_numpy()-te[name].to_numpy())-abs(te.margin.to_numpy()-base)
 boots=np.array([d[rng.integers(len(d),size=len(d))].mean() for _ in range(5000)])
 results[name]['mae_delta_vs_v2.2']={'mean':float(d.mean()),'ci95':np.quantile(boots,[.025,.975]).tolist(),'fraction_better':float(np.mean(boots<0))}
books=pd.concat([pd.read_csv(OUT/f'betting_{yr}.csv') for yr in [2024,2025]]);books['event_id']=books.game_id.astype(str);te['event_id']=te.event_id.astype(str)
b=te.merge(books[['event_id','home_team_spread','odds_source']],on='event_id',how='inner');b=b[b.home_team_spread.notna()];bookpred=-b.home_team_spread.to_numpy();book={'source':'Sportsdataverse ESPN closing-line archive, not FanDuel','metrics':metrics(b.margin.to_numpy(),bookpred),'matched_n':len(b),'model_same_rows':{k:metrics(b.margin.to_numpy(),b[k].to_numpy()) for k in sets},'odds_sources':b.odds_source.value_counts().to_dict()}
for name in sets:
 print(name,results[name])
print('BOOK',book)
res={'protocol':'Train2022-23, validation2024 selection only, 2025 historical comparison; 2025 was previously examined for v2.2 so not a new untouched test. Ridge alpha10, same rows; no book inputs. All national ranks computed from strictly earlier same-season games, FBS universe from ESPN group80. Known missing-stat zero rows omitted. Season openers excluded when no ranks.','selected':selected,'results':results,'book':book,'sources':['https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard','https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2025/types/2/groups/80/teams?limit=1000','https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_betting']}
json.dump(res,open(OUT/'results.json','w'),indent=2);te.to_csv(OUT/'test_predictions.csv',index=False)
# Forward 2026 check, fit using historical games only, frozen initial predictions remain immutable.
models_live={}
for name in ['pass_def','requested_five']:
 cs=sets[name];fs=FEATS+['d_'+c+'_pct' for c in cs];m=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(sub[fs],sub.margin);models_live[name]=(m,fs)
# Targeted rank lookup at each game's date, excludes all outcomes on that day.
def features_at(team,dt):
 d=pd.Timestamp(dt).tz_localize(None).normalize()
 q=tg[(tg.team==team)&(tg.season==2026)&(tg.date<=d)].sort_values('date')
 # For observed game date, pregame shifted row; for upcoming use synthetic as-of row.
 row=q.iloc[-1].copy() if len(q) else None
 if row is not None:
  for f in FEATS:
   c=f[2:]
   if pd.isna(row[c]) and team in s25i.index:row[c]=s25i.loc[team,c]
 rr=ranks[(ranks.team==team)&(ranks.season==2026)&(ranks.rank_date<=d)].sort_values('rank_date')
 rank=rr.iloc[-1] if len(rr) else None
 return row,rank

def make_feats(g):
 dt=g['date'];h,hr=features_at(g['home'],dt);a,ar=features_at(g['away'],dt)
 if h is None or a is None or hr is None or ar is None:return None
 vals={}
 for f in FEATS:
  c=f[2:];vals[f]=h[c]-a[c]
 for c in rcols:vals['d_'+c]=hr[c]-ar[c]
 if not np.isfinite(list(vals.values())).all():return None
 return vals
# Feature_at for historical observed dates must exactly match its own game shifted row rather than nearest later row.
forward=[]
for path in sorted((REPO/'tools/cfb').glob('*frozen_results.json')):
 d=json.load(open(path))
 for g in d.get('games',[]):
  if not g.get('home') or not g.get('away'):continue
  rows=tg[(tg.season==2026)&(tg.team==g['home'])&(tg.event_id.astype(str)==str(g['event_id']))]
  if rows.empty:continue
  b=dict(g);b['date']=rows.iloc[0]['date'].isoformat();v=make_feats(b)
  if v is None:continue
  forward.append({'event_id':g['event_id'],'game':g,'features':v})
print('forward items',len(forward))
fr=[]
for x in forward:
 g=x['game'];v=x['features'];fr.append({'event_id':x['event_id'],'actual':g['actual_margin_home'],'frozen_v2_2':g['frozen_predicted_margin_home'],'book_home_spread':g.get('book_home_spread'),**{k:float(m.predict(pd.DataFrame([v])[fs])[0]) for k,(m,fs) in models_live.items()}})
fdf=pd.DataFrame(fr)
if len(fdf):
 print('FORWARD', {k:metrics(fdf.actual.to_numpy(),fdf[k].to_numpy()) for k in ['frozen_v2_2','pass_def','requested_five']})
 res['forward2026_retrospective_candidate']={k:metrics(fdf.actual.to_numpy(),fdf[k].to_numpy()) for k in ['frozen_v2_2','pass_def','requested_five']}
 fdf.to_csv(OUT/'forward2026_predictions.csv',index=False)
# Export current ranks and current candidate margins for the full Week6 slate, excluding started games.
board=json.load(open(REPO/'tools/cfb/29-cfb_board_2026_week6_initial_v2_2.json'));cand=[]
for g in board['games']:
 v=make_feats(g)
 if g.get('book_frozen_pregame') or v is None:continue
 pred={name:float(m.predict(pd.DataFrame([v])[fs])[0]) for name,(m,fs) in models_live.items()}
 hr=ranks[(ranks.team==g['home'])&(ranks.season==2026)].sort_values('rank_date').iloc[-1]
 ar=ranks[(ranks.team==g['away'])&(ranks.season==2026)].sort_values('rank_date').iloc[-1]
 cand.append({'event_id':g['event_id'],'name':g['name'],'baseline_margin_home':g['predicted_margin_home'],'candidate_margins_home':pred,'home_ranks':{k:float(hr[k+'_rank']) for k in cols},'away_ranks':{k:float(ar[k+'_rank']) for k in cols},'rank_universe':int(hr.rank_universe),'date':g['date']})
json.dump({'label':'National-rank candidate variants, not adopted; v2.2 remains current.','generated_at':'2026-10-09T07:33:00-05:00','categories':list(cols),'rank_definition':'Season-to-date yards per game / net turnovers per game; minimum competition ranks (ties share rank), computed from ESPN completed boxscores through Week5, FBS-only. Not official NCAA ranks.','validation':res,'games':cand},open(OUT/'week6_candidate.json','w'),indent=2)
json.dump(forward,open(OUT/'forward_rows.json','w'),default=str)
print('current candidate games',len(cand))
