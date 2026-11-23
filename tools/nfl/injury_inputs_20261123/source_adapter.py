"""Retained-source injury-input adapter. No network, allocator or forecast mutation."""
import pathlib,json,gzip,re,datetime as dt
import pandas as pd
P=pathlib.Path(__file__).parent
S=P/'sources'
def clean(value):
 if isinstance(value,dict):return {k:clean(v)for k,v in value.items()}
 if isinstance(value,list):return [clean(v)for v in value]
 if value is None or isinstance(value,(str,bool)):return value
 if pd.isna(value):return None
 return value
def timestamp(x):
 d=dt.datetime.fromisoformat(str(x).replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('timezone required')
 return d.astimezone(dt.timezone.utc)
def depth_at(frame,decision_time):
 t=timestamp(decision_time);eligible=frame[pd.to_datetime(frame.dt,utc=True)<t]
 if eligible.empty:return eligible.copy()
 latest=eligible.groupby('team').dt.transform('max');out=eligible[eligible.dt==latest].copy()
 if out.duplicated(['team','pos_grp_id','pos_slot','pos_rank']).any():raise ValueError('ambiguous slot rank')
 return out
def player_link_id(athlete):
 ids=set()
 for l in athlete.get('links',[]):
  m=re.search(r'/id/(\d+)(?:/|$)',l.get('href',''))
  if m:ids.add(m.group(1))
 return next(iter(ids))if len(ids)==1 else None
def unique_map(frame,key,value):
 clean=frame[frame[key].notna()&frame[value].notna()]
 groups=clean.groupby(key)[value].agg(lambda s:set(s));return {k:next(iter(v))for k,v in groups.items()if len(v)==1}
def build(decision_time):
 D=pd.read_parquet(S/'depth_charts_2026.parquet');I=pd.read_parquet(S/'injuries_2026.parquet');N=pd.read_parquet(S/'snap_counts_2026.parquet');X=pd.read_parquet(S/'players.parquet');E=json.load(gzip.open(S/'espn_injuries_20261123T1919Z.json.gz','rt'))
 # Retained response is usable only after its recorded response time, never retroactively.
 if timestamp(decision_time)<timestamp(E['timestamp']):raise ValueError('retained response postdates decision')
 L=depth_at(D,decision_time);pm=unique_map(X,'pfr_id','gsis_id');em=unique_map(X,'espn_id','gsis_id')
 depth=L.to_dict('records')
 for r in depth:r.update(identity_status='verified_gsis'if pd.notna(r['gsis_id'])else'UNMAPPED',snapshot_time_semantics='record_loaded_not_disclosure_or_starter_certainty',slot_key=[r['team'],r['pos_grp_id'],r['pos_slot']])
 snaps=N.to_dict('records')
 for r in snaps:r.update(gsis_id=pm.get(r['pfr_player_id']),identity_status='crosswalk'if r['pfr_player_id']in pm else'UNMAPPED',measure='playing_time_not_additive_opportunities')
 entries=[]
 for team in E['injuries']:
  for e in team['injuries']:
   eid=player_link_id(e['athlete']);entries.append(dict(team=e['athlete'].get('team',{}).get('abbreviation'),espn_player_id=eid,gsis_id=em.get(eid),identity_status='crosswalk'if eid in em else'UNMAPPED',injury_entry_id=e.get('id'),status=e.get('status'),entry_updated_at=e.get('date'),response_timestamp=E['timestamp'],entry_future_time=timestamp(e['date'])>timestamp(E['timestamp'])))
 out=dict(version='nfl-source-layer-20261123-v1',decision_time=decision_time,admission='DESCRIPTIVE_INPUTS_ONLY',numerical_forecast_effect=False,prospective_allocation=None,depth=depth,weekly_injuries=dict(rows=I.to_dict('records'),row_timestamp_available=False,timing='week_only_plus_release_upload_not_disclosure'),snap_exposure=snaps,espn_statuses=entries,limitations=['Source statuses do not establish opportunity shares','No missing identity is name-filled','No return share restoration','Depth grouped by formation and slot, not abbreviation alone','Baseline mixture must match actual production history; continuing absence is not automatically zero delta'])
 return clean(out)
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--decision-time',required=True);args=a.parse_args();o=build(args.decision_time);(P/'source_layers.json').write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
