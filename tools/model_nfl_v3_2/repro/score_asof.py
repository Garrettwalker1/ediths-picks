#!/usr/bin/env python3
"""Fail-closed single-game scorer. Accepts independently sourced as-of feature rows.

Input schema example is described in README.md. Does not scrape, guess missing
features, mutate the public board, or use odds as model features.
"""
import argparse,datetime,hashlib,json,math
from pathlib import Path
R=Path(__file__).resolve().parent
class InputError(ValueError):pass
def score(data,artifact,expected_baseline=None,tolerance=1e-7):
    feats=artifact['feature_order'];asof=datetime.datetime.fromisoformat(data['as_of'].replace('Z','+00:00'))
    if asof.tzinfo is None:raise InputError('as_of must have a timezone')
    kickoff=datetime.datetime.fromisoformat(data['kickoff'].replace('Z','+00:00'))
    if kickoff.tzinfo is None or asof>kickoff:raise InputError('as_of must precede timezone-aware kickoff')
    f=data['features'];unknown=set(f)-set(feats);missing=set(feats)-set(f)
    if unknown or missing:raise InputError(f'feature mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}')
    provenance=data['provenance'];dates=[]
    for name in feats:
        value=f[name]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise InputError(f'{name} lacks finite numeric input')
        proof=provenance.get(name,{})
        if not proof.get('source_url') or not proof.get('observed_at') or not proof.get('method'):
            raise InputError(f'{name} lacks source URL, observed_at, or method')
        date=datetime.datetime.fromisoformat(proof['observed_at'].replace('Z','+00:00'))
        if date.tzinfo is None or date>asof:raise InputError(f'{name} has future or timezone-naive evidence')
        dates.append(date)
    pred=artifact['raw_intercept']+sum(artifact['raw_coefficients'][name]*f[name] for name in feats)
    result={'game_id':data['game_id'],'as_of':data['as_of'],'artifact_sha256':hashlib.sha256((R/'v32b_fit_2010_2025.json').read_bytes()).hexdigest(),'home_margin_raw':pred,'source_count':len(set(provenance[n]['source_url'] for n in feats)),'caveat':'Descriptive, historically worse than closing spread. No moneyline edge implied.'}
    if expected_baseline is not None:
        diff=pred-expected_baseline
        result['baseline_delta']=diff
        if abs(diff)>tolerance:raise InputError(f'baseline mismatch: scored {pred:.10f}, archived {expected_baseline:.10f}, delta {diff:+.10f}, tolerance {tolerance}')
        result['baseline_verified']=True
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('asof_json',type=Path);p.add_argument('--baseline',type=float);p.add_argument('--tolerance',type=float,default=1e-7);a=p.parse_args()
    try:print(json.dumps(score(json.loads(a.asof_json.read_text()),json.loads((R/'v32b_fit_2010_2025.json').read_text()),a.baseline,a.tolerance),indent=2))
    except (InputError,KeyError,ValueError) as e:p.error(str(e))
