"""Research-only past-play opponent adjustment, never a game forecast.
Weighted ridge on per-game success rates, with offensive/defensive team effects.
Counts, rather than averages of game percentages, determine weights.
No win/loss labels, betting lines, final margins or future games used.
"""
import collections,datetime,gzip,json,pathlib
import numpy as np
O=pathlib.Path('/tmp/deep-research/cfb-rework')
def adjust(rows,cutoff,penalty=20.):
 rows=[r for r in rows if r['date'][:10]<cutoff]
 assert rows
 names=sorted({r['offense_id']for r in rows}|{r['defense_id']for r in rows});ix={k:i for i,k in enumerate(names)};n=len(names);counts=collections.defaultdict(lambda:[0,0]);labels={}
 for r in rows:
  k=(r['event_id'],r['offense_id'],r['defense_id']);counts[k][0]+=r['success'];counts[k][1]+=1;labels[r['offense_id']]=r['offense'];labels[r['defense_id']]=r['defense']
 X=np.zeros((len(counts),2*n+1));y=np.zeros(len(counts));weight=np.zeros(len(counts))
 for i,((eid,off,de),(s,c)) in enumerate(sorted(counts.items())):X[i,0]=1;X[i,1+ix[off]]=1;X[i,1+n+ix[de]]=1;y[i]=s/c;weight[i]=c
 # Penalize team effects, not intercept. Defense effect >0 means more success allowed.
 reg=np.eye(2*n+1)*penalty;reg[0,0]=0
 beta=np.linalg.solve(X.T@(weight[:,None]*X)+reg,X.T@(weight*y))
 assert np.isfinite(beta).all()
 return {'cutoff_exclusive':cutoff,'status':'Unvalidated success-rate context only; no points conversion or game predictions','penalty_unvalidated':penalty,'plays':len(rows),'game_offense_rows':len(counts),'league_success_rate':float(beta[0]),'teams':[{'team_id':t,'team':labels[t],'offense_effect':float(beta[1+ix[t]]),'defense_success_allowed_effect':float(beta[1+n+ix[t]])}for t in names]}
def main():
 rows=[json.loads(x)for x in gzip.open(O/'raw_success_plays.jsonl.gz','rt')]
 d=adjust(rows,'2026-11-23');(O/'opponent_success_context.json').write_text(json.dumps(d,indent=2))
 # Chronology invariant: later injected observations do not affect earlier fit.
 before=adjust(rows,'2026-10-01');fake=dict(rows[0],date='2099-01-01T00:00Z',success=1-rows[0]['success']);after=adjust(rows+[fake],'2026-10-01');assert before==after
 print(json.dumps({k:v for k,v in d.items()if k!='teams'},indent=2));print('teams',len(d['teams']),'future_injection_invariance_passed',True)
if __name__=='__main__':main()
