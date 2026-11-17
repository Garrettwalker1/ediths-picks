"""Current venue-city weather facts only. No forecast correction or failed-candidate transfer."""
import json,pathlib,datetime,urllib.request,urllib.parse,concurrent.futures,hashlib
P=pathlib.Path(__file__).parent;R=P.parents[2];S=P/'weather_sources';S.mkdir(exist_ok=True);manifest=[]
def get(url):
 at=datetime.datetime.now(datetime.timezone.utc).isoformat();blob=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'edith-weather/1.0'}),timeout=4).read();name=hashlib.sha256(url.encode()).hexdigest()[:18]+'.json';(S/name).write_bytes(blob);manifest.append(dict(url=url,file=name,requested_at=at,received_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(blob).hexdigest()));return json.loads(blob)
cfurl='https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week=12&groups=80&limit=400';cf=get(cfurl);nfl=json.load(open(R/'tools/nfl/current_season_20261117/sources/week11.json'));core=json.load(open(R/'tools/cfb/current_season_20261115/current_forecasts.json'));ids={g['event_id']for g in core['games']};ev={e['id']:e for e in cf['events']};assert ids<=ev.keys();assert all(ev[i]['competitions'][0]['status']['type']['state']=='pre'for i in ids)
for g in core['games']:assert g['date']==ev[g['event_id']]['date']
coords={}
for f in [R/'tools/cfb/current_inputs_20261016/current-coords.json',R/'tools/cfb/week11_20261108/current-coords.json']:coords.update(json.load(open(f)))
def one(z):
 sport,e=z;c=e['competitions'][0];v=c.get('venue',{});addr=v.get('address',{});row=dict(event_id=e['id'],date=e['date'],name=e['name'],sport=sport,venue=v.get('fullName'),indoor=v.get('indoor',False),neutral=c.get('neutralSite',False),adjustment=None,status='context_only_no_adjustment')
 try:
  if row['indoor']:return dict(row,note='Indoor per ESPN venue record. No outdoor weather penalty assumed.')
  co=coords.get(str(v.get('id')))
  if not co:raise RuntimeError('No previously verified city coordinate for this venue; no guessed location used')
  url=f"https://api.open-meteo.com/v1/forecast?latitude={co['latitude']}&longitude={co['longitude']}&hourly=temperature_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=UTC";d=get(url);h=d['hourly'];kt=datetime.datetime.fromisoformat(e['date'].replace('Z','+00:00'));i=min(range(len(h['time'])),key=lambda j:abs((datetime.datetime.fromisoformat(h['time'][j]).replace(tzinfo=datetime.timezone.utc)-kt).total_seconds()));hour=datetime.datetime.fromisoformat(h['time'][i]).replace(tzinfo=datetime.timezone.utc);assert abs((hour-kt).total_seconds())<=3600,'Outside forecast horizon'
  return dict(row,city=co['name'],admin1=co.get('admin1'),latitude=co['latitude'],longitude=co['longitude'],forecast_hour_utc=h['time'][i],temperature_f=h['temperature_2m'][i],wind_mph=h['wind_speed_10m'][i],gust_mph=h['wind_gusts_10m'][i],precip_in=h['precipitation'][i],precip_probability=h['precipitation_probability'][i],source_url=url,note='City-resolution forecast near kickoff, not stadium microclimate or confirmed roof status. Facts only, no fitted numeric correction.')
 except Exception as ex:return dict(row,status='unavailable',reason=str(ex))
jobs=[('cfb',ev[i])for i in ids]+[('nfl',e)for e in nfl['events']]
with concurrent.futures.ThreadPoolExecutor(max_workers=32)as pool:rows=list(pool.map(one,jobs))
o=dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),label='WEATHER CONTEXT ONLY',numeric_adjustments=False,failed_weather_model_not_transferred=True,games=rows,cfb_schedule_source=cfurl,cfb_current_source_preserved='current_season_20261115 unchanged');(P/'weather_context.json').write_text(json.dumps(o,indent=2)+'\n');(S/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('weather rows',len(rows),'missing',sum(g['status']=='unavailable'for g in rows))
