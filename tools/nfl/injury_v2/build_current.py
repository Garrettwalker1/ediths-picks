#!/usr/bin/env python3
"""Separate unvalidated injury experiment. Never rewrite baseline or result grading."""
import pathlib,json,re,datetime,math,hashlib
import pandas as pd,numpy as np
from evaluate import norm,AL
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).parent
now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
h=(R/'index.html').read_text();ix=h.index('const D=');D,end=json.JSONDecoder().raw_decode(h[ix+8:])
rost=pd.read_csv(P/'roster_2026.csv');rost.team=rost.team.replace({**AL,'WAS':'WSH'});rost['key']=rost.full_name.map(norm)
# Keep latest record for a person's ID, then restrict current Week 5 status.
rost=rost.sort_values('week').drop_duplicates('key',keep='last')
records={}
def put(name,team,pos,status,practice,source,confidence='provider',conflict=False):
 team={'WAS':'WSH','LAR':'LA'}.get(team,team);key=(team,norm(name));records[key]=dict(player=name,team=team,position=pos,status=status,practice=practice,source=source,confidence=confidence,conflict=conflict,observed_at=now)
for a in rost[rost.status_description_abbr.isin(['R01','R48'])].itertuples():put(a.full_name,a.team,a.position,'IR','', 'https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv')
# Sleeper additions only if roster corroborates current team and not active/retired.
for a in json.load(open(P/'sleeper-ir.json')):
 z=rost[(rost.key==norm(a['player']))&(rost.team==a['team'])]
 if len(z) and z.iloc[0].status=='RES' and (a['team'],norm(a['player'])) not in records:
  put(a['player'],a['team'],a['position'],'IR','', 'https://api.sleeper.app/v1/players/nfl')
injs=pd.read_csv(P/'injuries_2026.csv');injs=injs[injs.week==5]
for a in injs.itertuples():
 team='WSH' if a.team=='WAS' else a.team;k=(team,norm(a.full_name))
 if k not in records:put(a.full_name,team,a.position,a.report_status if pd.notna(a.report_status) else 'No game designation',a.practice_status if pd.notna(a.practice_status) else '', 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.csv')
# Only current Oct 7 rows. Earlier-week archival news cannot set this week's status.
for a in D['news'][:18]:
 name=re.sub(r'\s*\([^)]*\)$','',a['player']);pos=re.search(r'\(([^)]*)\)$',a['player']);pos=pos.group(1) if pos else '';text=a['status'].lower();url=re.search('href="([^"]+)"',a['source']);url=url.group(1) if url else ''
 if 'conflicting' in text:put(name,a['team'],pos,'Conflict','',url,conflict=True);continue
 practice='Did Not Participate In Practice' if any(s in text for s in ['did not practice','not practicing','not expected at wednesday practice']) else 'Limited Participation in Practice' if 'limited' in text else 'Full Participation in Practice' if 'full wednesday' in text else 'Unknown'
 status='IR' if 'injured reserve' in text else 'No game designation'
 # Current full/limited practice supersedes stale game status, not current IR unless activated evidence.
 if (a['team'],norm(name)) in records and records[(a['team'],norm(name))]['status']=='IR' and status!='IR':
  put(name,a['team'],pos,'Conflict',practice,url,conflict=True)
 else:put(name,a['team'],pos,status,practice,url,'official/reporting')
sc=pd.concat([pd.read_csv(P/'snap_counts_2026.csv'),pd.read_csv(R/'tools/nflverse/225-snap_counts_2025.csv')]);sc=sc[(sc.game_type=='REG')&((sc.season<2026)|(sc.week<5))].copy();sc.team=sc.team.replace({**AL,'WAS':'WSH'});sc['key']=sc.player.map(norm);sc['share']=sc[['offense_pct','defense_pct']].max(axis=1)
# Current-season role preferred. Previous season fallback allowed for players with zero current games; marked.
hist={(t,n):z.sort_values(['season','week']) for (t,n),z in sc.groupby(['team','key'])}
GROUP=lambda p:'QB' if p=='QB' else 'SKILL' if p in ['RB','FB','WR','TE'] else 'OL' if p in ['C','G','T','OG','OT','OL'] else 'DEF' if p in ['DE','DT','NT','DL','LB','ILB','OLB','CB','DB','S','FS','SS'] else 'OTHER'
teamfeat={};missing=[]
for k,a in records.items():
 z=hist.get(k);recent=z[z.season==2026].tail(4) if z is not None else pd.DataFrame()
 fallback=False
 if recent.empty and z is None:
  other=sc[(sc.key==k[1])&(sc.season==2025)]
  if len(other):z=other.sort_values('week')
 if recent.empty and z is not None:recent=z[z.season==2025].tail(4);fallback=True
 a['snap_weight']=round(float(recent.share.mean()),4) if len(recent) else None;a['snap_weight_source']='2025 fallback (may be previous team)' if fallback else '2026 through Week 4' if len(recent) else 'missing';a['position_group']=GROUP(a['position'])
 if a['snap_weight'] is None:missing.append(a['player'])
 f=teamfeat.setdefault(a['team'],{g+'_'+s:0.0 for g in ['QB','SKILL','OL','DEF'] for s in ['absent','question','practice']});w=a['snap_weight'] or 0;g=a['position_group']
 if g=='OTHER' or a['conflict']:continue
 if a['status'] in ['IR','Out','Doubtful']:f[g+'_absent']+=w
 if a['status']=='Questionable':f[g+'_question']+=w
 if a['practice']=='Did Not Participate In Practice':f[g+'_practice']+=w
fit=json.load(open(P/'results.json'));pred=json.load(open(R/'tools/nfl/week5_2026/game_predictions_raw.json'));games=[]
variant=fit['variants']['margin']['practice_groups'];cols=list(variant['coefficients']);coef=np.array(list(variant['coefficients'].values()));scale=np.array(variant['feature_scale'])
# Difference from a no-injury row cancels residual intercept and feature centering.
for a in pred:
 home={'WAS':'WSH','LAR':'LA'}.get(a['home'],a['home']);away={'WAS':'WSH','LAR':'LA'}.get(a['away'],a['away']);features=np.array([teamfeat.get(home,{}).get(c[5:],0)-teamfeat.get(away,{}).get(c[5:],0) for c in cols]);delta=float((features/scale)@coef);m=round(a['raw_margin_home']+delta,2)
 games.append(dict(matchup=away+' at '+home,kickoff_date=a['date'],baseline_margin_home=a['raw_margin_home'],injury_adjusted_margin_home=m,delta_margin_home=round(delta,2),injury_adjusted_spread=('PK' if abs(m)<.25 else f'{home if m>0 else away} -{abs(m):.2f}'),baseline_total=a['model_total'],injury_adjusted_total=None,total_note='Withheld: injury-total candidate worsened diagnostic error',coverage_missing=[b['player'] for b in records.values() if b['team'] in [home,away] and b['snap_weight'] is None],conflicts=[b['player'] for b in records.values() if b['team'] in [home,away] and b['conflict']]))
players=[];base=json.load(open(R/'week5_player_predictions.json'))
for a in base['players']:
 b=records.get((a['team'],norm(a['player'])));out=bool(b and b['status'] in ['IR','Out'] and not b['conflict']);pending=bool(b and (b['conflict'] or (b['status'] not in ['IR','Out'] and b['practice'] in ['Did Not Participate In Practice','Unknown'])))
 numeric={k:(a.get(k,{}).get('median') if isinstance(a.get(k),dict) else a.get(k)) for k in ['passing_yards','passing_tds','receiving_yards','rushing_yards','receptions','anytime_td_probability']}
 adjusted={k:(0 if out and v is not None else None if pending else v) for k,v in numeric.items()}
 note='IR/out: zero participation, not a wager or void-settlement probability.' if out else 'Pending availability: no participation probability or backup redistribution fitted.' if pending else 'Baseline unchanged: teammate/backup opportunity redistribution not modeled.'
 players.append(dict(player_id=a['player_id'],player=a['player'],team=a['team'],baseline=numeric,injury_adjusted=adjusted,status=b['status'] if b else 'No captured injury designation',practice=b['practice'] if b else '',note=note))
result=dict(generated_at=now,model_version='injury-experiment-20261007-v1',caveat='Injury adjusted is unvalidated; not a betting edge. Baseline stays frozen.',method='Fitted practice/status residual-margin coefficients, train 2020-22. Current IR counts as Out; DNP is a distinct practice input, not Out. Adjustment relative to no-injury row; no manual points or book inputs.',limitations=['Full current IR coverage is provider-based, not 32-team transaction audit.','Long-term IR may already influence score-only baseline; applying full absence can double-count.','Missing snap roles contribute zero and are listed, not proof of no impact.','No player teammate/backup redistribution or DNP play-probability model.','Totals injury adjustment withheld because it worsened historical diagnostics.'],coverage=dict(ir_players=sum(a['status']=='IR' for a in records.values()),availability_rows=len(records),missing_snap_weights=len(missing),injury_report_teams=injs.team.unique().tolist(),sources=['https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv','https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2026.csv','https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.csv','https://api.sleeper.app/v1/players/nfl']),inventory=list(records.values()),games=games,players=players)
(R/'injury_adjustments.json').write_text(json.dumps(result,indent=1)+'\n');(P/'forward_predictions_20261007.json').write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps(result['coverage']));print('MOVERS',sorted(games,key=lambda a:abs(a['delta_margin_home']),reverse=True)[:5]);print('players unavailable',[(a['player'],a['baseline']['anytime_td_probability']) for a in players if a['status']=='IR'][:20])
