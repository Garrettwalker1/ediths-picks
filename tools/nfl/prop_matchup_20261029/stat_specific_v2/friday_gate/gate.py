import json,pandas as pd,numpy as np,importlib.util,datetime,hashlib
from pathlib import Path
from sklearn.linear_model import LinearRegression
P=Path('/tmp/prop-matchup/v2');R=Path('/tmp/edith-oct28');Q=R/'tools/nfl/week8_2026/refresh_20261030'
f=json.load(open(P/'forward_unverified.json'));d=pd.DataFrame(f['rows']);u=d.drop_duplicates('player_id');r=pd.read_csv(Q/'roster.csv',low_memory=False);r.team=r.team.replace({'WAS':'WSH','LAR':'LA'});r=r.sort_values('week').drop_duplicates('gsis_id',keep='last');z=u.merge(r,left_on='player_id',right_on='gsis_id',how='left',suffixes=('','_roster'))
inj=pd.read_csv(Q/'injuries.csv');inj=inj[inj.week.eq(8)];inj.team=inj.team.replace({'WAS':'WSH','LAR':'LA'});ii=inj.set_index('gsis_id').to_dict('index');audit=[]
for a in z.to_dict('records'):
 b=ii.get(a['player_id'],{});reasons=[]
 if a['team']!=a['team_roster']:reasons.append('LATEST_STATS_TEAM_DIFFERS_CURRENT_ROSTER')
 if a['status_roster']!='ACT':reasons.append('ROSTER_STATUS_'+str(a['status_roster']))
 if a['last_played_week']<7:reasons.append('NO_WEEK7_PLAYED_ROW_RECHECK_ROLE_OR_BYE')
 if a['position']=='QB':reasons.append('EXPECTED_STARTER_UNVERIFIED')
 reasons.append('CURRENT_OPPORTUNITY_ROLE_UNVERIFIED')
 if a['team']=='SEA':reasons.append('PROVIDER_WEEK8_REPORT_MISSING')
 reasons.append('FINAL_AVAILABILITY_UNVERIFIED')
 audit.append({k:a[k] for k in ['player_id','player','team','position','game_id','last_played_week']}|{'roster_team':a['team_roster'],'roster_status':a['status_roster'],'roster_status_detail':a['status_description_abbr'],'roster_week':int(a['week']),'provider_report_status':None if pd.isna(b.get('report_status')) else b.get('report_status'),'gates':reasons})
# Reconstruct deployed generator recipe on its historical training data; future features use fresh throughWeek7. No refit promotion.
spec=importlib.util.spec_from_file_location('old',R/'tools/nfl/week7_2026/players/generate_players_w7.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
raw=pd.concat([pd.read_csv(R/f'tools/player_projection_cache/stats_{y}.csv',low_memory=False) for y in [2023,2024,2025]])
raw=raw[raw.season_type.eq('REG')];roll=old.roll(raw);train=roll[roll.season.le(2025)&roll.position.isin(['RB','WR','TE'])&roll.receiving_yards_r3.notna()]
rush=roll[roll.season.le(2025)&roll.position.isin(['RB','QB'])&roll.rushing_yards_r3.notna()]
cur=pd.read_csv(P/'stats_2026.csv',low_memory=False);cur=cur[cur.season_type.eq('REG')&cur.week.le(7)];allhist=pd.concat([raw,cur]);L=old.latest_rows(allhist).set_index('player_id');base={}
for target,fs,tt in [('receiving_yards',old.RF,train),('rushing_yards',old.QF,rush),('receptions',old.REPF,train)]:
 tt=tt.dropna(subset=fs);m=LinearRegression().fit(tt[fs],tt[target]);base[target]={pid:max(0,float(m.predict(pd.DataFrame([{k:L.loc[pid,k] for k in fs}]))[0])) for pid in u.player_id if pid in L.index and np.isfinite(L.loc[pid,fs].astype(float)).all()}
out=[]
for a in f['rows']:
 a=a.copy();a['deployed_recipe_fresh_features_mean']=base.get(a['stat'],{}).get(a['player_id']);a['comparison_note']='Same deployed 2023-25 linear recipe reconstructed, fresh player rolling inputs throughWeek7. Not old stored Week7 values. In-sample training recipes differ; forward-only comparison is not accuracy validation.';out.append(a)
res={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':audit,'counts':{'identities':len(audit),'non_ACT':sum(a['roster_status']!='ACT' for a in audit),'team_mismatch':sum(a['team']!=a['roster_team'] for a in audit),'numeric_model_stat_rows':len(out),'cleared_for_pregame_seal':0},'policy':'No silent exclusions. Preserve all universe entries, reasons and unavailable forecasts. ACT does not prove game-day active or opportunity. Role and final availability gates still open.'}
(P/'roster_gate_audit.json').write_text(json.dumps(res,indent=2));(P/'forward_comparison_research.json').write_text(json.dumps({'research_only':True,'withheld_from_live_predictions':True,'rows':out},indent=2));print(res['counts'])
for stat in base:
 a=pd.DataFrame(out);a=a[a.stat.eq(stat)&a.model.eq('usage_stat_matchup')].dropna(subset=['deployed_recipe_fresh_features_mean']);delta=a.unrounded_mean-a.deployed_recipe_fresh_features_mean;print(stat,'paired',len(a),'median_abs_difference',delta.abs().median())
