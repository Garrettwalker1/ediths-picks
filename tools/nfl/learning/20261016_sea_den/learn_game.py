"""Postgame audit and fixed-rule state assimilation. No fitting or forecast rewriting.
Run from repo root: python3 tools/nfl/learning/20261016_sea_den/learn_game.py
"""
import pathlib,sys,json,hashlib,datetime,importlib.util
import pandas as pd,numpy as np
P=pathlib.Path(__file__).resolve().parent;R=P.parents[3]
sys.path.insert(0,str(R/'tools/model_nfl_v3_2/point_in_time'));import elo_candidate as E,totals_candidate as T
GID='2026_06_SEA_DEN';g=pd.read_csv(P/'games_asof_20261016.csv',low_memory=False);g=g[g.game_type.isin(['REG','WC','DIV','CON','SB'])].copy();r=g[g.game_id==GID].iloc[0];assert (r.home_score,r.away_score)==(17,14)
# Nothing at or after current day can be learned; future and target outcomes cannot enter pregame features.
assert g[(g.season==2026)&(g.gameday>='2026-10-16')].home_score.isna().all()
pre=g.copy();pre.loc[pre.game_id==GID,['home_score','away_score']]=np.nan
Epre=E.diffs(pre);Epost=E.diffs(g);Fpre=T.feats(pre[pre.game_type=='REG']);Fpost=T.feats(g[g.game_type=='REG'])
assert Epre[GID]==Epost[GID]
a=Fpre[Fpre.game_id==GID].iloc[0];b=Fpost[Fpost.game_id==GID].iloc[0];assert np.allclose(a[T.COLS].astype(float),b[T.COLS].astype(float))
# Audit the already-declared next-six-game-half-life update, not a new fitted rule.
weight=1-.5**(1/6);states={}
for team,loc,score,allow in [('SEA','a',14,17),('DEN','h',17,14)]:
 pf,pa=float(b[loc+'pf']),float(b[loc+'pa']);future=g[(g.gameday>r.gameday)&((g.home_team==team)|(g.away_team==team))].sort_values(['gameday','game_id']).iloc[0];f0=Fpre[Fpre.game_id==future.game_id].iloc[0];f1=Fpost[Fpost.game_id==future.game_id].iloc[0];prefix='h' if future.home_team==team else 'a';newpf=pf+weight*(score-pf);newpa=pa+weight*(allow-pa)
 assert np.isclose(newpf,f1[prefix+'pf']) and np.isclose(newpa,f1[prefix+'pa'])
 assert not np.isclose(Epre[future.game_id],Epost[future.game_id])
 states[team]={'last_completed_game':GID,'next_game_id':future.game_id,'points_for_before':pf,'points_for_after':newpf,'points_against_before':pa,'points_against_after':newpa,'next_game_elo_difference_before':Epre[future.game_id],'next_game_elo_difference_after':Epost[future.game_id],'note':'Unrounded model state, not a new game prediction; no future Week6 results available yet.'}
frozen=json.load(open(R/'tools/nfl/week6_2026/game_predictions_raw.json'));p=next(x for x in frozen if x['game_id']==GID);assert p['model_total']==44.5 and p['raw_margin_home']==-.71
inj=json.load(open(R/'tools/nfl/week6_2026/refresh_20261015/injury_forward_20261015.json'));ip=next(x for x in inj['games'] if x['matchup']=='SEA at DEN')
# Evaluate every settled frozen totals-ridge forward game from Weeks4,5,6, no cherry-picking Thursday.
rows=[];alias={'LA':'LA','LAR':'LA','WAS':'WAS','WSH':'WAS'};norm=lambda x:alias.get(x,x)
for w in [4,5,6]:
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
# Same established player latest_rows rolling rule, no parameter refit or current-week rerender.
spec=importlib.util.spec_from_file_location('player_weekly',R/'tools/nfl/week5_2026/players/generate_players_w5.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
stats=pd.read_csv(P/'player_stats_asof_20261016.csv',low_memory=False);jsn=pd.concat([pd.read_csv(P/'jsn_2025_prior_history.csv'),stats[stats.player_id=='00-0038543']],ignore_index=True);jsn=jsn[jsn.season_type=='REG'].copy();assert jsn[(jsn.season==2026)&(jsn.week==6)].iloc[0].receiving_tds==0
bef=M.latest_rows(jsn[(jsn.season<2026)|(jsn.week<6)]);aft=M.latest_rows(jsn[(jsn.season<2026)|(jsn.week<=6)]);fields=['receiving_yards_r3','receiving_yards_r6','targets_r3','receiving_tds_r6','rushing_tds_r6'];playerstate={k:{'before':float(bef.iloc[0][k]),'after':float(aft.iloc[0][k])} for k in fields};assert playerstate['targets_r3']['before']!=playerstate['targets_r3']['after']
prob=next(x['anytime_td_probability'] for x in json.load(open(R/'player_projections.json'))['players'] if x['player']=='Jaxon Smith-Njigba');assert prob==.558
report={'as_of':'2026-10-16','owner_request':'Just need to have the model learn from this game','status':'Final assimilated into fixed-rule next-game state and prospective error checks; no fit/hyperparameter/promotion changes','game_id':GID,'final':{'away':14,'home':17,'total':31,'overtime':True},'frozen_forecast_errors':{'model_total':44.5,'actual_total':31,'total_overprediction':13.5,'model_margin_home':-.71,'actual_margin_home':3,'margin_absolute_error':3.71,'baseline_winner_correct':False,'displayed_score':'SEA23-DEN22','score_errors':{'SEA':9,'DEN':5},'frozen_injury_experiment_margin_home':ip['injury_adjusted_margin_home'],'injury_absolute_error':abs(3-ip['injury_adjusted_margin_home']),'home_win_probability':.472,'home_win_brier':(1-.472)**2},'total_forward_diagnostic':{'before_this_game':metrics([x for x in rows if x['game_id']!=GID]),'including_this_game':metrics(rows),'rows':rows,'interpretation':'Descriptive small prospective sample. No calibration slope/intercept or feature weights selected on this result; no claim of resolved miscalibration or cause.'},'learned_team_state_unrounded':states,'learned_player_state_unrounded':playerstate,'td_observation':{'player':'Jaxon Smith-Njigba','forecast_probability':prob,'outcome':0,'brier':prob**2,'receptions':12,'targets':16,'receiving_yards':134,'rushing_tds':0,'receiving_tds':0,'note':'One failed TD observation, not three independent misses. All3 tickets share JSN exposure; no calibrated joint SGP probability existed. Receiving opportunity was substantial; a TD miss alone does not establish a usage failure or causal diagnosis.'},'chronology_tests':{'same_game_pregame_elo_unchanged':True,'same_game_pregame_totals_features_unchanged':True,'future_team_state_updated':True,'fixed_player_rolling_rule_updates':True},'limits':['No attribution to injuries, weather, red-zone luck or play calling without a separate tested causal analysis.','One game cannot calibrate a TD probability or justify model promotion.','All pregame predictions, current board and immutable injury cohorts remain frozen; future Week7 board waits for remaining Week6 results.','Book prices and three ticket outcomes are evaluation context only, never score-state inputs.'],'sources':['https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv','https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv','https://www.espn.com/nfl/boxscore/_/gameId/401872995','https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv']}
(P/'learning_audit.json').write_text(json.dumps(report,indent=2)+'\n');(P/'source_manifest.json').write_text(json.dumps({'files':{str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in P.iterdir() if x.is_file() and x.name!='source_manifest.json'}},indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['frozen_forecast_errors','learned_team_state_unrounded','learned_player_state_unrounded','chronology_tests']},indent=2));print('Totals sample',report['total_forward_diagnostic']['before_this_game'],report['total_forward_diagnostic']['including_this_game'])
