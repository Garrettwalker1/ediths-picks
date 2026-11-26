"""Versioned opponent-adjusted possession model candidate, not validated.
Ridge regularization fixed at five game-equivalents, not tuned to outcomes.
No current-roster metrics retrofitted into past games. Player features are
coverage/context pending prospective contribution testing, not fake effects.
"""
import collections,json,math
import numpy as np
from predictor import eligible,time,VERSION
VERSION='cbb-efficiency-v1-ridge5'
def estimate(g):
 vals=[]
 for side in ('home','away'):
  d=g['team_box_statistics'][g[side+'_id']]
  fga=float(d['fieldGoalsMade-fieldGoalsAttempted'].split('-')[1]);fta=float(d['freeThrowsMade-freeThrowsAttempted'].split('-')[1]);orb=float(d['offensiveRebounds']);to=float(d.get('totalTurnovers',d['turnovers']))
  poss=fga-orb+to+.475*fta
  if not math.isfinite(poss) or poss<=0:raise ValueError('possessions')
  vals.append(poss)
 return sum(vals)/2

def fit(games,target,T):
 pool=[]
 for g in games:
  if eligible(g,target,T):
   try:p=estimate(g);pool.append((g,p))
   except (KeyError,TypeError,ValueError):continue
 seen={}
 for g,p in sorted(pool,key=lambda q:time(q[0]['received_at'])):seen.setdefault(g['event_id'],(g,p))
 pool=list(seen.values());teams=sorted({g[k] for g,p in pool for k in ('home_id','away_id')});ix={t:i for i,t in enumerate(teams)};n=len(teams)
 if not pool:return None
 mu=sum((g['home_points']+g['away_points'])/p*100 for g,p in pool)/(2*len(pool))
 X=[];Y=[];counts=collections.Counter();pace=collections.defaultdict(list)
 for g,p in pool:
  period=g.get('period',2);minutes=40+5*max(0,period-2);norm=p*40/minutes
  for side,other in (('home','away'),('away','home')):
   team=g[side+'_id'];opp=g[other+'_id'];r=np.zeros(2*n);r[ix[team]]=1;r[n+ix[opp]]=1;X.append(r);Y.append(100*g[side+'_points']/p-mu);counts[team]+=1;pace[team].append(norm)
 X=np.array(X);Y=np.array(Y);coef=np.linalg.solve(X.T@X+5*np.eye(2*n),X.T@Y)
 return dict(teams=teams,ix=ix,mu=mu,coef=coef,counts=counts,pace=pace,games=pool)

def predict_efficiency(games,target,T):
 from predictor import predict
 baseline=predict(games,target,T)
 out={k:v for k,v in baseline.items()};out['model_version']=VERSION
 if baseline['status']!='prediction_computed_not_issued':return out
 m=fit(games,target,T)
 if m is None:
  for k in ('home_points','away_points','margin_home_minus_away','total_points'):out[k]=None
  out.update(status='withheld',reason='no_possession_inputs');return out
 h,a=target['home_id'],target['away_id'];ix=m['ix'];n=len(ix)
 if h not in ix or a not in ix:
  for k in ('home_points','away_points','margin_home_minus_away','total_points'):out[k]=None
  out.update(status='withheld',reason='missing_possession_form');return out
 pace_mean=sum(x for vs in m['pace'].values() for x in vs)/sum(len(vs) for vs in m['pace'].values())
 tempos={t:(sum(m['pace'][t])+5*pace_mean)/(len(m['pace'][t])+5) for t in (h,a)};pace=(tempos[h]+tempos[a])/2
 o=lambda t:float(m['coef'][ix[t]]);d=lambda t:float(m['coef'][n+ix[t]])
 hp=(m['mu']+o(h)+d(a))*pace/100;ap=(m['mu']+o(a)+d(h))*pace/100
 out.update(home_points=hp,away_points=ap,margin_home_minus_away=hp-ap,total_points=hp+ap,pooled_team_points=None,
  adjusted_efficiency={t:{'offense_per100':m['mu']+o(t),'defense_allowed_per100':m['mu']+d(t),'pace_per40':tempos[t],'games':m['counts'][t]} for t in (h,a)},
  opponent_adjustment='ridge additive offense/defense, lambda5 fixed, no home effect; limited prospective-window schedule, not validated',
  input_event_ids=sorted(g['event_id'] for g,p in m['games']))
 return out
