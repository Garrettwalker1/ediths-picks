#!/usr/bin/env python3
"""Build the immutable Week 7 injury-experiment cohort v8 (unproven; shown beside the frozen baseline per the standing Oct 7 instruction).
v8 changes vs v7 (Oct 24 AM): Saturday provider injury-file refresh (asset updated 2026-10-24T11:57:46Z) now carries Friday practice participation AND official game designations for all 28 playing teams - including Puka Nacua's official Questionable (calf, DNP Friday), so the dated ESPN news override from v7 is dropped (provider row carries the same facts with better provenance). All other v7 inputs unchanged: same roster asset (Oct 23 12:36:57Z), same frozen fit, v1-v7 stay as published.
v7 had: dated verified-news override for Nacua (ESPN Oct 23) until the provider file reflected Friday practice - now superseded by the provider row itself.
Same frozen Oct 7 fit as the Week 5/6 cohorts (tools/nfl/injury_v2/results.json, sha256 87e03553c5bd90a1123710d222e25af72042262f3251c6c24bfb30563545e358; no refit, no tuning).
Snap weights: 2026 through Week 6, 2025 fallback for missing. No book/weather inputs, no manual point bumps."""
import sys,pathlib,json,datetime
import pandas as pd,numpy as np
R=pathlib.Path(__file__).resolve().parents[4];P=pathlib.Path(__file__).resolve().parent.parent;Q=P/'refresh_20261029'
import re
AL={'WAS':'WSH','LAR':'LA'}
def norm(s):
 return re.sub(r'[^a-z]','',re.sub(r'\b(jr|sr|ii|iii|iv)\b','',str(s).lower().replace('.','')))
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
AL={**AL,'WAS':'WSH','LAR':'LA'}
rost=pd.read_csv(Q/'roster.csv',low_memory=False);rost.team=rost.team.replace(AL);rost['key']=rost.full_name.map(norm);rost=rost.sort_values('week').drop_duplicates('key',keep='last')
records={}
def put(n,t,p,s,pr,src,conflict=False):records[(t,norm(n))]=dict(player=n,team=t,position=p,status=s,practice=pr,source=src,conflict=conflict,observed_at=now)
for a in rost[rost.status_description_abbr.isin(['R01','R48'])].itertuples():put(a.full_name,a.team,a.position,'IR','','https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv')
# Week 7 provider injury-file rows (asset updated 2026-10-24T11:57:46Z): all 28 playing teams with official game designations
inj=pd.read_csv(Q/'injuries.csv',low_memory=False);inj=inj[(inj.season==2026)&(inj.week==8)].copy();inj.team=inj.team.replace(AL)
report_teams=sorted(inj.team.unique())
for a in inj.itertuples():
 k=(a.team,norm(a.full_name));s=a.report_status if pd.notna(a.report_status) and str(a.report_status).strip() else 'No game designation';pr=a.practice_status if pd.notna(a.practice_status) and str(a.practice_status).strip() else 'Unknown'
 if k in records and records[k]['status']=='IR':records[k].update(practice=pr,report_status=s);continue
 put(a.full_name,a.team,a.position,s,pr,'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.csv')
put('Keisean Nixon','GB','CB','Questionable','Unknown','https://www.packers.com/news/packers-announce-injury-update-oct-29-2026')
put('Taylor Moton','CAR','OT','IR','','https://www.panthers.com/news/panthers-place-right-tackle-taylor-moton-on-injured-reserve')
sc=pd.concat([pd.read_csv(P/'snap_counts_2026.csv'),pd.read_csv(R/'tools/nflverse/225-snap_counts_2025.csv')]);sc=sc[(sc.game_type=='REG')&((sc.season<2026)|((sc.season==2026)&(sc.week<8)))].copy();sc.team=sc.team.replace(AL);sc['key']=sc.player.map(norm);sc['share']=sc[['offense_pct','defense_pct']].max(axis=1)
for a in rost.itertuples():
 sc.loc[(sc.team==a.team)&(sc.pfr_player_id==a.pfr_id),'key']=a.key
GROUP=lambda p:'QB' if p=='QB' else 'SKILL' if p in ['RB','FB','WR','TE'] else 'OL' if p in ['C','G','T','OG','OT','OL'] else 'DEF' if p in ['DE','DT','NT','DL','LB','ILB','OLB','CB','DB','S','FS','SS'] else 'OTHER'
teamfeat={}
for (t,n),a in records.items():
 z=sc[(sc.team==t)&(sc.key==n)&(sc.season==2026)].sort_values('week').tail(4);fallback=False
 if z.empty:z=sc[(sc.key==n)&(sc.season==2025)].sort_values('week').tail(4);fallback=not z.empty
 a['snap_weight']=round(float(z.share.mean()),4) if len(z) else None;a['snap_weight_source']='2025 fallback (may be previous team)' if fallback else '2026 through Week7' if len(z) else 'missing';g=GROUP(a['position']);a['position_group']=g
 f=teamfeat.setdefault(t,{g+'_'+s:0. for g in ['QB','SKILL','OL','DEF'] for s in ['absent','question','practice']});w=a['snap_weight'] or 0
 if g=='OTHER' or a['conflict']:continue
 if a['status'] in ['IR','Out','Doubtful']:f[g+'_absent']+=w
 if a['status']=='Questionable':f[g+'_question']+=w
 if a['practice']=='Did Not Participate In Practice':f[g+'_practice']+=w
fit=json.load(open(R/'tools/nfl/injury_v2/results.json'))['variants']['margin']['practice_groups'];cols=list(fit['coefficients']);coef=np.array(list(fit['coefficients'].values()));scale=np.array(fit['feature_scale']);pred=json.load(open(R/'tools/nfl/week8_2026/game_predictions_raw.json'));games=[];covered=set(rost.team.unique())
for a in pred:
 h=AL.get(a['home'],a['home']);w=AL.get(a['away'],a['away']);f=np.array([teamfeat.get(h,{}).get(c[5:],0)-teamfeat.get(w,{}).get(c[5:],0) for c in cols]);delta=float((f/scale)@coef);m=a['raw_margin_home']+delta
 miss=[t for t in (w,h) if t not in report_teams]
 note='Week 7 game designations and Friday practice participation reflected from the provider injury file (asset updated Oct 24 11:57:46Z; all 28 playing teams carry official designations).' if not miss else f'No Week 7 report rows for {", ".join(miss)} in the provider injury file (asset updated Oct 24 11:57:46Z); IR inventory + verified news only.'
 games.append(dict(matchup=w+' at '+h,kickoff_date=a['date'],baseline_margin_home=a['raw_margin_home'],injury_adjusted_margin_home=round(m,2),delta_margin_home=round(delta,2),injury_adjusted_spread='PK' if abs(m)<.25 else f"{h if m>0 else w} -{round(abs(m)*2)/2:g}",baseline_total=a['model_total'],injury_adjusted_total=None,total_note='Withheld: injury-total candidate worsened diagnostics',coverage_missing=[b['player'] for b in records.values() if b['team'] in [w,h] and b['snap_weight'] is None],missing_report_teams=miss,report_note=note,conflicts=[]))
base=json.load(open(R/'player_projections.json'));players=[]
for a in base['players']:
 b=records.get((AL.get(a['team'],a['team']),norm(a['player'])));out=bool(b and b['status'] in ['IR','Out'])
 numeric={k:a.get(k,{}).get('median') if isinstance(a.get(k),dict) else a.get(k) for k in ['passing_yards','passing_tds','receiving_yards','rushing_yards','receptions','anytime_td_probability']}
 players.append(dict(player_id=a['player_id'],player=a['player'],team=a['team'],baseline=numeric,injury_adjusted={k:0 if out and v is not None else v for k,v in numeric.items()},status=b['status'] if b else 'No captured designation (not proof healthy)',practice=b['practice'] if b else '',note='IR/Out: zero participation, not book settlement odds.' if out else 'Generic baseline unchanged; no teammate redistribution.'))
res=dict(generated_at=now,week=8,model_version='injury-experiment-20261027-w8-v1',caveat='Early Week8 cohort: fresh roster IR inventory only, zero provider Week8 report rows. Not promoted. Prior Week7 practice/game designations are NOT reused.',method='Same frozen Oct7 practice-group residual fit; fresh snap weights through Week7; no book inputs, manual point bumps, or teammate redistribution.',limitations=['Week8 reports missing for every playing team at build; current unknowns are not proof healthy.','IR inventory can double-count long absences already in scores baseline.','Missing roles have zero contribution, not healthy.','No QB replacement quality, workload or teammate redistribution adjustment.','Totals withheld; historical diagnostics do not validate improvement.'],coverage=dict(ir_players=sum(a['status']=='IR' for a in records.values()),availability_rows=len(records),missing_snap_weights=sum(a['snap_weight'] is None for a in records.values()),injury_report_teams=report_teams,injury_report_rows=len(inj)),inventory=list(records.values()),games=games,players=players)
res.update(model_version='injury-experiment-20261029-w8-v2',caveat='26 of28 playing teams have current Week8 provider reports; CHI/SEA first Monday-game reports missing. Weekend practice participation is not final clearance. Official CAR/GB final reports checked; Nixon Q added from official Oct29 update.',limitations=['Experimental, not proven more accurate.','Weekend game designations pending; absence of a designation is not clearance.','IR long absences may already be reflected in scores baseline.','No QB replacement quality, teammate redistribution or weather model.','Missing snap roles contribute zero, not healthy.'])
res['coverage']['news_overrides']=['Keisean Nixon official Questionable Oct29 shoulder; Taylor Moton official IR retained.']
for g in res['games']:
 g['report_note']='Current Week8 practice reports; CAR/GB final designation report. Other games not final.'
 if g['missing_report_teams']:
  g['injury_adjusted_margin_home']=None;g['injury_adjusted_spread']=None;g['withheld_reason']='Current-week report missing'
out=Q/'injury_forward_20261029_v2.json';out.write_text(json.dumps(res,indent=1)+'\n')
print('INJURY',res['coverage']);print('TNF',res['games'][0])
