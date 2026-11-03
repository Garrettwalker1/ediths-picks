import importlib.util,pathlib,json,pandas as pd,numpy as np
R=pathlib.Path('/tmp/edith-oct28');P=pathlib.Path('/tmp/projection-repair');sp=importlib.util.spec_from_file_location('old',R/'tools/3-generate_player_projections-157ce8c7.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
raw=pd.concat([pd.read_csv(R/f'tools/player_projection_cache/stats_{y}.csv',usecols=m.COLS,low_memory=False).query("season_type=='REG'") for y in [2023,2024,2025]],ignore_index=True);d=m.roll(raw);r=d[d.position.isin(['WR','TE','RB'])&d.receiving_yards_r3.notna()].copy();rr=d[d.position.isin(['RB','QB'])&d.rushing_yards_r3.notna()];td=r.copy();td['y']=((td.receiving_tds+td.rushing_tds)>0).astype(int);boom=r[(r.targets_r3>=2)&r.receiving_yards_r6.notna()].copy();boom['y']=((boom.receiving_yards>=80)&(boom.receiving_yards>=1.5*boom.receiving_yards_r6.clip(lower=20))).astype(int);bust=r[(r.targets_r3>=4)&r.receiving_yards_r6.notna()].copy();bust['bust']=((bust.receiving_yards<30)&(bust.receiving_yards<.5*bust.receiving_yards_r6)).astype(int)
models={'recv':m.lin(r,m.RF,'receiving_yards'),'rush':m.lin(rr,m.QF,'rushing_yards'),'recs':m.lin(r,m.REPF,'receptions'),'td':m.logit(td,m.TDF,'y'),'boom':m.logit(boom,m.RF,'y'),'bust':m.logit(bust,m.BF,'bust')};features={'recv':m.RF,'rush':m.QF,'recs':m.REPF,'td':m.TDF,'boom':m.RF,'bust':m.BF}
cur=pd.read_csv(R/'tools/nfl/week9_2026/player_stats_2026.csv',usecols=m.COLS,low_memory=False);cur=cur[(cur.season_type=='REG')&(cur.week<=6)];both=pd.concat([raw,cur]);old=json.load(open(R/'player_projections.json'));diff=[]
for x in old['players']:
 g=both[both.player_id.eq(x['player_id'])].sort_values(['season','week']);z=g.iloc[-1].copy()
 for c in m.BASE_FEATURES:
  for n in [3,6]:z[f'{c}_r{n}']=g[c].tail(n).mean()
 vals={'recv':round(m.pred(models['recv'],m.RF,z),1),'rush':round(m.pred(models['rush'],m.QF,z),1),'recs':round(m.pred(models['recs'],m.REPF,z),1),'td':round(m.prob(models['td'],m.TDF,z),3),'boom':round(m.prob(models['boom'],m.RF,z),3),'bust':round(m.prob(models['bust'],m.BF,z),3) if z.targets_r3>=4 else None}
 orig={'recv':x['receiving_yards']['median'],'rush':x['rushing_yards']['median'],'recs':x['receptions']['median'],'td':x['anytime_td_probability'],'boom':x['boom_probability'],'bust':x['bust_probability']};
 if vals!=orig:diff.append({'player':x['player'],'original':orig,'reproduced':vals,'last_season':int(g.season.iloc[-1]),'last_week':int(g.week.iloc[-1])})
print('ALL',len(old['players']),'DIFF',len(diff));print(json.dumps(diff[:5],indent=2));(P/'reproduction.json').write_text(json.dumps({'players':len(old['players']),'differences':diff},indent=2))
import joblib
joblib.dump({'models':models,'features':features},P/'locked-models.joblib')
