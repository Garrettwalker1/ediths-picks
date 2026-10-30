import pandas as pd,json
from pathlib import Path
P=Path('/tmp/prop-matchup/v2');d=pd.read_csv(P/'depth_charts_2026.csv',low_memory=False);d.team=d.team.replace({'WAS':'WSH','LAR':'LA'});mx=d.groupby('team')['dt'].max();d=d[d['dt'].eq(d.team.map(mx))]
a=json.load(open(P/'roster_gate_audit.json'))
for x in a['rows']:
 z=d[d.gsis_id.eq(x['player_id'])&d.team.eq(x['team'])];x['depth_chart_as_of']=mx.get(x['team']);x['depth_roles']=z[['pos_grp','pos_abb','pos_slot','pos_rank']].drop_duplicates().to_dict('records')
 if x['position']=='QB':
  q=z[z.pos_abb.eq('QB')];x['listed_first_QB']=bool(len(q) and q.pos_rank.min()==1)
  if x['listed_first_QB']:x['gates']=[v for v in x['gates'] if v!='EXPECTED_STARTER_UNVERIFIED']+['DEPTH_QB1_NOT_FINAL_STARTER_CONFIRMATION']
print('QB1',[(x['team'],x['player']) for x in a['rows'] if x.get('listed_first_QB')]);print('missingdepth',sum(not x['depth_roles'] for x in a['rows']))
a['depth_source']='https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2026.csv';a['depth_limitation']='Latest per-team depth listing is a role lead, not game-day participation, snap share or guaranteed starting designation.';(P/'roster_gate_audit.json').write_text(json.dumps(a,indent=2))
