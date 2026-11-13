"""Owner-requested season-only NFL version. No claimed accuracy validation."""
import pathlib,json,datetime,hashlib,collections
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
P=pathlib.Path(__file__).parent;R=pathlib.Path('/tmp/edith');S=P/'sources';now=datetime.datetime.now(datetime.timezone.utc);G=pd.read_csv(S/'games.csv',dtype={'espn':str},low_memory=False);G=G[(G.game_type=='REG')&G.season.between(2020,2026)].copy();G['espn']=G.espn.str.replace('.0','',regex=False)
parts=[];sources=[]
for yr in range(2020,2027):
 files=list((R/'tools/nflverse').glob(f'*-player_stats_{yr}.csv')) if yr<2025 else (sorted((R/'tools/nflverse').glob('*-stats_player_week_2025_part*.csv'))if yr==2025 else[S/'player_stats_2026.csv'])
 assert files,yr
 for f in files:
  x=pd.read_csv(f,low_memory=False);x=x[x.season_type=='REG'].copy();x.rename(columns={'recent_team':'team','interceptions':'passing_interceptions'},inplace=True);parts.append(x);sources.append(dict(file=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),season=yr))
D=pd.concat(parts,ignore_index=True);D.team=D.team.replace({'WSH':'WAS','STL':'LA','SD':'LAC','OAK':'LV'});assert not D.duplicated(['season','week','team','player_id']).any()
cols=['completions','attempts','passing_yards','passing_tds','passing_interceptions','carries','rushing_yards','rushing_tds','receptions','receiving_yards','receiving_tds'];A=D.groupby(['season','week','team'])[cols].sum();final=G[G.home_score.notna()&G.away_score.notna()].sort_values(['gameday','game_id']);games=final.to_dict('records');hist=collections.defaultdict(list)
for g in games:
 for side in ['home','away']:hist[g['season'],g[side+'_team']].append(g)
metrics=['pf','pa','yf','ya','completion_rate','pass_ypa','pass_td_rate','pass_int_rate','rush_ypa','rush_td_rate','rec_ypc','rec_td_rate','record_strength','schedule_strength','opponent_score_rating'];cache={};prov=[];missing=[]
def context(yr,day):
 key=(yr,day)
 if key in cache:return cache[key]
 prior=[g for g in games if g['season']==yr and g['gameday']<day];names=sorted(set(G[G.season==yr].home_team)|set(G[G.season==yr].away_team));ix={t:i for i,t in enumerate(names)};n=len(names);C=np.eye(n)*2;b=np.ones(n);M=np.zeros((len(prior),n+1));y=np.zeros(len(prior));opp=collections.defaultdict(list)
 for i,g in enumerate(prior):
  h,a=ix[g['home_team']],ix[g['away_team']];C[h,h]+=1;C[a,a]+=1;C[h,a]-=1;C[a,h]-=1;w=np.sign(g['home_score']-g['away_score'])/2;b[h]+=w;b[a]-=w;opp[h].append(a);opp[a].append(h);M[i,h]=1;M[i,a]=-1;M[i,n]=0 if g['location']=='Neutral'else 1;y[i]=g['home_score']-g['away_score']
 col=np.linalg.solve(C,b);r=np.linalg.solve(M.T@M+20*np.eye(n+1),M.T@y);r[:n]-=r[:n].mean();v={}
 for tm in names:
  hs=[g for g in hist[yr,tm]if g['gameday']<day]
  if len(hs)<3:continue
  ps=[];pf=[];pa=[];yf=[];ya=[];bad=False
  for g in hs:
   home=g['home_team']==tm;ot=g['away_team']if home else g['home_team'];k=(yr,g['week'],tm);ok=(yr,g['week'],ot)
   if k not in A.index or ok not in A.index:bad=True;break
   z,o=A.loc[k],A.loc[ok];ps.append(z);pf.append(g['home_score']if home else g['away_score']);pa.append(g['away_score']if home else g['home_score']);yf.append(z.passing_yards+z.rushing_yards);ya.append(o.passing_yards+o.rushing_yards)
  if bad:continue
  pp=pd.DataFrame(ps).sum();at,ra,rc=pp.attempts,pp.carries,pp.receptions
  if min(at,ra,rc)<=0:continue
  j=ix[tm];vv=dict(pf=float(np.mean(pf)),pa=float(np.mean(pa)),yf=float(np.mean(yf)),ya=float(np.mean(ya)),completion_rate=pp.completions/at,pass_ypa=pp.passing_yards/at,pass_td_rate=pp.passing_tds/at,pass_int_rate=pp.passing_interceptions/at,rush_ypa=pp.rushing_yards/ra,rush_td_rate=pp.rushing_tds/ra,rec_ypc=pp.receiving_yards/rc,rec_td_rate=pp.receiving_tds/rc,record_strength=col[j],schedule_strength=col[opp[j]].mean(),opponent_score_rating=r[j]);v[tm]=(vv,[g['game_id']for g in hs])
 cache[key]=v;return v
def features(g,day):
 c=context(g['season'],day);h,a=g['home_team'],g['away_team']
 if h not in c or a not in c:return None
 hv,hi=c[h];av,ai=c[a];z={'d_'+m:float(hv[m]-av[m])for m in metrics};z['home_field']=0. if g['location']=='Neutral'else 1.;assert np.isfinite(list(z.values())).all();prov.append(dict(game_id=g['game_id'],cutoff_date=day,home_history=hi,away_history=ai,context_games=[x['game_id']for x in games if x['season']==g['season']and x['gameday']<day]));return z
train=[]
for g in games:
 z=features(g,g['gameday'])
 if z is None:missing.append(g['game_id']);continue
 train.append(dict(z,game_id=g['game_id'],season=g['season'],date=g['gameday'],home=g['home_team'],away=g['away_team'],margin=g['home_score']-g['away_score']))
T=pd.DataFrame(train);fs=['d_'+m for m in metrics]+['home_field'];X=T[fs].to_numpy();y=T.margin.to_numpy();model=make_pipeline(StandardScaler(),Ridge(alpha=10,fit_intercept=False)).fit(np.vstack([X,-X]),np.r_[y,-y]);slate=json.load(open(S/'week10.json'));lookup={str(e['id']):e for e in slate['events']};future=[]
for g in G[(G.season==2026)&(G.week==10)].to_dict('records'):
 eid=g['espn'];e=lookup[eid];c=e['competitions'][0]
 if c['status']['type']['state']!='pre':continue
 assert g['home_score']!=g['home_score'];teams={t['homeAway']:t['team']for t in c['competitors']};z=features(g,now.date().isoformat());assert z,g['game_id'];x=np.array([[z[k]for k in fs]]);m=float(model.predict(x)[0]);assert abs(m+float(model.predict(-x)[0]))<1e-10
 future.append(dict(event_id=eid,game_id=g['game_id'],season=2026,date=c['date'],home=teams['home']['displayName'],away=teams['away']['displayName'],home_abbr=g['home_team'],away_abbr=g['away_team'],raw_margin_home=m,display_margin_home=round(m*2)/2,features=z,home_gp=len(context(2026,now.date().isoformat())[g['home_team']][1]),away_gp=len(context(2026,now.date().isoformat())[g['away_team']][1]),forecast_status='season_only_stats_forecast_injury_adjustment_unavailable',injury_numeric_adjustment=None))
meta=dict(version='NFL-current-season-SOS-record-player-v1-owner-requested',generated_at=now.isoformat(),status='Owner-requested version; accuracy unvalidated; injury adjustment unavailable',features=fs,training_rows=len(T),training_rows_by_season=T.groupby('season').size().to_dict(),training='Past-only same-season REG games; min3 earlier games each team; 2020-26; mirrored StandardScaler+Ridge alpha10, no intercept',record_strength_definition='Same-season Colley W/L with ties counted half, not ESPN proprietary SOR',schedule_strength_definition='Mean Colley rating of opponents already faced',player_inputs='Same-season stable-ID player passing/rushing/receiving stats aggregated to team rates; gross passing+rushing yards, not net offense. Realized historical participation, NOT confirmed available-player projection.',preseason_talent_inputs=False,prior_season_stats_inputs=False,odds_inputs=False,injury_numeric_inputs=False,injury_limitation='No numerical injury or replacement adjustment. Current personnel not yet reconciled.',source_cutoff='Completed NFL REG games and player production through Nov12; future Nov15-16 games only',scaler_mean=model[0].mean_.tolist(),scaler_scale=model[0].scale_.tolist(),coefficients=model[1].coef_.tolist())
for name,obj in [('current_forecasts.json',dict(metadata=meta,games=future)),('training_features.json',train),('feature_provenance.json',prov),('historical_input_manifest.json',sources),('training_exclusions.json',missing)]: (P/name).write_text(json.dumps(obj,indent=2)+'\n')
print('training',len(T),'future',len(future));print([(g['away_abbr'],g['home_abbr'],g['display_margin_home'])for g in future])
