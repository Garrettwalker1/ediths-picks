#!/usr/bin/env python3
"""Diagnostic evaluation of the frozen cohort injury-experiment-20261007-v1 against Week 5 finals. Never refits or edits the cohort. Not a promotion test (FORWARD_PLAN.md: >=100 forecasts needed)."""
import json,pathlib,numpy as np,hashlib
R=pathlib.Path(__file__).resolve().parents[3]
f=R/'tools/nfl/injury_v2/forward_predictions_20261007.json';d=json.load(open(f))
g=json.load(open(R/'tools/nfl/week5_2026/grade/week5_grade.json'))['rows'];fin={r['event'].replace(' at LAR',' at LA'):r for r in g}
rows=[]
for x in d['games']:
    r=fin[x['matchup']];act=r['actual_margin_home'];b=x['baseline_margin_home'];e=x['injury_adjusted_margin_home']
    rows.append((x['matchup'],b,e,act,abs(b-act),abs(e-act),len(x['coverage_missing']),len(x['conflicts'])))
b=np.array([r[4] for r in rows]);e=np.array([r[5] for r in rows]);dl=e-b
rng=np.random.default_rng(261013);bs=[rng.choice(dl,len(dl)).mean() for _ in range(10000)]
out=dict(cohort=d['model_version'],frozen_file_sha256=hashlib.sha256(open(f,'rb').read()).hexdigest(),n=len(rows),baseline_mae=round(b.mean(),3),experiment_mae=round(e.mean(),3),mean_paired_delta_exp_minus_base=round(dl.mean(),4),paired_bootstrap_95=[round(float(np.percentile(bs,2.5)),3),round(float(np.percentile(bs,97.5)),3)],bootstrap='10000 game resamples, seed 261013',experiment_better_games=int((dl<-1e-9).sum()),baseline_better_games=int((dl>1e-9).sum()),equal_games=int((abs(dl)<=1e-9).sum()),games_with_missing_role_players=sum(1 for r in rows if r[6]>0),conflicts=sum(r[7] for r in rows),
 rows=[dict(game=r[0],baseline=r[1],experiment=r[2],actual_home_margin=r[3],baseline_abs_err=round(r[4],3),experiment_abs_err=round(r[5],3),missing_role=r[6]) for r in rows],
 note='Diagnostic only, one week, 15 games. No promotion, no refit. Paired interval crosses zero unless stated otherwise; research gate needs >=100 untouched forecasts.')
(R/'tools/nfl/injury_v2/forward_week5_result.json').write_text(json.dumps(out,indent=2)+'\n')
print({k:v for k,v in out.items() if k!='rows'})
