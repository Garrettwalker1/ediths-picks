#!/usr/bin/env python3
"""Diagnostic evaluation of the frozen Oct15 Week6 injury cohort (injury_forward_20261015.json, sha256 a93322e44be8beda5704dc54cdf19a33a8dcc079735a8c3e272ddf8c7a695319) against Week 6 finals. Never refits or edits the cohort. Not a promotion test (tools/nfl/injury_v2/FORWARD_PLAN.md: >=100 untouched forecasts needed). BUF at LV and WSH at SF stay withheld: BUF/SF/WSH injury reports were absent at freeze."""
import json,pathlib,numpy as np,hashlib
R=pathlib.Path(__file__).resolve().parents[4]
f=R/'tools/nfl/week6_2026/refresh_20261015/injury_forward_20261015.json';d=json.load(open(f))
g=json.load(open(R/'tools/nfl/week6_2026/grade/week6_grade.json'))['rows'];fin={r['event'].replace(' at LAR',' at LA'):r for r in g}
rows=[]
for x in d['games']:
    if x['matchup'] in ('BUF at LV','WSH at SF'):continue  # withheld at freeze: missing BUF/SF/WSH reports
    r=fin[x['matchup']];act=r['actual_margin_home'];b=x['baseline_margin_home'];e=x['injury_adjusted_margin_home']
    rows.append((x['matchup'],b,e,act,abs(b-act),abs(e-act),len(x['coverage_missing']),len(x['conflicts'])))
assert len(rows)==12
b=np.array([r[4] for r in rows]);e=np.array([r[5] for r in rows]);dl=e-b
rng=np.random.default_rng(261020);bs=[rng.choice(dl,len(dl)).mean() for _ in range(10000)]
out=dict(cohort=d['model_version'],frozen_file_sha256=hashlib.sha256(open(f,'rb').read()).hexdigest(),n=len(rows),withheld=['BUF at LV','WSH at SF'],withheld_reason='BUF/SF/WSH injury reports absent at freeze (explicit at freeze time)',baseline_mae=round(b.mean(),3),experiment_mae=round(e.mean(),3),mean_paired_delta_exp_minus_base=round(dl.mean(),4),paired_bootstrap_95=[round(float(np.percentile(bs,2.5)),3),round(float(np.percentile(bs,97.5)),3)],bootstrap='10000 game resamples, seed 261020',experiment_better_games=int((dl<-1e-9).sum()),baseline_better_games=int((dl>1e-9).sum()),equal_games=int((abs(dl)<=1e-9).sum()),games_with_missing_role_players=sum(1 for r in rows if r[6]>0),conflicts=sum(r[7] for r in rows),
 rows=[dict(game=r[0],baseline=r[1],experiment=r[2],actual_home_margin=r[3],baseline_abs_err=round(r[4],3),experiment_abs_err=round(r[5],3),missing_role=r[6]) for r in rows],
 note='Diagnostic only, one week, 12 numerical games. No promotion, no refit. Research gate needs >=100 untouched forecasts. Week5 diagnostic was baseline 9.257 vs experiment 9.370; preserve both weeks as separate immutable cohorts.')
(R/'tools/nfl/week6_2026/refresh_20261015/forward_week6_result.json').write_text(json.dumps(out,indent=2)+'\n')
print({k:v for k,v in out.items() if k!='rows'})
