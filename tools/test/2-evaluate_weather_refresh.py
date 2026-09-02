#!/usr/bin/env python3
"""Evaluate a validated weather fact snapshot against the locked refresh policy.
Does not fit or mutate the model. It emits the trigger decision used before an
exact v3 weather-only rerun. Book lines/prices are neither accepted nor read.
"""
import argparse,datetime,json,os
p=argparse.ArgumentParser();p.add_argument('--policy',required=True);p.add_argument('--snapshot',required=True);p.add_argument('--previous');p.add_argument('--output',required=True);a=p.parse_args()
if os.path.exists(a.output):raise SystemExit('refusing to replace immutable decision: '+a.output)
pol=json.load(open(a.policy));s=json.load(open(a.snapshot));prev=json.load(open(a.previous)) if a.previous else None
req=['event_id','kickoff','stadium','latitude','longitude','timezone','roof_status','forecast_observed_at','forecast_valid_at','temperature_2m_f','wind_speed_10m_mph']
miss=[k for k in req if s.get(k) is None]
if miss:raise SystemExit('missing required weather fact fields: '+','.join(miss))
def dt(x):return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
kick=dt(s['kickoff']);obs=dt(s['forecast_observed_at']);valid=dt(s['forecast_valid_at'])
if abs((valid-kick).total_seconds())>3600:raise SystemExit('forecast_valid_at must be within one hour of kickoff')
hours=(kick-obs).total_seconds()/3600
if hours<0 or hours>pol['forecast_window_hours']:raise SystemExit('snapshot is outside locked pre-kick forecast window')
roof=s['roof_status'].lower().replace('_',' ')
if roof in ('fixed closed','retractable closed'):
 decision={'event_id':str(s['event_id']),'evaluated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rerun':False,'reason':'confirmed closed roof; weather logged only','snapshot':s}
elif roof not in ('open air','retractable open'):
 raise SystemExit('ambiguous roof status; preserve last good model')
else:
 def band(v,edges):
  for i in range(len(edges)-1):
   if edges[i]<=float(v)<edges[i+1]:return i
  raise ValueError('value outside policy edges')
 cur={'temperature_2m_f':band(s['temperature_2m_f'],pol['material_bins']['temperature_2m_f']['edges']),'wind_speed_10m_mph':band(s['wind_speed_10m_mph'],pol['material_bins']['wind_speed_10m_mph']['edges'])}
 if prev is None:rerun=True;why='first validated inside-48h weather replaces preseason median default'
 else:
  old={'temperature_2m_f':band(prev['temperature_2m_f'],pol['material_bins']['temperature_2m_f']['edges']),'wind_speed_10m_mph':band(prev['wind_speed_10m_mph'],pol['material_bins']['wind_speed_10m_mph']['edges'])};changed=[k for k in cur if cur[k]!=old[k]];rerun=bool(changed);why=('locked weather bin crossed: '+','.join(changed)) if changed else 'no locked weather bin crossed'
 decision={'event_id':str(s['event_id']),'evaluated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rerun':rerun,'reason':why,'input_bands':cur,'snapshot':s}
with open(a.output,'x') as f:json.dump(decision,f,indent=2)
print(json.dumps({'output':a.output,'rerun':decision['rerun'],'reason':decision['reason']}))
