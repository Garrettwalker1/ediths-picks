from pathlib import Path
import pandas as pd,numpy as np,json,datetime,requests,hashlib,joblib,sys
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error,mean_squared_error
P=Path('/tmp/prop-matchup/v2');R=Path('/tmp/edith-oct28');AL={'WAS':'WSH','LAR':'LA','OAK':'LV','SD':'LAC','STL':'LA'}
manifest=[];frames=[]
for year in range(2021,2027):
 path=Path('/tmp/td-matchup/cache')/f'stats_{year}.csv'
 if not path.exists():path=R/'tools/player_projection_cache'/f'stats_{year}.csv'
 if year==2026:
  url=f'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year}.csv';path=P/'stats_2026.csv';q=requests.get(url,timeout=90);q.raise_for_status();path.write_bytes(q.content);manifest.append({'url':url,'sha256':hashlib.sha256(q.content).hexdigest(),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 d=pd.read_csv(path,low_memory=False);d=d[d.season_type.eq('REG')&d.position.isin(['QB','RB','WR','TE'])];frames.append(d)
d=pd.concat(frames,ignore_index=True);d.team=d.team.replace(AL);d.opponent_team=d.opponent_team.replace(AL);d=d.sort_values(['player_id','season','week'])
url='https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv';q=requests.get(url,timeout=90);q.raise_for_status();(P/'schedules.csv').write_bytes(q.content);manifest.append({'url':url,'sha256':hashlib.sha256(q.content).hexdigest(),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()});games=pd.read_csv(P/'schedules.csv');home=dict(zip(games.game_id,games.home_team.replace(AL)))
base={'receiving_yards':['receiving_yards','targets','receptions','receiving_air_yards','target_share','air_yards_share','wopr'],'rushing_yards':['rushing_yards','carries'],'receptions':['receptions','targets'],'passing_yards':['passing_yards','attempts','completions','passing_air_yards','sacks_suffered']}
# Team-position game totals. Opponent allowances use only earlier current-season games.
metrics=['receiving_yards','targets','receptions','receiving_air_yards','rushing_yards','carries','passing_yards','attempts','completions','sacks_suffered','passing_air_yards'];tot=d.groupby(['season','week','game_id','team','opponent_team','position'],as_index=False)[metrics].sum()
hist={pid:g for pid,g in d.groupby('player_id')};teamhist={(y,t):g for (y,t),g in d.groupby(['season','team'])};defhist={(y,t,p):g for (y,t,p),g in tot.groupby(['season','opponent_team','position'])}
features={};rows=[];future=[]
def construct(pid,h,y,w,t,opp,is_home):
 h=h[(h.season<y)|((h.season==y)&(h.week<w))];cur=h[h.season.eq(y)&h.team.eq(t)]
 if len(h)<3 or len(cur)<2:return None
 pos=h.position.iloc[-1];de=defhist.get((y,opp,pos));allcur=teamhist.get((y,t));de=de[de.week<w] if de is not None else None;allcur=allcur[allcur.week<w] if allcur is not None else None
 if de is None or de.game_id.nunique()<2 or allcur is None:return None
 x={'is_home':is_home,'prior_current_games':len(cur),'opp_sample_games':de.game_id.nunique()}
 for c in metrics+['target_share','air_yards_share','wopr']:
  for n in [3,6]:x[c+'_r'+str(n)]=float(h[c].tail(n).mean())
  x[c+'_current4']=float(cur[c].tail(4).mean())
 for c in ['carries','targets','attempts']:x[c+'_share']=float(cur[c].sum()/max(1,allcur[c].sum()))
 for c in metrics:x['opp_'+c+'_allowed']=float(de[c].mean())
 for p in ['QB','RB','TE']:x['pos_'+p]=int(pos==p)
 return x
year=int(sys.argv[1]) if len(sys.argv)>1 else None
for pid,g in (hist.items() if year else []):
 for a in g[(g.season.eq(year) if year else g.season.le(2025))&g.week.ge(3)].itertuples():
  x=construct(pid,g,a.season,a.week,a.team,a.opponent_team,int(home.get(a.game_id)==a.team))
  if x:rows.append({'player_id':pid,'player':a.player_display_name,'game_id':a.game_id,'season':a.season,'week':a.week,'position':a.position,**{c:getattr(a,c) for c in base},**x})
if year:
 pd.DataFrame(rows).to_pickle(P/f'rows_{year}.pkl');print(year,len(rows),flush=True);sys.exit(0)
# Forward roster is history-derived, not verified current roster/availability; hold numbers in research until checked.
for game in games[games.season.eq(2026)&games.week.eq(8)&games.gameday.ge('2026-10-30')].itertuples():
 for t,opp in [(AL.get(game.home_team,game.home_team),AL.get(game.away_team,game.away_team)),(AL.get(game.away_team,game.away_team),AL.get(game.home_team,game.home_team))]:
  for pid,g in hist.items():
   a=g.iloc[-1]
   if a.season!=2026 or a.team!=t:continue
   x=construct(pid,g,2026,8,t,opp,int(t==AL.get(game.home_team,game.home_team)))
   if x:future.append({'player_id':pid,'player':a.player_display_name,'position':a.position,'team':t,'opponent':opp,'game_id':game.game_id,'last_played_week':int(a.week),'status':'UNVERIFIED_CURRENT_ROSTER_ROLE_AND_AVAILABILITY','features':x})
z=pd.concat([pd.read_pickle(P/f'rows_{y}.pkl') for y in range(2021,2026)],ignore_index=True);f=pd.DataFrame([{**{k:v for k,v in a.items() if k!='features'},**a['features']} for a in future]);result={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Research only. Train2021-23, select alpha2024;2025 seen diagnostic. Conditional played-player sample. Forward current-team inferred from latest stats, NOT verified roster/availability. No injury redistribution.','sources':manifest,'targets':{}};out=[]
for target,raw in base.items():
 positions=['QB'] if target=='passing_yards' else (['RB'] if target=='rushing_yards' else ['RB','WR','TE']);a=z[z.position.isin(positions)].copy();ff=f[f.position.isin(positions)].copy()
 old=[c+'_r'+str(n) for c in raw for n in [3,6]];new=old+[c+'_current4' for c in raw]+['carries_share','targets_share','attempts_share','is_home','prior_current_games','opp_sample_games']+['opp_'+c+'_allowed' for c in raw if c in metrics and c!='passing_air_yards']+['pos_QB','pos_RB','pos_TE'];a=a.dropna(subset=new);ff=ff.dropna(subset=new);tr=a.season.le(2023);va=a.season.eq(2024);te=a.season.eq(2025);rr={}
 for label,fs in [('rolling_comparator',old),('usage_stat_matchup',new)]:
  candidates=[]
  for alpha in [1,10,100]:
   m=make_pipeline(StandardScaler(),Ridge(alpha=alpha)).fit(a.loc[tr,fs],a.loc[tr,target]);pred=np.maximum(0,m.predict(a.loc[va,fs]));candidates.append((mean_absolute_error(a.loc[va,target],pred),alpha,m))
  _,alpha,m=min(candidates,key=lambda x:x[0]);rr[label]={'alpha':alpha,'features':fs}
  for name,mask in [('validation2024',va),('seen2025',te)]:
   pred=np.maximum(0,m.predict(a.loc[mask,fs]));err=a.loc[mask,target]-pred;a.loc[mask,label]=pred;rr[label][name]={'n':int(mask.sum()),'MAE':mean_absolute_error(a.loc[mask,target],pred),'RMSE':float(np.sqrt(mean_squared_error(a.loc[mask,target],pred)))}
  residual=a.loc[va,target]-a.loc[va,label];bounds=np.quantile(residual,[.1,.9]);pp=np.maximum(0,m.predict(ff[fs]));rr[label]['validation_residual_quantiles_10_90']=bounds.tolist();rr[label]['seen2025_interval_coverage']=float(((a.loc[te,target]>=np.maximum(0,a.loc[te,label]+bounds[0]))&(a.loc[te,target]<=a.loc[te,label]+bounds[1])).mean())
  for idx,pred in zip(ff.index,pp):
   rec=future[idx].copy();rec.pop('features');out.append({**rec,'stat':target,'model':label,'unrounded_mean':float(pred),'display_mean':round(float(pred)*2)/2,'interval80':[float(max(0,pred+bounds[0])),float(max(0,pred+bounds[1]))],'interval_note':'2024 residual quantiles, marginal only; not conditional player-specific guarantee'})
  joblib.dump(m,P/f'{target}_{label}.joblib')
 a.to_pickle(P/f'{target}_paired.pkl');delta=(a.loc[te,'usage_stat_matchup']-a.loc[te,target]).abs()-(a.loc[te,'rolling_comparator']-a.loc[te,target]).abs();cl=a.loc[te,['game_id']].assign(delta=delta).groupby('game_id').delta.agg(['sum','size']);rng=np.random.default_rng(931);boot=[]
 for _ in range(2000):
  q=cl.iloc[rng.integers(0,len(cl),len(cl))];boot.append(q['sum'].sum()/q['size'].sum())
 rr['paired_game_cluster_MAE_delta_CI95']=np.quantile(boot,[.025,.975]).tolist();result['targets'][target]=rr;print(target,json.dumps(rr),flush=True)
(P/'diagnostics.json').write_text(json.dumps(result,indent=2));(P/'forward_unverified.json').write_text(json.dumps({'research_only':True,'withheld_from_live_predictions':True,'source_max_week2026':int(d[d.season.eq(2026)].week.max()),'rows':out},indent=2));print('forward',len(out),flush=True)
