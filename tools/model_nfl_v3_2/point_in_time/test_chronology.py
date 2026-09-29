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
# As-of snapshots must disregard same-date finals even if the revised input
# carries them, and must never increment games-played for later fixtures.
# Synthetic date is intentionally just before Week 8; prior weeks are complete.
asof_games=games.copy()
assert (asof_games.game_id==target).any()
cutoff=asof_games.loc[asof_games.game_id==target,'gameday'].iloc[0]
pre=build(asof_games,stat,as_of=cutoff).set_index('game_id').sort_index()
assert pd.isna(pre.loc[target,'margin'])
assert_frame_equal(base.loc[[target],FEATURES],pre.loc[[target],FEATURES])
poisoned_games=asof_games.copy()
poisoned_games.loc[poisoned_games.gameday>=cutoff,['home_score','away_score']]=1000000
pre_poison=build(poisoned_games,stat,as_of=cutoff).set_index('game_id').sort_index()
assert_frame_equal(pre[FEATURES],pre_poison[FEATURES])
# Removing intervening unplayed schedule rows cannot alter later game form.
future_row=pre[(pre.season==2024)&(pre.week==10)].index
without=build(asof_games[~((asof_games.season==2024)&(asof_games.gameday>=cutoff)&(asof_games.week.isin([8,9])))],stat,as_of=cutoff).set_index('game_id').sort_index()
assert_frame_equal(pre.loc[future_row,FEATURES],without.loc[future_row,FEATURES])
print('Chronology invariants pass: target-game poison, later-season truncation, week-1 poison, as-of same-date poison, unplayed schedule removal')
