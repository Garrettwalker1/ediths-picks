#!/usr/bin/env python3
"""Leakage invariants against complete historical nflverse inputs."""
from pathlib import Path
import pandas as pd
from pandas.testing import assert_frame_equal
from build_frame import build,FEATURES,SOURCES
NEEDED=['season','season_type','week','team','opponent_team','passing_yards','rushing_yards','passing_interceptions','fumbles_lost_total','sacks_suffered','attempts','completions','passing_tds','def_sacks','def_interceptions','fumble_recovery_opp']
games=pd.read_csv(SOURCES/'games.csv',low_memory=False);stat=pd.concat([pd.read_csv(f,usecols=NEEDED,low_memory=False) for f in sorted(SOURCES.glob('spw_*.csv'))],ignore_index=True)
# Keep recent complete seasons to exercise year priors and first games.
games=games[games.season.between(2023,2025)].copy();stat=stat[stat.season.between(2022,2025)].copy()
base=build(games,stat).set_index('game_id').sort_index();assert len(base)==816
# Target-game statistics are unknown before it kicks off. Poison them, and
# assert this game's features do not move; subsequent games may move.
target='2024_08_BAL_CLE';row=stat[(stat.season==2024)&(stat.week==8)&(stat.team=='BAL')];assert len(row)>0
poisoned=stat.copy();poisoned.loc[row.index,'passing_yards']=poisoned.loc[row.index,'passing_yards'].fillna(0)+1000000
altered=build(games,poisoned).set_index('game_id').sort_index();assert_frame_equal(base.loc[[target],FEATURES],altered.loc[[target],FEATURES]);assert not base.loc[base.season==2024,FEATURES].equals(altered.loc[altered.season==2024,FEATURES])
# Future-season data cannot move 2023 features.
removed=build(games[games.season==2023],stat[stat.season<=2023]).set_index('game_id').sort_index();assert_frame_equal(base.loc[removed.index,FEATURES],removed[FEATURES])
# Early games in a new season may use last year's completed priors, not their
# own full-season statistics. The target week-1 stats are never predictors.
first='2024_01_BAL_KC';assert first in base.index
poisoned=stat.copy();ix=poisoned[(poisoned.season==2024)&(poisoned.week==1)&(poisoned.team=='BAL')].index;assert len(ix)>0;poisoned.loc[ix,'passing_yards']=1000000
altered=build(games,poisoned).set_index('game_id').sort_index();assert_frame_equal(base.loc[[first],FEATURES],altered.loc[[first],FEATURES])
print('Chronology invariants pass: target-game poison, later-season truncation, week-1 poison')
