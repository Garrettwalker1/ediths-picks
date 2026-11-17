"""Integrate inspected provider JSON delivered by alternate read route. Never applies points."""
import json,pathlib,datetime,hashlib
P=pathlib.Path(__file__).parent;D=P/'weather_alternate_sources';D.mkdir(exist_ok=True);allwx={};manifest=[]
for f in sorted(pathlib.Path('/tmp').glob('ww-*.txt')):
 url=None
 for line in f.read_text().splitlines():
  if line.startswith('https://api.open-meteo'):url=line.strip()
  if line.startswith('{'):
   try:
    data=json.loads(line)
    if 'hourly'in data:
     allwx[url]=data;name=hashlib.sha256(url.encode()).hexdigest()[:18]+'.json';(D/name).write_text(line+'\n');manifest.append(dict(url=url,file=name,received_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256((line+'\n').encode()).hexdigest(),route='alternate provider read'))
   except json.JSONDecodeError:pass
req=json.load(open(P/'weather_forecast_requests.json'));o=json.load(open(P/'weather_context.json'))
for g in o['games']:
 r=req.get(g['event_id']);data=allwx.get(r['url'])if r else None
 if not data:continue
 h=data['hourly'];kt=datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00'));times=[datetime.datetime.fromisoformat(t).replace(tzinfo=datetime.timezone.utc)for t in h['time']];i=min(range(len(times)),key=lambda i:abs((times[i]-kt).total_seconds()))
 if abs((times[i]-kt).total_seconds())>3600:g['reason']='Outside current forecast horizon';continue
 g.pop('reason',None);g.update(status='context_only_no_adjustment',city=r['coords']['name'],admin1=r['coords'].get('admin1'),latitude=r['coords']['latitude'],longitude=r['coords']['longitude'],forecast_hour_utc=h['time'][i],temperature_f=h['temperature_2m'][i],wind_mph=h['wind_speed_10m'][i],gust_mph=h['wind_gusts_10m'][i],precip_in=h['precipitation'][i],precip_probability=h['precipitation_probability'][i],source_url=r['url'],note='City-resolution forecast near kickoff. Not stadium microclimate, roof confirmation or model correction.')
o['checked_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();o['direct_route_timed_out_alternate_read_recovered']=True;o['coverage']=dict(rows=len(o['games']),weather_forecasts=sum('temperature_f'in r for r in o['games']),indoor=sum(r['indoor']for r in o['games']),missing=sum(r['status']=='unavailable'for r in o['games']));(P/'weather_context.json').write_text(json.dumps(o,indent=2)+'\n');(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(o['coverage']);print([(g['name'],g.get('temperature_f'),g.get('wind_mph'),g.get('reason'))for g in o['games']if g['date']<'2026-11-18T06:00Z'])
