#!/usr/bin/env python3
"""Locked NFL anytime-TD research prototype. No picks and no market-edge claim.
Protocol: train 2023-24, validate 2025 W1-9 once, freeze, test 2025 W10+.
Requires nflverse weekly stats/PBP/schedules cached under tools/td_model_cache.
"""
from pathlib import Path
import json, math
import numpy as np, pandas as pd
from scipy.optimize import minimize
from sklearn.linear_model import PoissonRegressor, LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]; CACHE=ROOT/'tools/td_model_cache'; OUT=ROOT/'tools/anytime_td_research_v1.json'
SEASONS=(2023,2024,2025); POS=('QB','RB','WR','TE')
USAGE=['carries','targets','rushing_tds','receiving_tds']
ALLOC=['log_opp','rz_share','gl_share','target_share','carry_share','td_rate','is_qb','is_rb','is_te']

def sigmoid(x): return 1/(1+np.exp(-np.clip(x,-30,30)))
def metrics(y,p):
    p=np.clip(np.asarray(p),1e-8,1-1e-8); y=np.asarray(y)
    out={'n':int(len(y)),'events':int(y.sum()),'event_rate':float(y.mean()),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1]))}
    out['auc']=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None
    z=np.log(p/(1-p)).reshape(-1,1)
    cal=LogisticRegression(C=1e6,max_iter=1000).fit(z,y)
    out['calibration_intercept']=float(cal.intercept_[0]); out['calibration_slope']=float(cal.coef_[0,0])
    out['mean_probability']=float(p.mean())
    return out

def paired_bootstrap(x,reps=500):
    # Game-cluster bootstrap for model-minus-naive metric deltas; negative favors model.
    rng=np.random.default_rng(4242); games=x.game_id.unique(); vals=[]
    for _ in range(reps):
        pick=rng.choice(games,len(games),replace=True); parts=[x[x.game_id==g] for g in pick]; b=pd.concat(parts,ignore_index=True); y=b.y.to_numpy(); pm=np.clip(b.p_model.to_numpy(),1e-8,1-1e-8); pn=np.clip(b.p_naive.to_numpy(),1e-8,1-1e-8)
        vals.append((np.mean((y-pm)**2)-np.mean((y-pn)**2),np.mean(-(y*np.log(pm)+(1-y)*np.log(1-pm)))-np.mean(-(y*np.log(pn)+(1-y)*np.log(1-pn)))))
    a=np.asarray(vals)
    return {'brier_delta_model_minus_naive':{'estimate':float(np.mean((x.y-x.p_model)**2)-np.mean((x.y-x.p_naive)**2)),'ci95':[float(v) for v in np.quantile(a[:,0],[.025,.975])]},'log_loss_delta_model_minus_naive':{'estimate':float(np.mean(-(x.y*np.log(np.clip(x.p_model,1e-8,1-1e-8))+(1-x.y)*np.log(np.clip(1-x.p_model,1e-8,1-1e-8))))-np.mean(-(x.y*np.log(np.clip(x.p_naive,1e-8,1-1e-8))+(1-x.y)*np.log(np.clip(1-x.p_naive,1e-8,1-1e-8))))),'ci95':[float(v) for v in np.quantile(a[:,1],[.025,.975])]}}

def load():
    stats=[]; rz=[]
    use=['player_id','player_display_name','position','team','season','week','season_type','game_id','opponent_team','carries','targets','rushing_tds','receiving_tds']
    for y in SEASONS:
        s=pd.read_csv(CACHE/f'stats_{y}.csv',usecols=use,low_memory=False); stats.append(s[(s.season_type=='REG')&s.position.isin(POS)])
        p=pd.read_parquet(CACHE/f'pbp_{y}.parquet',columns=['game_id','season','week','season_type','posteam','defteam','yardline_100','play_type','rusher_player_id','receiver_player_id','rush_touchdown','pass_touchdown','touchdown','drive'])
        p=p[(p.season_type=='REG')&p.posteam.notna()]
        for typ,pid in [('carry','rusher_player_id'),('target','receiver_player_id')]:
            q=p[p[pid].notna() & p.play_type.eq('run' if typ=='carry' else 'pass')].copy(); q['player_id']=q[pid]
            q['rz']=q.yardline_100.le(20).astype(int); q['in10']=q.yardline_100.le(10).astype(int); q['gl']=q.yardline_100.le(5).astype(int)
            q['score']=np.where(typ=='carry',q.rush_touchdown.fillna(0),q.pass_touchdown.fillna(0))
            a=q.groupby(['season','week','game_id','posteam','defteam','player_id']).agg(**{f'{typ}_rz':('rz','sum'),f'{typ}_in10':('in10','sum'),f'{typ}_gl':('gl','sum')}).reset_index(); rz.append(a)
    s=pd.concat(stats,ignore_index=True).fillna({c:0 for c in USAGE}); r=pd.concat(rz,ignore_index=True).groupby(['season','week','game_id','posteam','defteam','player_id'],as_index=False).sum(numeric_only=True)
    s=s.merge(r,left_on=['season','week','game_id','team','opponent_team','player_id'],right_on=['season','week','game_id','posteam','defteam','player_id'],how='left').drop(columns=['posteam','defteam'])
    rc=[c for c in s if c.endswith(('_rz','_in10','_gl'))]; s[rc]=s[rc].fillna(0); s['tds']=s.rushing_tds+s.receiving_tds; s['y']=(s.tds>0).astype(int)
    return s

def features(s):
    s=s.sort_values(['player_id','season','week']).copy(); g=s.groupby('player_id',group_keys=False)
    lagcols=['carries','targets','tds','carry_rz','target_rz','carry_in10','target_in10','carry_gl','target_gl']
    for c in lagcols:
        s[c+'_r6']=g[c].transform(lambda x:x.shift().rolling(6,min_periods=2).sum())
    s['games_r6']=g['game_id'].transform(lambda x:x.shift().rolling(6,min_periods=2).count())
    # Team shares are based only on each player's lagged totals within that pregame team roster snapshot.
    s['opp_r6']=s.carries_r6+s.targets_r6; s['rz_r6']=s.carry_rz_r6+s.target_rz_r6; s['gl_r6']=s.carry_gl_r6+s.target_gl_r6
    for c,new in [('targets_r6','target_share'),('carries_r6','carry_share'),('rz_r6','rz_share'),('gl_r6','gl_share')]:
        den=s.groupby(['season','week','game_id','team'])[c].transform('sum'); s[new]=(s[c]/den.replace(0,np.nan)).fillna(0)
    s['td_rate']=(s.tds_r6/(s.games_r6+2)).fillna(0); s['log_opp']=np.log1p(s.opp_r6.fillna(0)/s.games_r6.clip(lower=1))
    for p in POS:s['is_'+p.lower()]=(s.position==p).astype(int)
    games=pd.read_csv(CACHE/'games.csv'); games=games[(games.season.isin(SEASONS))&(games.game_type=='REG')][['game_id','home_team','away_team','home_score','away_score','spread_line','total_line']]
    s=s.merge(games,on='game_id',how='left'); s['is_home']=(s.team==s.home_team)
    s['implied_total']=np.where(s.is_home,(s.total_line-s.spread_line)/2,(s.total_line+s.spread_line)/2)
    # Historical schedule lines are treated as the available pregame market context; no FanDuel player prices are used.
    s=s[(s.games_r6>=2)&s.implied_total.notna()&s.player_id.notna()].copy()
    team=s.groupby(['season','week','game_id','team','opponent_team','implied_total'],as_index=False).agg(team_tds=('tds','sum'))
    team=team.merge(games[['game_id','home_score','away_score','home_team']],on='game_id',how='left'); team['team_points']=np.where(team.team==team.home_team,team.home_score,team.away_score)
    # Lagged team scoring and lagged opponent TD allowed, strictly shifted.
    team=team.sort_values(['team','season','week']); team['team_td_r6']=team.groupby('team').team_tds.transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
    team=team.sort_values(['opponent_team','season','week']); team['opp_td_allowed_r6']=team.groupby('opponent_team').team_tds.transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
    team[['team_td_r6','opp_td_allowed_r6']]=team[['team_td_r6','opp_td_allowed_r6']].fillna(team[['team_td_r6','opp_td_allowed_r6']].median())
    s=s.merge(team[['game_id','team','team_tds','team_td_r6','opp_td_allowed_r6']],on=['game_id','team'],how='left')
    return s,team

def fit_team(team):
    fs=['implied_total','team_td_r6','opp_td_allowed_r6']; tr=team[team.season<=2024].dropna(subset=fs)
    sc=StandardScaler().fit(tr[fs]); m=PoissonRegressor(alpha=1.0,max_iter=1000).fit(sc.transform(tr[fs]),tr.team_tds)
    return fs,sc,m

def fit_alloc(s,alpha):
    tr=s[s.season<=2024].dropna(subset=ALLOC).copy(); sc=StandardScaler().fit(tr[ALLOC]); X=sc.transform(tr[ALLOC]); y=tr.tds.to_numpy(float); groups=pd.factorize(tr.game_id.astype(str)+'|'+tr.team)[0]
    idx=[np.where(groups==k)[0] for k in np.unique(groups)]
    def obj(w):
        val=.5*alpha*np.dot(w,w); grad=alpha*w
        z=X@w
        for ii in idx:
            zz=z[ii]-z[ii].max(); pr=np.exp(zz); pr/=pr.sum(); n=y[ii].sum()
            if n: val-=np.dot(y[ii],np.log(np.clip(pr,1e-12,1))); grad+=X[ii].T@(n*pr-y[ii])
        return val,grad
    res=minimize(lambda w:obj(w),np.zeros(X.shape[1]),jac=True,method='L-BFGS-B',options={'maxiter':400});
    if not res.success: raise RuntimeError(res.message)
    return sc,res.x

def predict(s,tfit,afit):
    fs,ts,tm=tfit; asc,w=afit; o=s.copy(); o['team_lambda']=np.maximum(.01,tm.predict(ts.transform(o[fs])))
    o['score']=asc.transform(o[ALLOC])@w; o['allocation']=0.0
    for _,ii in o.groupby(['game_id','team']).groups.items():
        ii=list(ii); z=o.loc[ii,'score'].to_numpy(); z-=z.max(); p=np.exp(z); o.loc[ii,'allocation']=p/p.sum()
    o['lambda_player']=o.team_lambda*o.allocation; o['p_model']=1-np.exp(-o.lambda_player)
    # Naive baseline: team lambda allocated by weighted opportunity, with smoothing to avoid zeroing every low-usage player.
    raw=1+o.targets_r6+o.carries_r6+2*(o.target_in10_r6+o.carry_in10_r6)+3*(o.target_gl_r6+o.carry_gl_r6)
    den=raw.groupby([o.game_id,o.team]).transform('sum'); share=raw/den; o['p_naive']=1-np.exp(-o.team_lambda*share)
    # Position/base-rate baseline estimated from train only.
    rates=s[s.season<=2024].groupby('position').y.mean().to_dict(); o['p_position']=o.position.map(rates).fillna(s[s.season<=2024].y.mean())
    return o

def main():
    s,team=features(load()); tfit=fit_team(team)
    # Validation is used once to choose regularization from a short declared grid, then frozen before W10+.
    grid=[]
    for a in (.1,1.0,10.0):
        af=fit_alloc(s,a); p=predict(s,tfit,af); v=p[(p.season==2025)&(p.week<=9)]; grid.append((metrics(v.y,v.p_model)['log_loss'],a,af))
    _,alpha,afit=min(grid,key=lambda x:x[0]); p=predict(s,tfit,afit)
    splits={'validation_2025_w1_9':p[(p.season==2025)&(p.week<=9)],'locked_test_2025_w10_plus':p[(p.season==2025)&(p.week>=10)]}
    result={'schema_version':'1.0.0','status':'research_only_no_picks','protocol':{'train':'2023-2024 regular seasons','validation':'2025 weeks 1-9, one pass selecting allocation L2 alpha from [0.1,1,10]','locked_test':'2025 weeks 10+; untouched until model freeze','selected_alpha':alpha},'model':{'stage_1':'Poisson team offensive TD expectation from pregame consensus implied total plus lagged team TD and opponent TD allowed','stage_2':'Within-team softmax allocation of team TD expectation from lagged opportunity, red-zone/goal-line share, target/carry share, TD rate and position','probability':'1-exp(-team_lambda*player_allocation)'},'limitations':['No historical FanDuel anytime-TD prices or closes exist, so edge, CLV and ROI are untestable.','Historical player-week rows come from end-of-season nflverse files; point-in-time inactive/depth-chart history is unavailable.','Participation source is not true routes run and was not represented as routes.','Schedule total/spread is market context, but source does not provide a timestamped FanDuel provenance for these historical values.'],'sources':['https://nflreadr.nflverse.com/reference/load_pbp.html','https://nflreadr.nflverse.com/','https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv'],'splits':{},'verdict':{}}
    for n,x in splits.items(): result['splits'][n]={k:metrics(x.y,x[k]) for k in ['p_model','p_naive','p_position']}
    test_df=splits['locked_test_2025_w10_plus']; result['locked_test_paired_game_bootstrap']=paired_bootstrap(test_df)
    te=result['splits']['locked_test_2025_w10_plus']; win=te['p_model']['log_loss']<te['p_naive']['log_loss'] and te['p_model']['brier']<te['p_naive']['brier']
    ci=result['locked_test_paired_game_bootstrap']; settled=(ci['brier_delta_model_minus_naive']['ci95'][1]<0 and ci['log_loss_delta_model_minus_naive']['ci95'][1]<0)
    if win and settled: conclusion='Prototype clears the naive opportunity baseline with paired 95% intervals below zero, but is not a betting model until it beats timestamped FanDuel prices prospectively.'
    elif win: conclusion='Prototype is numerically better than the naive opportunity baseline on locked-test Brier and log loss, but the paired game-bootstrap 95% intervals cross zero. The improvement is not settled. Keep measurement only; no picks.'
    else: conclusion='Prototype does not beat the naive opportunity baseline on both locked-test Brier and log loss. Do not use it for picks; keep measurement only.'
    result['verdict']={'beats_naive_opportunity_baseline_on_brier_and_log_loss':bool(win),'improvement_statistically_settled_at_paired_95pct':bool(settled),'honest_conclusion':conclusion}
    OUT.write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
