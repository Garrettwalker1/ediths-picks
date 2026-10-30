import pandas as pd,numpy as np,json
from pathlib import Path
P=Path('/tmp/prop-matchup/out');d=json.load(open(P/'diagnostics.json'));rng=np.random.default_rng(1029)
for target in d['targets']:
 a=pd.read_pickle(P/f'{target}_paired.pkl');a=a[a.season.eq(2025)];a['delta']=abs(a.usage_matchup-a[target])-abs(a.old_formula-a[target]);g=a.groupby('game_id').agg(s=('delta','sum'),n=('delta','size'));v=[]
 for _ in range(2000):
  z=g.iloc[rng.integers(0,len(g),len(g))];v.append(z.s.sum()/z.n.sum())
 ci=np.quantile(v,[.025,.975]).tolist();d['targets'][target]['seen2025_paired_game_MAE_delta_CI95']=ci;print(target,ci)
(P/'diagnostics.json').write_text(json.dumps(d,indent=2)+'\n')
