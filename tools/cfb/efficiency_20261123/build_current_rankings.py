"""Reproducible current ranking export. Run beside semantic ledger and opponent_success.py.
Inputs: accepted plays + full ledger from semantic_ledger.py, not obsolete extract_success.py.
"""
import collections,csv,gzip,hashlib,json,pathlib
from opponent_success import adjust
O=pathlib.Path(__file__).parent

def main():
 plays=[json.loads(l)for l in gzip.open(O/'raw_success_plays.jsonl.gz','rt')];fit=adjust(plays,'2026-11-23');by={x['team_id']:x for x in fit['teams']};ledger=[json.loads(l)for l in gzip.open(O/'semantic_ledger.jsonl.gz','rt')]
 counts=collections.defaultdict(lambda:dict(n=0,s=0,g=set()));held=collections.Counter()
 for p in plays:
  for side in ['offense','defense']:
   a=counts[(p[side+'_id'],side)];a['n']+=1;a['s']+=p['success'];a['g'].add(p['event_id'])
 for p in ledger:
  if p['status']=='quarantine' or p['game_quarantined']:
   for side in ['offense','defense']:held[p[side+'_id'],side]+=1
 out=[]
 for tid,t in by.items():
  r=dict(team=t['team'],team_id=tid,adjusted_offense_success_pct=100*(fit['league_success_rate']+t['offense_effect']),adjusted_defense_success_allowed_pct=100*(fit['league_success_rate']+t['defense_success_allowed_effect']))
  for side,adj in [('offense','offensive'),('defense','defensive')]:
   c=counts[tid,side];r.update({adj+'_plays':c['n'],adj+'_games':len(c['g']),'raw_'+side+'_success'+('_allowed'if side=='defense'else'')+'_pct':100*c['s']/c['n'],adj+'_quarantined_source_rows':held[tid,side]})
  r['status']='PROVISIONAL_RESEARCH_NOT_FULL_SEASON_EFFICIENCY';out.append(r)
 for side,key,reverse in [('offense','adjusted_offense_success_pct',True),('defense','adjusted_defense_success_allowed_pct',False)]:
  for i,r in enumerate(sorted(out,key=lambda r:(-r[key]if reverse else r[key],r['team_id'])),1):r[side+'_rank']=i
 out.sort(key=lambda r:r['offense_rank']);meta={k:v for k,v in fit.items()if k!='teams'};meta.update(team_count=len(out),success_definition='50/70/100 percent distance on downs 1/2/3-4',coverage='Accepted regulation FBS-v-FBS plays; no garbage-time filter; unresolved adverse plays withheld',source_provenance='semantic_ledger.jsonl.gz has event/play/source hashes and URLs; source manifest supplied separately')
 (O/'current_efficiency_rankings.json').write_text(json.dumps(dict(metadata=meta,rows=out),indent=2))
 for side in ['offense','defense']:
  with open(O/('cfb-2026-'+side+'-efficiency.csv'),'w')as f:w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(sorted(out,key=lambda r:r[side+'_rank']))
 manifest=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in[O/'raw_success_plays.jsonl.gz',O/'semantic_ledger.jsonl.gz',O/'opponent_success.py',O/'build_current_rankings.py',O/'current_efficiency_rankings.json']];(O/'ranking_export_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(dict(teams=len(out),plays=fit['plays'],top=out[0]),indent=2))
if __name__=='__main__':main()
