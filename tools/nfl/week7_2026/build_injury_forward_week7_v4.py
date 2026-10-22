#!/usr/bin/env python3
"""Build the immutable Week 7 injury-experiment cohort v4 (unproven; shown beside the frozen baseline per the standing Oct 7 instruction).
Same frozen Oct 7 fit as the Week 5/6 cohorts (tools/nfl/injury_v2/results.json, sha256 87e03553c5bd90a1123710d222e25af72042262f3251c6c24bfb30563545e358; no refit, no tuning).
v4 changes vs v3 (Oct 21): refreshed provider IR inventory (roster asset of Oct 21; Adams and Ford now roster-confirmed IR, Romeo Doubs NE added) plus the first Week 7 report rows in the provider injury file (asset updated 2026-10-21T12:53Z): CHI and NE only (Thursday night teams; Tuesday practice participation, no game-status designations yet). All other teams remain IR-inventory + verified-news only, as in v3.
Snap weights: 2026 through Week 6, 2025 fallback for missing. No book/weather inputs, no manual point bumps."""
import sys,pathlib,json,datetime
import pandas as pd,numpy as np
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tools/nfl/injury_v2'));from evaluate import norm,AL
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
AL={**AL,'WAS':'WSH','LAR':'LA'}
rost=pd.read_csv(P/'roster_2026_20261021.csv',low_memory=False);rost.team=rost.team.replace(AL);rost['key']=rost.full_name.map(norm);rost=rost.sort_values('week').drop_duplicates('key',keep='last')
records={}
def put(n,t,p,s,pr,src,conflict=False):records[(t,norm(n))]=dict(player=n,team=t,position=p,status=s,practice=pr,source=src,conflict=conflict,observed_at=now)
for a in rost[rost.status_description_abbr.isin(['R01','R48'])].itertuples():put(a.full_name,a.team,a.position,'IR','','https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv')
# Week 7 provider injury-file rows (asset updated 2026-10-21T12:53Z): CHI/NE only so far
inj=pd.read_csv(P/'injuries_2026_20261021.csv',low_memory=False);inj=inj[(inj.season==2026)&(inj.week==7)].copy();inj.team=inj.team.replace(AL)
report_teams=sorted(inj.team.unique())
for a in inj.itertuples():
 k=(a.team,norm(a.full_name));s=a.report_status if pd.notna(a.report_status) and str(a.report_status).strip() else 'No game designation';pr=a.practice_status if pd.notna(a.practice_status) and str(a.practice_status).strip() else 'Unknown'
 if k in records and records[k]['status']=='IR':records[k].update(practice=pr,report_status=s);continue
 put(a.full_name,a.team,a.position,s,pr,'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.csv')
# Verified news override not yet roster-reflected (see tools/nfl/week7_2026/availability_news_20261020.json)
put('Terry McLaurin','WSH','WR','Out','','https://www.espn.com/nfl/story/_/id/50230371/commanders-wr-terry-mclaurin-torn-patellar-tendon')
# News-confirmed statuses now roster-confirmed IR: annotate, keep traceable
for nm_,tm_,src_ in [('Jalen Hurts','PHI','https://theeagleswire.usatoday.com/story/sports/nfl/eagles/2026/10/19/eagles-jalen-hurts-blood-clots-lungs-nicole-lynn-statement/92328312007/'),('Davante Adams','LA','https://www.nfl.com/news/davante-adams-hamstring-expected-to-miss-6-10-weeks-as-injuries-pile-up-rams'),('Poona Ford','LA','https://apnews.com/article/rams-davante-adams-poona-ford-injuries-b8140c5993e799a0c5a44dab5e8b87b2')]:
 k=(tm_,norm(nm_));assert k in records and records[k]['status']=='IR',f'{nm_} expected on roster IR'
 records[k]['news_source']=src_
sc=pd.concat([pd.read_csv(P/'snap_counts_2026.csv'),pd.read_csv(R/'tools/nflverse/225-snap_counts_2025.csv')]);sc=sc[(sc.game_type=='REG')&((sc.season<2026)|((sc.season==2026)&(sc.week<7)))].copy();sc.team=sc.team.replace(AL);sc['key']=sc.player.map(norm);sc['share']=sc[['offense_pct','defense_pct']].max(axis=1)
for a in rost.itertuples():
 sc.loc[(sc.team==a.team)&(sc.pfr_player_id==a.pfr_id),'key']=a.key
GROUP=lambda p:'QB' if p=='QB' else 'SKILL' if p in ['RB','FB','WR','TE'] else 'OL' if p in ['C','G','T','OG','OT','OL'] else 'DEF' if p in ['DE','DT','NT','DL','LB','ILB','OLB','CB','DB','S','FS','SS'] else 'OTHER'
teamfeat={}
for (t,n),a in records.items():
 z=sc[(sc.team==t)&(sc.key==n)&(sc.season==2026)].sort_values('week').tail(4);fallback=False
 if z.empty:z=sc[(sc.key==n)&(sc.season==2025)].sort_values('week').tail(4);fallback=not z.empty
 a['snap_weight']=round(float(z.share.mean()),4) if len(z) else None;a['snap_weight_source']='2025 fallback (may be previous team)' if fallback else '2026 through Week6' if len(z) else 'missing';g=GROUP(a['position']);a['position_group']=g
 f=teamfeat.setdefault(t,{g+'_'+s:0. for g in ['QB','SKILL','OL','DEF'] for s in ['absent','question','practice']});w=a['snap_weight'] or 0
 if g=='OTHER' or a['conflict']:continue
 if a['status'] in ['IR','Out','Doubtful']:f[g+'_absent']+=w
 if a['status']=='Questionable':f[g+'_question']+=w
 if a['practice']=='Did Not Participate In Practice':f[g+'_practice']+=w
fit=json.load(open(R/'tools/nfl/injury_v2/results.json'))['variants']['margin']['practice_groups'];cols=list(fit['coefficients']);coef=np.array(list(fit['coefficients'].values()));scale=np.array(fit['feature_scale']);pred=json.load(open(R/'tools/nfl/week7_2026/game_predictions_raw.json'));games=[];covered=set(rost.team.unique())
for a in pred:
 h=AL.get(a['home'],a['home']);w=AL.get(a['away'],a['away']);f=np.array([teamfeat.get(h,{}).get(c[5:],0)-teamfeat.get(w,{}).get(c[5:],0) for c in cols]);delta=float((f/scale)@coef);m=a['raw_margin_home']+delta
 miss=[t for t in (w,h) if t not in report_teams]
 note='Week 7 practice participation reflected from the provider injury file (asset updated Oct 21 12:53Z; Tuesday practice, no game-status designations yet).' if not miss else f'No Week 7 report rows for {", ".join(miss)} in the provider injury file (asset updated Oct 21 12:53Z; only CHI/NE rows so far); IR inventory + verified news only.'
 games.append(dict(matchup=w+' at '+h,kickoff_date=a['date'],baseline_margin_home=a['raw_margin_home'],injury_adjusted_margin_home=round(m,2),delta_margin_home=round(delta,2),injury_adjusted_spread='PK' if abs(m)<.25 else f"{h if m>0 else w} -{round(abs(m)*2)/2:g}",baseline_total=a['model_total'],injury_adjusted_total=None,total_note='Withheld: injury-total candidate worsened diagnostics',coverage_missing=[b['player'] for b in records.values() if b['team'] in [w,h] and b['snap_weight'] is None],missing_report_teams=miss,report_note=note,conflicts=[]))
base=json.load(open(R/'player_projections.json'));players=[]
for a in base['players']:
 b=records.get((AL.get(a['team'],a['team']),norm(a['player'])));out=bool(b and b['status'] in ['IR','Out'])
 numeric={k:a.get(k,{}).get('median') if isinstance(a.get(k),dict) else a.get(k) for k in ['passing_yards','passing_tds','receiving_yards','rushing_yards','receptions','anytime_td_probability']}
 players.append(dict(player_id=a['player_id'],player=a['player'],team=a['team'],baseline=numeric,injury_adjusted={k:0 if out and v is not None else v for k,v in numeric.items()},status=b['status'] if b else 'No captured designation (not proof healthy)',practice=b['practice'] if b else '',note='IR/Out: zero participation, not book settlement odds.' if out else 'Generic baseline unchanged; no teammate redistribution.'))
res=dict(generated_at=now,week=7,model_version='injury-experiment-20261021-w7-v4',caveat='New immutable Week7 cohort v4 (refreshed Oct 21 IR inventory with Adams/Ford roster-confirmed and the first Week 7 report rows: CHI/NE Tuesday practice for Thursday night; v1, v2 and v3 stay as published); unvalidated experiment, not a betting edge. Baseline frozen and shown beside it.',method='Same Oct7 fitted practice/status residual-margin coefficients as Week 5/6 cohorts, no refit (fit sha256 87e03553c5bd90a1123710d222e25af72042262f3251c6c24bfb30563545e358). Snap weights through Week6; 2025 fallback for missing. Refreshed IR inventory (Oct 21 roster asset) + Week 7 report rows where they exist (CHI/NE) + verified news; adjustment relative to no-injury row. No book/weather inputs or manual point bumps.',limitations=['Only CHI and NE (Thursday night teams) have Week 7 rows in the provider injury file as of its Oct 21 12:53Z asset update - Tuesday practice participation only, no Out/Doubtful/Questionable game designations yet. All other teams remain IR-inventory + verified-news only, so their report-based statuses are NOT yet reflected. Expect material changes when the remaining reports land; this cohort will be superseded.','Practice participation is not game clearance, and game designations for CHI/NE have not been issued yet.','IR provider inventory is not a 32-team transaction audit and long absences can already be in the scores-only baseline, so double counting is possible.','Missing snap roles have zero contribution and are listed, not assumed healthy.','No fitted DNP play probability or teammate redistribution.','Totals and home-win probabilities stay baseline; the injury-total candidate worsened diagnostics.','Unproven: two straight one-week diagnostics (Weeks 5 and 6) favored the baseline. Shown beside the baseline per the standing Oct 7 instruction; NOT promoted.'],coverage=dict(ir_players=sum(a['status']=='IR' for a in records.values()),availability_rows=len(records),missing_snap_weights=sum(a['snap_weight'] is None for a in records.values()),roster_inventory_teams=sorted(covered),injury_report_teams=report_teams,injury_report_rows=int(len(inj)),provider_injuries_asset_updated='2026-10-21T12:53:02Z',numerical_games=sum(g['injury_adjusted_margin_home'] is not None for g in games),news_overrides=['Terry McLaurin (WSH WR) Out for season (coach Dan Quinn via ESPN Oct 20; torn patellar tendon per ESPN/NBC Sports PFT)','Jalen Hurts (PHI QB) IR, roster-confirmed','Davante Adams (LA WR) IR, roster-confirmed Oct 21 (hamstring, out 6-10 weeks per McVay Oct 19)','Poona Ford (LA DT) IR, roster-confirmed Oct 21 (out for season per AP Oct 19)'],sources=['https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.csv','https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv','https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2026.csv','https://www.nfl.com/news/davante-adams-hamstring-expected-to-miss-6-10-weeks-as-injuries-pile-up-rams','https://apnews.com/article/rams-davante-adams-poona-ford-injuries-b8140c5993e799a0c5a44dab5e8b87b2','https://www.espn.com/nfl/story/_/id/50230371/commanders-wr-terry-mclaurin-torn-patellar-tendon']),inventory=list(records.values()),games=games,players=players)
out=P/'injury_forward_20261021_v4.json';out.write_text(json.dumps(res,indent=1)+'\n')
import hashlib;print('sha256',hashlib.sha256(open(out,'rb').read()).hexdigest())
print(res['coverage'])
for g in games:print(g['matchup'],'base',g['baseline_margin_home'],'adj',g['injury_adjusted_margin_home'],'delta',g['delta_margin_home'])
