import numpy as np,pandas as pd
COLS=['player_id','player_display_name','position','team','season','week','season_type','game_id','opponent_team','carries','rushing_yards','rushing_tds','targets','receptions','receiving_yards','receiving_tds','receiving_air_yards','target_share','air_yards_share','wopr','fantasy_points_ppr']
BASE_FEATURES=['receiving_yards','targets','receptions','receiving_air_yards','target_share','air_yards_share','wopr','rushing_yards','carries','receiving_tds','rushing_tds','fantasy_points_ppr']
RF=['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receptions_r3','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3']
QF=['rushing_yards_r3','rushing_yards_r6','carries_r3','carries_r6']
REPF=['receptions_r3','targets_r3','targets_r6']
TDF=['receiving_tds_r6','rushing_tds_r6','targets_r3','target_share_r3','receiving_air_yards_r3','carries_r3','receiving_yards_r3','rushing_yards_r3']
BF=['receiving_yards_r3','receiving_yards_r6','targets_r3','targets_r6','receiving_air_yards_r3','target_share_r3','air_yards_share_r3','wopr_r3']
def pred(m,fs,z):return float(max(0,m.predict(pd.DataFrame([{f:z[f] for f in fs}]))[0]))
def prob(m,fs,z):return float(m.predict_proba(pd.DataFrame([{f:z[f] for f in fs}]))[0,1])
