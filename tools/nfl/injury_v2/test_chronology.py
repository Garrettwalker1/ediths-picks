import pandas as pd,numpy as np
from evaluate import load_features
snaps=pd.DataFrame([dict(season=s,week=w,team='KC',player='Test QB',game_type='REG',offense_pct=a,defense_pct=0) for s,w,a in [(2024,18,.9),(2025,1,.7),(2025,2,.8),(2025,3,.99),(2025,4,1)]])
inj=pd.DataFrame([dict(season=2025,week=w,team='KC',full_name='Test QB',game_type='REG',position='QB',report_status='Out',practice_status='Did Not Participate In Practice') for w in [1,2,3]])
a,_=load_features(snaps,inj)
assert np.allclose(a.QB_absent,[.9,.7,.75]),a
# Poison target-week and future-week snaps; target Week 3 must not change.
poison=snaps.copy();poison.loc[(poison.season==2025)&(poison.week>=3),'offense_pct']=99
b,_=load_features(poison,inj);assert np.allclose(a.QB_absent,b.QB_absent)
# Truncate all target/future rows; identical target Week 3.
c,_=load_features(snaps[~((snaps.season==2025)&(snaps.week>=3))],inj);assert np.allclose(a.QB_absent,c.QB_absent)
# No prior history means zero weight, never first future/same-game snap fallback.
d,cov=load_features(snaps[snaps.season==2025],inj);assert d.QB_absent.iloc[0]==0 and cov['weights_missing']==1
print('PASS: strictly earlier snaps, previous-year-only fallback, poison/truncation invariance, first-year missing policy')
