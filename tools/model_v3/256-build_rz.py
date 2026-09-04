#!/usr/bin/env python3
"""Build red-zone/goal-line opportunity aggregates per player-game from nflverse pbp 2020-2025."""
import pandas as pd, numpy as np
from pathlib import Path
CACHE=Path('/tmp/training/cache'); OUT=Path('/tmp/training/out')
PCOLS=['game_id','season','week','season_type','posteam','yardline_100','play_type','rusher_player_id','receiver_player_id']
rz=[]
for y in (2020,2021,2022,2023,2024,2025):
    p=pd.read_parquet(CACHE/f'pbp_{y}.parquet',columns=PCOLS)
    p=p[(p.season_type=='REG')&p.posteam.notna()]
    for typ,pid in [('carry','rusher_player_id'),('target','receiver_player_id')]:
        q=p[p[pid].notna()&p.play_type.eq('run' if typ=='carry' else 'pass')].copy()
        q['player_id']=q[pid]
        q['rz']=q.yardline_100.le(20).astype(int); q['gl']=q.yardline_100.le(5).astype(int)
        a=q.groupby(['game_id','player_id']).agg(**{f'{typ}_rz':('rz','sum'),f'{typ}_gl':('gl','sum')}).reset_index()
        rz.append(a)
    print(y,'done')
r=pd.concat(rz,ignore_index=True).groupby(['game_id','player_id'],as_index=False).sum(numeric_only=True)
r.to_parquet(OUT/'rzgl.parquet'); print('saved',len(r))
