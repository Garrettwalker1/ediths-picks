import pandas as pd, numpy as np
rows = []
for y in range(2010, 2026):
    p = pd.read_parquet(f'pbp/pbp_{y}.parquet', columns=['game_id','posteam','defteam','play_type','epa','success','season','week'])
    p = p[p.play_type.isin(['pass','run']) & p.epa.notna()]
    off = p.groupby(['game_id','posteam'],as_index=False).agg(
        off_epa_pp=('epa','mean'), off_success=('success','mean'), off_plays=('epa','size'),
        off_pass_epa_pp=('epa', lambda x: x[p.loc[x.index,'play_type']=='pass'].mean()),
        off_rush_epa_pp=('epa', lambda x: x[p.loc[x.index,'play_type']=='run'].mean()))
    off = off.rename(columns={'posteam':'team'})
    dfn = p.groupby(['game_id','defteam'],as_index=False).agg(
        def_epa_pp=('epa','mean'), def_success=('success','mean'))
    dfn = dfn.rename(columns={'defteam':'team'})
    m = off.merge(dfn, on=['game_id','team'])
    g = pd.read_parquet(f'pbp/pbp_{y}.parquet', columns=['game_id','season','week']).drop_duplicates('game_id')
    m = m.merge(g, on='game_id')
    rows.append(m)
    print(y, len(m))
epa = pd.concat(rows, ignore_index=True)
epa.to_parquet('out/team_game_epa.parquet')
print('saved', len(epa))
