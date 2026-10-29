import pandas as pd,numpy as np,json,pathlib,requests,datetime,hashlib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,log_loss
import joblib
P=pathlib.Path('/tmp/td-matchup');R=pathlib.Path('/tmp/edith-oct28');OUT=P/'out'; AL={'WAS':'WSH','LAR':'LA','OAK':'LV','SD':'LAC','STL':'LA'}
cols=['game_id','season','week','season_type','posteam','defteam','yardline_100','play_type','rusher_player_id','receiver_player_id','epa','rush_touchdown','pass_touchdown','two_point_attempt']
pieces=[];rzs=[];stats=[]
for y in range(2021,2027):
 p=pd.read_parquet(P/f'cache/pbp_{y}.parquet',columns=cols);p=p[(p.season_type=='REG')&p.play_type.isin(['run','pass'])&(p.two_point_attempt!=1)];p.posteam=p.posteam.replace(AL);p.defteam=p.defteam.replace(AL)
 t=p.groupby(['season','week','game_id','posteam','defteam'],as_index=False).agg(plays=('epa','size'),epa=('epa','sum'),rush_td=('rush_touchdown','sum'),pass_td=('pass_touchdown','sum'))
 pieces.append(t)
 for typ,pid,play in [('carry','rusher_player_id','run'),('target','receiver_player_id','pass')]:
  z=p[(p.play_type==play)&p[pid].notna()].copy();z['rz']=z.yardline_100.le(20).astype(int);z['gl']=z.yardline_100.le(5).astype(int);a=z.groupby(['game_id',pid]).agg(**{typ+'_rz':('rz','sum'),typ+'_gl':('gl','sum')}).reset_index().rename(columns={pid:'player_id'});rzs.append(a)
 sp=R/f'tools/player_projection_cache/stats_{y}.csv'
 if not sp.exists():
  sp=P/f'cache/stats_{y}.csv'
  if not sp.exists():rr=requests.get(f'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{y}.csv');rr.raise_for_status();sp.write_text(rr.text)
 d=pd.read_csv(sp,low_memory=False);d=d[(d.season_type=='REG')&d.position.isin(['QB','RB','WR','TE'])];stats.append(d)
 print('read',y,flush=True)
team=pd.concat(pieces,ignore_index=True);d=pd.concat(stats,ignore_index=True).sort_values(['player_id','season','week']);d.team=d.team.replace(AL);d.opponent_team=d.opponent_team.replace(AL);rz=pd.concat(rzs).groupby(['game_id','player_id'],as_index=False).sum(numeric_only=True);d=d.merge(rz,on=['game_id','player_id'],how='left');rzcols=['carry_rz','carry_gl','target_rz','target_gl'];d[rzcols]=d[rzcols].fillna(0);d['tds']=d.rushing_tds.fillna(0)+d.receiving_tds.fillna(0);d['touch']=d.carries.fillna(0)+d.targets.fillna(0);d['y']=(d.tds>0).astype(int)
# Strict within-season pregame team offense/defense ranks, no full-season fill.
teamfeatures={}
for year in range(2021,2027):
 for w in range(3,19):
  z=team[(team.season==year)&(team.week<w)]
  off=z.groupby('posteam').agg(epa=('epa','sum'),plays=('plays','sum'),rush_td=('rush_td','sum'),pass_td=('pass_td','sum'),gp=('game_id','nunique'))
  de=z.groupby('defteam').agg(epa=('epa','sum'),plays=('plays','sum'),rush_td=('rush_td','sum'),pass_td=('pass_td','sum'),gp=('game_id','nunique'))
  for frame in [off,de]:
   frame['epa_rate']=frame.epa/frame.plays;frame['rush_rate']=frame.rush_td/frame.gp;frame['pass_rate']=frame.pass_td/frame.gp
  for t in off.index:
   teamfeatures[(year,w,t)]={**{'off_'+c:float(off[c].rank(pct=True)[t]) for c in ['epa_rate','rush_rate','pass_rate']},**{'def_'+c:float(de[c].rank(pct=True)[t]) for c in ['epa_rate','rush_rate','pass_rate']},'off_epa_rank':int(off.epa_rate.rank(ascending=False,method='min')[t]),'def_epa_rank':int(de.epa_rate.rank(method='min')[t]),'off_gp':int(off.gp[t]),'def_gp':int(de.gp[t])}
# Player source identities never normalized-name joined.
hist={pid:g.sort_values(['season','week']) for pid,g in d.groupby('player_id')};den=d.groupby(['season','team']).apply(lambda x:x.sort_values('week'),include_groups=False) if False else None
allcurcache={(y,w,t):g[g.week<w] for (y,t),g in d.groupby(['season','team']) for w in range(3,19)}
lam=json.load(open(R/'tools/props_w4/validation_atd.json'))['lam'];rows=[]
def row(g,season,week,teamname,opp,home):
 h=g[(g.season<season)|((g.season==season)&(g.week<week))];cur=h[(h.season==season)&(h.team==teamname)];allcur=allcurcache[(season,week,teamname)]
 if len(h)<3 or len(cur)<2 or h.touch.tail(6).mean()<3:return None
 off=teamfeatures.get((season,week,teamname));de=teamfeatures.get((season,week,opp))
 if not off or not de:return None
 pos=h.position.iloc[-1];v=h.tds.tail(17).to_numpy();w=.5**(np.arange(len(v))[::-1]/12);base=1-np.exp(-((w*v).sum()+4*lam.get(pos,.28))/(w.sum()+4));x={'baseline_logit':float(np.log(np.clip(base,1e-6,1-1e-6)/(1-np.clip(base,1e-6,1-1e-6)))),'is_home':home}
 for c in ['targets','carries']+rzcols:x[c+'_share']=float(cur[c].sum()/max(1,allcur[c].sum()))
 for c in ['targets','carries']:x[c+'_recent4']=float(cur[c].tail(4).mean())
 for c in ['epa_rate','rush_rate','pass_rate']:x['off_'+c]=off['off_'+c];x['opp_'+c]=de['def_'+c]
 for p in ['QB','RB','TE']:x['pos_'+p]=int(pos==p)
 return dict(x=x,baseline=float(base),off_epa_rank=off['off_epa_rank'],opp_def_epa_rank=de['def_epa_rank'],prior_current_games=len(cur))
games=pd.read_csv(R/'tools/player_projection_cache/schedules.csv');home=dict(zip(games.game_id,games.home_team.replace(AL)))
for pid,g in hist.items():
 for a in g[g.week>=3].itertuples():
  if a.season>2025:continue
  x=row(g,a.season,a.week,a.team,a.opponent_team,int(home.get(a.game_id)==a.team))
  if x:rows.append(dict(player_id=pid,player=a.player_display_name,game_id=a.game_id,season=a.season,week=a.week,team=a.team,y=a.y,**x))
print('features',len(rows),flush=True);features=list(rows[0]['x']);df=pd.DataFrame([{**{k:v for k,v in r.items() if k!='x'},**r['x']} for r in rows]);df.to_pickle(OUT/'dataset.pkl');tr=df.season<=2023;va=df.season==2024;te=df.season==2025
models=[]
for c in [.01,.1,1]:
 m=make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=1000)).fit(df.loc[tr,features],df.loc[tr,'y']);p=m.predict_proba(df.loc[va,features])[:,1];models.append((log_loss(df.loc[va,'y'],p),c,m))
_,c,m=min(models,key=lambda x:x[0]);joblib.dump(m,OUT/'candidate.joblib');res={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selected_C':c,'features':features,'splits':{},'warning':'2025 seen diagnostic; conditional played-player cohort, not inactive/role availability test'}
for name,mask in [('validation2024',va),('seen2025',te)]:
 y=df.loc[mask,'y'];p=m.predict_proba(df.loc[mask,features])[:,1];b=df.loc[mask,'baseline'];res['splits'][name]={'n':int(mask.sum()),'events':int(y.sum()),'candidate_brier':brier_score_loss(y,p),'baseline_brier':brier_score_loss(y,b),'candidate_logloss':log_loss(y,p),'baseline_logloss':log_loss(y,b),'mean_probability':float(p.mean()),'event_rate':float(y.mean())};df.loc[mask,'candidate']=p
# paired game-cluster diagnostic
z=df[te];dd=z.assign(bd=(z.candidate-z.y)**2-(z.baseline-z.y)**2).groupby('game_id').agg(s=('bd','sum'),n=('bd','size'));rng=np.random.default_rng(921);arr=[]
for _ in range(2000):
 ii=rng.integers(0,len(dd),len(dd));t=dd.iloc[ii];arr.append(t.s.sum()/t.n.sum())
res['seen2025_brier_delta_CI95']=np.quantile(arr,[.025,.975]).tolist();json.dump(res,open(OUT/'diagnostics.json','w'),indent=2);print(json.dumps(res['splits'],indent=2),flush=True)
# fixed current cohort matching published names via exact ID source + team, reject ambiguous
board=json.load(open(R/'week8_anytime_td.json'));current=[]
for b in board['rows']:
 if b['team'] not in ['CAR','GB']:continue
 z=d[(d.player_display_name==b['player'])&(d.team==b['team'])];ids=z.player_id.unique()
 if len(ids)!=1:continue
 a=row(hist[ids[0]],2026,8,b['team'],b['opp'],int(b['team']=='GB'))
 if not a:continue
 pr=float(m.predict_proba(pd.DataFrame([a['x']])[features])[0,1]);current.append(dict(player_id=ids[0],player=b['player'],team=b['team'],opponent=b['opp'],baseline_published=b['model'],candidate=pr,features=a['x'],off_epa_rank=a['off_epa_rank'],opp_def_epa_rank=a['opp_def_epa_rank'],prior_current_games=a['prior_current_games'],own_status=b.get('own_status'),role=b.get('role'),eligibility='pending final active/role check'))
json.dump({'generated_at':res['created_at'],'research_only':True,'rows':current},open(OUT/'tonight_preliminary.json','w'),indent=2);print('tonight',[(x['player'],round(x['candidate'],3)) for x in current],flush=True)
