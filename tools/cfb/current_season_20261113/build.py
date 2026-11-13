"""Owner-requested season-only version. Correctness checks, not claimed validated skill."""
import pathlib,json,gzip,hashlib,datetime,collections,sys,os
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
P=pathlib.Path(__file__).parent;R=pathlib.Path(os.environ.get('EDITH_ROOT','/tmp/edith'));F=P;now=datetime.datetime.now(datetime.timezone.utc).isoformat();games=json.load(open(P/'canonical_input.json'));members={int(y):set(v)for y,v in json.load(open(R/'tools/model_cfb_v2/national_rank_variant/fbs-names.json')).items()};manifest=[]
cols=['pass_cmp','pass_att','pass_yds','pass_td','pass_int','rush_att','rush_yds','rush_td','rec','rec_yds','rec_td']
pg=pd.concat([pd.read_csv(f,dtype={'event_id':str,'player_id':str})for f in sorted((R/'tools/espn/player_games').glob('*cfb*'))]);pg=pg[pg.season.between(2022,2025)].copy();assert (pg.groupby(['event_id','team','player_id'])[cols].count()<=1).all().all(),'duplicatecategory-stat'
pg=pg.groupby(['event_id','league','season','date','team','player_id','player_name'],as_index=False)[cols].sum()
# Parse complete current summaries; preserve stable player IDs and explicit categories.
by={}
for folder in ['tools/cfb/boxscores','tools/cfb/current_inputs_20261016/boxscores','tools/cfb/saturday_20261107/sources']+sorted(str(p.relative_to(R))for p in(R/'tools/cfb').glob('week*_20*/boxscores')):
 for f in sorted(list((R/folder).glob('boxscore-*.json'))+list((R/folder).glob('boxscore-*.json.gz'))):by[f.name.split('boxscore-')[-1].split('.json')[0]]=f
for f in(P/'sources').glob('boxscore-*.json'):by[f.name.split('boxscore-')[-1].split('.json')[0]]=f
current=[];extra=[];known={g['event_id']for g in games}
for eid,f in sorted(by.items()):
 d=json.load(gzip.open(f,'rt')if f.suffix=='.gz'else open(f));c=d['header']['competitions'][0]
 if not c['status']['type']['completed']:continue
 t={z['homeAway']:z for z in c['competitors']};h,a=t['home']['team']['displayName'],t['away']['team']['displayName']
 if h not in members[2026]or a not in members[2026]:continue
 stats={z['homeAway']:{s['name']:s['displayValue']for s in z['statistics']}for z in d['boxscore']['teams']};sv={}
 for side,opp in [('home','away'),('away','home')]:
  z,oz=stats[side],stats[opp];sv[side]=dict(pf=float(t[side]['score']),pa=float(t[opp]['score']),yf=float(z['totalYards']),ya=float(oz['totalYards']),passf=float(z['netPassingYards']),passa=float(oz['netPassingYards']),rushf=float(z['rushingYards']),rusha=float(oz['rushingYards']),tof=float(oz['turnovers']),tol=float(z['turnovers']))
 if eid not in known:extra.append(dict(event_id=eid,season=2026,date=c['date'],home=h,away=a,neutral=bool(c['neutralSite']),home_score=float(t['home']['score']),away_score=float(t['away']['score']),stats=sv,kind='2026 final newlycaptured'))
 assert d['boxscore'].get('players'),eid
 for team in d['boxscore']['players']:
  tm=team['team']['displayName'];ps={}
  for cat in team['statistics']:
   if cat['name']not in ['passing','rushing','receiving']:continue
   for ath in cat.get('athletes',[]):
    aid=str(ath['athlete']['id']);z=ps.setdefault(aid,dict(event_id=eid,league='CFB',season=2026,date=c['date'][:10],team=tm,player_id=aid,player_name=ath['athlete']['displayName'],**{k:0. for k in cols}));v=dict(zip(cat['keys'],ath['stats']))
    def num(k):
     x=str(v.get(k,'0')).replace(',','');return float(x)if x not in ['--','-','']else 0.
    if cat['name']=='passing':
     ca=v.get('completions/passingAttempts',v.get('completions/attempts'));assert ca and'/'in ca,(eid,aid,cat['keys']);co,at=ca.split('/');z.update(pass_cmp=float(co),pass_att=float(at),pass_yds=num('passingYards'),pass_td=num('passingTouchdowns'),pass_int=num('interceptions'))
    elif cat['name']=='rushing':z.update(rush_att=num('rushingAttempts'),rush_yds=num('rushingYards'),rush_td=num('rushingTouchdowns'))
    else:z.update(rec=num('receptions'),rec_yds=num('receivingYards'),rec_td=num('receivingTouchdowns'))
  current.extend(ps.values())
 manifest.append({'event_id':eid,'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
games=sorted(games+extra,key=lambda g:(g['date'],g['event_id']));pg=pd.concat([pg,pd.DataFrame(current)],ignore_index=True);assert not pg.duplicated(['event_id','team','player_id']).any();agg=pg.groupby(['event_id','team'])[cols].sum();ids={r.event_id for r in pg.itertuples()};gameby={g['event_id']:g for g in games};history=collections.defaultdict(list)
for g in games:
 for side in ['home','away']:history[g['season'],g[side]].append(g)
metrics=['pf','pa','yf','ya','pass_completion_rate','pass_ypa','pass_td_rate','pass_int_rate','rush_ypa','rush_td_rate','rec_ypc','rec_td_rate','record_strength','schedule_strength','opp_score_rating','opp_yard_rating']
cache={};abstain=[];provenance=[]
def context(day,yr):
 key=(day,yr)
 if key in cache:return cache[key]
 prior=[g for g in games if g['season']==yr and g['date'][:10]<day];names=sorted(members[yr]);ix={n:i for i,n in enumerate(names)};n=len(names);C=2*np.eye(n);b=np.ones(n);A=np.zeros((len(prior),n+1));Y=np.zeros((len(prior),2));op=collections.defaultdict(list)
 for i,g in enumerate(prior):
  h,a=ix[g['home']],ix[g['away']];C[h,h]+=1;C[a,a]+=1;C[h,a]-=1;C[a,h]-=1;v=.5 if g['home_score']>g['away_score']else-.5;b[h]+=v;b[a]-=v;op[h].append(a);op[a].append(h);A[i,h]=1;A[i,a]=-1;A[i,n]=0 if g['neutral']else 1;Y[i]=[g['home_score']-g['away_score'],g['stats']['home']['yf']-g['stats']['away']['yf']]
 col=np.linalg.solve(C,b);coef=np.linalg.solve(A.T@A+20*np.eye(n+1),A.T@Y);coef[:n]-=coef[:n].mean(axis=0);vals={}
 for tm in names:
  hist=[g for g in history[yr,tm]if g['date'][:10]<day]
  if len(hist)<3:continue
  if any((g['event_id'],tm)not in agg.index for g in hist):continue
  pp=agg.loc[[(g['event_id'],tm)for g in hist]].sum();at,ra,rc=pp.pass_att,pp.rush_att,pp.rec
  if min(at,ra,rc)<=0:continue
  teamstats=[g['stats']['home'if g['home']==tm else'away']for g in hist];v={k:float(np.mean([z[k]for z in teamstats]))for k in ['pf','pa','yf','ya']};j=ix[tm];v.update(pass_completion_rate=pp.pass_cmp/at,pass_ypa=pp.pass_yds/at,pass_td_rate=pp.pass_td/at,pass_int_rate=pp.pass_int/at,rush_ypa=pp.rush_yds/ra,rush_td_rate=pp.rush_td/ra,rec_ypc=pp.rec_yds/rc,rec_td_rate=pp.rec_td/rc,record_strength=float(col[j]),schedule_strength=float(col[op[j]].mean())if op[j]else .5,opp_score_rating=float(coef[j,0]),opp_yard_rating=float(coef[j,1]));vals[tm]=(v,len(hist),[g['event_id']for g in hist])
 cache[key]=vals;return vals
def make(g,cut=None):
 day=cut or g['date'][:10];cs=context(day,g['season']);h,a=g['home'],g['away']
 if h not in cs or a not in cs:return None
 hv,hgp,hi=cs[h];av,agp,ai=cs[a];x={'d_'+m:float(hv[m]-av[m])for m in metrics};x['home_field']=0. if g['neutral']else 1.;x.update(event_id=g['event_id'],season=g['season'],date=g['date'],home=h,away=a,home_gp=hgp,away_gp=agp);assert np.isfinite([x['d_'+m]for m in metrics]+[x['home_field']]).all();provenance.append(dict(event_id=g['event_id'],cutoff_date=day,home_history=hi,away_history=ai,context_games=[z['event_id']for z in games if z['season']==g['season']and z['date'][:10]<day]));return x
train=[]
for g in games:
 if g['season']<2023:continue
 z=make(g)
 if z is None:abstain.append({'event_id':g['event_id'],'reason':'fewerthan3earlierFBSgamesorplayerstatcoverage/denominatorgap'});continue
 z['margin']=g['home_score']-g['away_score'];train.append(z)
D=pd.DataFrame(train);fs=['d_'+m for m in metrics]+['home_field'];X=D[fs].to_numpy();y=D.margin.to_numpy();model=make_pipeline(StandardScaler(),Ridge(alpha=10,fit_intercept=False)).fit(np.vstack([X,-X]),np.r_[y,-y]);slate=json.load(open(P/'sources/week11.json'));future=[]
for e in slate['events']:
 c=e['competitions'][0]
 if c['status']['type']['state']!='pre':continue
 t={z['homeAway']:z['team']['displayName']for z in c['competitors']};g=dict(event_id=e['id'],season=2026,date=c['date'],home=t['home'],away=t['away'],neutral=bool(c.get('neutralSite')))
 if g['home']not in members[2026]or g['away']not in members[2026]:continue
 z=make(g,datetime.datetime.now(datetime.timezone.utc).date().isoformat())
 if z is None:future.append(dict(g,status='withheld_missing_current_inputs'));continue
 x=np.array([[z[k]for k in fs]]);m=float(model.predict(x)[0]);rev=float(model.predict(-x)[0]);assert abs(m+rev)<1e-10;future.append(dict(g,raw_margin_home=m,display_margin_home=round(m*2)/2,features={k:z[k]for k in fs},home_gp=z['home_gp'],away_gp=z['away_gp'],forecast_status='season_only_stats_forecast_injury_adjustment_unavailable',injury_numeric_adjustment=None))
metadata={'version':'CFB-current-season-SOS-record-player-v1-owner-requested','generated_at':now,'requested_change':'SOS/recordstrengthandcurrent-seasonplayerproduction,no pre-season talent/prioryearstatprofiles','status':'Owner-requestednewversion,accuracyunvalidated;notfrozenNov9challenger','source_cutoff':'Allcompletedeligible2026FBS-versus-FBSfinalsthroughNov12,beforeNov13UTC','record_strength_definition':'ColleyW/Lratingsfromthisseasoncompletedgamesbeforeforecastcutoff,notESPNproprietarySOR','schedule_strength_definition':'MeanColleyratingofopponentsalreadyfaced,thisseasononly','player_inputs':'Current-seasonpassing/rushing/receivingplayerboxscoretotals,by stableathleteID/team/event,aggregatedtoteamratefeatures. Notfutureplayerprojectionorhistoricalroster-membershipfilter. Departures/available-roleadjustmentnotverified.','training':'Past-onlysame-seasonfeatures,min3priorFBSgamesbothteams;2023throughNov12,2026;mirroredStandardScaler+Ridgealpha10,fit_interceptfalse. Coefficientsfitwithoutperformance-testprerequisite,novalidatedimprovementclaim.','features':fs,'training_rows':len(D),'training_rows_by_season':D.groupby('season').size().to_dict(),'training_exclusions':len(abstain),'preseason_talent_inputs':False,'prior_season_stats_inputs':False,'odds_inputs':False,'injury_numeric_inputs':False,'injury_limitation':'Currentavailabilityisaseparateexplicitgate/context.Notnumericallyadjusted:no defensible player-to-points/replacementcoefficient supplied. Neverinterpretcontextasadjustedspread.','original_versions':'OriginalWeek11seal,frozenNov9winnerchallengerandtheirtrackrecordsunchanged;donotgradethisnewversionasifknownNov8.','scaler_mean':model[0].mean_.tolist(),'scaler_scale':model[0].scale_.tolist(),'coefficients':model[1].coef_.tolist()}
(P/'canonical_used.json').write_text(json.dumps(games)+'\n');(P/'current_forecasts.json').write_text(json.dumps({'metadata':metadata,'games':future},indent=2)+'\n');(P/'training_features.json').write_text(json.dumps(train)+'\n');(P/'feature_provenance.json').write_text(json.dumps(provenance)+'\n');(P/'training_exclusions.json').write_text(json.dumps(abstain,indent=2)+'\n');(P/'player_sources.json').write_text(json.dumps(manifest,indent=2)+'\n');pd.DataFrame(current).to_csv(P/'current_player_games.csv',index=False);print('train',len(D),'future',len(future),'extraFinals',len(extra),'2026players',len(current));print([(g['away'],g['home'],g.get('display_margin_home'))for g in future if 'Tennessee'in g['away']or'Texas Longhorns'in g['away']]);
