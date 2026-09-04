#!/usr/bin/env python3
"""E.D.I.T.H. model v3 - training dataset builder.
Assembles NFL player-game training table 2020-2025 REG from nflverse weekly stats.
Features: strictly shifted rolling player form, team QB-play rolling, opponent defensive ratings.
NO book/market data anywhere in inputs. Point-in-time only.
Outputs: /tmp/training/out/player_games_features.parquet
"""
import numpy as np, pandas as pd
from pathlib import Path

CACHE=Path('/tmp/training/cache'); OUT=Path('/tmp/training/out'); OUT.mkdir(exist_ok=True)
SEASONS=(2020,2021,2022,2023,2024,2025)
POS=('QB','RB','WR','TE')

COLS=['player_id','player_display_name','position','team','season','week','season_type','game_id','opponent_team',
 'attempts','completions','passing_yards','passing_tds','passing_interceptions','sacks_suffered','passing_epa','passing_cpoe',
 'carries','rushing_yards','rushing_tds','targets','receptions','receiving_yards','receiving_tds',
 'target_share','air_yards_share','wopr']
d=pd.concat([pd.read_csv(CACHE/f'stats_player_week_{y}.csv',usecols=lambda c:c in COLS,low_memory=False) for y in SEASONS],ignore_index=True)
d=d[(d.season_type=='REG')&d.position.isin(POS)].copy()
d['games_played']=1
print('rows',len(d))

g=d.groupby('player_id',group_keys=False)
d=d.sort_values(['player_id','season','week']).copy(); g=d.groupby('player_id',group_keys=False)
ROLL=['attempts','completions','passing_yards','passing_tds','passing_interceptions','passing_epa','passing_cpoe',
 'carries','rushing_yards','rushing_tds','targets','receptions','receiving_yards','receiving_tds',
 'target_share','air_yards_share','wopr']
for c in ROLL:
    d[f'{c}_r6']=g[c].transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
d['prior_games']=g['games_played'].transform(lambda x:x.shift().rolling(100,min_periods=1).count())

# --- team QB play (shifted): team passing aggregates per game, rolled by team ---
qb=d.groupby(['team','season','week','game_id'],as_index=False).agg(
    qb_att=('attempts','sum'),qb_yards=('passing_yards','sum'),qb_tds=('passing_tds','sum'),
    qb_epa_sum=('passing_epa','sum'),qb_int=('passing_interceptions','sum'))
qb['qb_epa_per_att']=qb.qb_epa_sum/qb.qb_att.replace(0,np.nan)
qb=qb.sort_values(['team','season','week'])
gq=qb.groupby('team',group_keys=False)
for c in ['qb_att','qb_yards','qb_tds','qb_epa_per_att','qb_int']:
    qb[c+'_r6']=gq[c].transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
d=d.merge(qb[['game_id','team','qb_att_r6','qb_yards_r6','qb_tds_r6','qb_epa_per_att_r6','qb_int_r6']],on=['game_id','team'],how='left')

# --- defensive ratings (shifted): what each team ALLOWED, rolled ---
# offense rows attributed to opponent_team; build allowed aggregates per defending team per game
defg=d.groupby(['opponent_team','season','week','game_id'],as_index=False).agg(
    al_pass_yds=('passing_yards','sum'),al_pass_att=('attempts','sum'),al_pass_tds=('passing_tds','sum'),
    al_rush_yds=('rushing_yards','sum'),al_carries=('carries','sum'),al_rush_tds=('rushing_tds','sum'),
    al_rec_yds=('receiving_yards','sum'),al_targets=('targets','sum'),al_rec_tds=('receiving_tds','sum'))
defg['al_ypa']=defg.al_pass_yds/defg.al_pass_att.replace(0,np.nan)
defg['al_ypc']=defg.al_rush_yds/defg.al_carries.replace(0,np.nan)
defg['al_ypt']=defg.al_rec_yds/defg.al_targets.replace(0,np.nan)
defg['al_tds']=defg.al_pass_tds+defg.al_rush_tds
defg=defg.sort_values(['opponent_team','season','week'])
gd=defg.groupby('opponent_team',group_keys=False)
for c in ['al_pass_yds','al_rush_yds','al_rec_yds','al_ypa','al_ypc','al_ypt','al_tds','al_pass_tds','al_rush_tds','al_rec_tds']:
    defg[c+'_r6']=gd[c].transform(lambda x:x.shift().rolling(6,min_periods=3).mean())
keep=['game_id','opponent_team']+[c+'_r6' for c in ['al_pass_yds','al_rush_yds','al_rec_yds','al_ypa','al_ypc','al_ypt','al_tds','al_pass_tds','al_rush_tds','al_rec_tds']]
d=d.merge(defg[keep],on=['game_id','opponent_team'],how='left')

# home/away from schedules (schedule info, not market data)
games=pd.read_csv(CACHE/'games.csv',usecols=['game_id','game_type','home_team','away_team','season'])
games=games[(games.game_type=='REG')&(games.season.isin(SEASONS))]
d=d.merge(games[['game_id','home_team']],on='game_id',how='left')
d['is_home']=(d.team==d.home_team).astype(int)

d['any_td']=((d.rushing_tds.fillna(0)+d.receiving_tds.fillna(0))>0).astype(int)
d.to_parquet(OUT/'player_games_features.parquet')
print('saved', OUT/'player_games_features.parquet', len(d))
print(d.groupby('season').size().to_dict())
print('feature null share (r6 cols):')
print(d[[c for c in d.columns if c.endswith('_r6')]].isna().mean().round(3).to_dict())
