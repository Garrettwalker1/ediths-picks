"""Postgame audit and fixed-rule state assimilation. No fitting or forecast rewriting.
Run from repo root: python3 tools/nfl/learning/20261022_ne_chi/learn_game.py
"""
import pathlib,sys,json,hashlib,datetime
import pandas as pd,numpy as np
P=pathlib.Path(__file__).resolve().parent;R=P.parents[3]
sys.path.insert(0,str(R/'tools/model_nfl_v3_2/point_in_time'));import elo_candidate as E,totals_candidate as T
GID='2026_07_NE_CHI';g=pd.read_csv(P/'games_asof_20261022.csv',low_memory=False);g=g[g.game_type.isin(['REG','WC','DIV','CON','SB'])].copy();r=g[g.game_id==GID].iloc[0];assert (r.home_score,r.away_score)==(30,24)
# Nothing after the TNF gameday can be learned; future outcomes cannot enter pregame features.
assert g[(g.season==2026)&(g.gameday>'2026-10-22')].home_score.isna().all()
pre=g.copy();pre.loc[pre.game_id==GID,['home_score','away_score']]=np.nan
Epre=E.diffs(pre);Epost=E.diffs(g);Fpre=T.feats(pre[pre.game_type=='REG']);Fpost=T.feats(g[g.game_type=='REG'])
assert Epre[GID]==Epost[GID]
a=Fpre[Fpre.game_id==GID].iloc[0];b=Fpost[Fpost.game_id==GID].iloc[0];assert np.allclose(a[T.COLS].astype(float),b[T.COLS].astype(float))
# Audit the already-declared next-six-game-half-life update, not a new fitted rule.
weight=1-.5**(1/6);states={}
for team,loc,score,allow in [('NE','a',24,30),('CHI','h',30,24)]:
 pf,pa=float(b[loc+'pf']),float(b[loc+'pa']);future=g[(g.gameday>r.gameday)&((g.home_team==team)|(g.away_team==team))].sort_values(['gameday','game_id']).iloc[0];f0=Fpre[Fpre.game_id==future.game_id].iloc[0];f1=Fpost[Fpost.game_id==future.game_id].iloc[0];prefix='h' if future.home_team==team else 'a';newpf=pf+weight*(score-pf);newpa=pa+weight*(allow-pa)
 assert np.isclose(newpf,f1[prefix+'pf']) and np.isclose(newpa,f1[prefix+'pa'])
 assert not np.isclose(Epre[future.game_id],Epost[future.game_id])
 states[team]={'last_completed_game':GID,'next_game_id':future.game_id,'points_for_before':pf,'points_for_after':newpf,'points_against_before':pa,'points_against_after':newpa,'next_game_elo_difference_before':Epre[future.game_id],'next_game_elo_difference_after':Epost[future.game_id],'note':'Unrounded model state, not a new game prediction; no future Week7 results available yet.'}
frozen=json.load(open(R/'tools/nfl/week7_2026/game_predictions_raw.json'));p=next(x for x in frozen if x['game_id']==GID);assert p['model_total']==45.8 and p['raw_margin_home']==.12
inj=json.load(open(R/'tools/nfl/week7_2026/injury_forward_20261022_v5.json'));ip=next(x for x in inj['games'] if x['matchup']=='NE at CHI')
# Evaluate every settled frozen totals-ridge forward game from Weeks4-7, no cherry-picking Thursday.
rows=[];alias={'LA':'LA','LAR':'LA','WAS':'WAS','WSH':'WAS'};norm=lambda x:alias.get(x,x)
for w in [4,5,6,7]:
 if w==4:
  preds=json.load(open(R/'tools/model_nfl_v3_2/point_in_time/totals_week4_predictions.json'))
 else:preds=json.load(open(R/f'tools/nfl/week{w}_2026/game_predictions_raw.json'))
 for q in preds:
  aw,hm=q['event'].split(' at ') if w==4 else (q['away'],q['home']);match=g[(g.season==2026)&(g.week==w)&(g.home_team.map(norm)==norm(hm))&(g.away_team.map(norm)==norm(aw))];assert len(match)==1
  z=match.iloc[0]
  if pd.isna(z.home_score):continue
  actual=float(z.home_score+z.away_score);pred=q['model_total'];rows.append({'week':w,'game_id':z.game_id,'frozen_total':pred,'actual_total':actual,'signed_error_prediction_minus_actual':pred-actual,'absolute_error':abs(pred-actual)})
base=json.load(open(R/'tools/model_nfl_v3_2/point_in_time/totals_evaluation.json'))['train_mean']
def metrics(xs):
 errors=np.array([x['signed_error_prediction_minus_actual'] for x in xs]);return {'n':len(xs),'mae':float(abs(errors).mean()),'mean_signed_error_prediction_minus_actual':float(errors.mean()),'rmse':float(np.sqrt((errors**2).mean())),'train_mean_baseline_mae':float(np.mean([abs(base-x['actual_total']) for x in xs]))}
# Anytime-TD audit: every active NE/CHI board player, one Bernoulli observation each.
td=json.load(open(R/'week7_anytime_td.json'));scored={"D'Andre Swift","Rhamondre Stevenson","Luther Burden III","Colston Loveland","Drake Maye","Eli Raridon"};inactive={"Kyle Monangai","Romeo Doubs"}
tdrows=[x for x in td['rows'] if x['team'] in ('NE','CHI') and x['player'] not in inactive]
tdaudit=[{'player':x['player'],'pos':x['pos'],'model':x['model'],'scored':int(x['player'] in scored),'brier':round((x['model']-int(x['player'] in scored))**2,6)} for x in tdrows]
# Archived official weekly stats corroborate the scoring summary.
stats=pd.read_csv(P/'player_stats_asof_20261022.csv',low_memory=False);w7=stats[(stats.season==2026)&(stats.week==7)]
expect={"D'Andre Swift":(1,0),'Rhamondre Stevenson':(0,1),'Luther Burden III':(0,1),'Colston Loveland':(0,1),'Drake Maye':(1,0),'Eli Raridon':(0,1),'TreVeyon Henderson':(0,0),'DeMario Douglas':(0,0)}
for n,(ru,re) in expect.items():
 x=w7[w7.player_display_name==n].iloc[0];assert (int(x.rushing_tds),int(x.receiving_tds))==(ru,re),n
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
out={'generated_at':now,'game_id':GID,'final':'CHI 30, NE 24 (Final)','sources':{'games':'https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv (asset updated 2026-10-23T04:46:36Z)','player_stats':'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv (asset updated 2026-10-23T04:46:11Z)','espn_summary':'https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=401873010 (STATUS_FINAL, archived espn_final.json)'},
'misses':{'frozen_home_margin':{'prediction':p['raw_margin_home'],'actual':6,'absolute_error':5.88,'note':'Baseline picked a pure coin-flip game (PK, home win 50%); actual CHI by 6. One game.'},'injury_overlay_margin':{'prediction':ip['injury_adjusted_margin_home'],'actual':6,'absolute_error':4.9,'note':'Unproven overlay was closer this once; one game does not validate it. Weeks 5 and 6 favored the baseline.'},'frozen_total':{'prediction':p['model_total'],'actual':54,'signed_error_prediction_minus_actual':-8.2,'note':'Use frozen model_total 45.8, not the rounded 23-23 displayed scores (sum 46).'},'home_win_brier':0.25},
'totals_forward_record':metrics(rows),'totals_rows':rows,
'anytime_td_audit':{'players':len(tdaudit),'mean_brier':round(float(np.mean([x['brier'] for x in tdaudit])),6),'locked_test_reference':'Brier 0.184 vs 0.193 constant baseline, bootstrap intervals cross zero; research-only, not a validated edge','rows':tdaudit,'note':'Henderson and DeMario Douglas each appeared on two tickets; shared players across tickets are not independent observations. Monangai (Out) and Doubs (IR) excluded: zero participation, display-zeroed.'},
'team_state_assimilation':states,
'player_stats_assertions':'Week 7 rows archived and verified for all eight audited players (TD counts match the ESPN scoring summary). Tuesday Week-8 rebuild must fresh-fetch completed schedule/player inputs and include this game; no refit, no tuning from one game.',
'no_cause_asserted':'Injury/weather/play-calling causes for the misses are not established and none are invented.'}
(P/'learning_audit.json').write_text(json.dumps(out,indent=1)+'\n')
print('OK',out['totals_forward_record'])
