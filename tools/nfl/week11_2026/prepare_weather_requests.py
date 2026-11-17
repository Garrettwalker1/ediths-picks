import pathlib,json,urllib.parse
P=pathlib.Path(__file__).parent;R=P.parents[2];geo=json.load(open(P/'weather_geocode_requests.json'));allgeo={}
for f in pathlib.Path('/tmp').glob('wg-*.txt'):
 url=None
 for line in f.read_text().splitlines():
  if line.startswith('https://geocoding-api'):url=line.strip()
  if line.startswith('{'):
   try:allgeo[url]=json.loads(line)
   except json.JSONDecodeError:pass
states={'OH':'Ohio','NC':'North Carolina','IL':'Illinois','CO':'Colorado','NY':'New York','CA':'California','FL':'Florida','KS':'Kansas','PA':'Pennsylvania','DC':'Washington, D.C.','MD':'Maryland','MO':'Missouri','Mexico City':'Mexico City'};coords={}
for f in (R/'tools/cfb').glob('**/*coords*.json'):coords.update(json.load(open(f)))
for vid,x in geo.items():
 res=allgeo.get(x['url'],{}).get('results',[]);match=[r for r in res if r.get('country_code')==('MX'if x['country']in['Mexico','MEX']else'US')and r['name'].lower()==x['city'].lower()and r.get('admin1')==states.get(x['state'],x['state'])]
 if len(match)!=1:print('geoheld',vid,x['city'],x['state'],[(r['name'],r.get('admin1'),r.get('country_code'))for r in res[:4]]);continue
 r=match[0];coords[vid]={k:r[k]for k in ['name','latitude','longitude','admin1']};coords[vid]['source_url']=x['url']
j=json.load(open(R/'tools/cfb/current_season_20261115/sources/week12.json'));ids={g['event_id']for g in json.load(open(R/'tools/cfb/current_season_20261115/current_forecasts.json'))['games']};events=[e for e in j['events']if e['id']in ids]+json.load(open(R/'tools/nfl/current_season_20261117/sources/week11.json'))['events'];req={}
for e in events:
 v=e['competitions'][0]['venue'];co=coords.get(v['id'])
 if not co or v.get('indoor'):continue
 url=f"https://api.open-meteo.com/v1/forecast?latitude={co['latitude']}&longitude={co['longitude']}&hourly=temperature_2m%2Cprecipitation_probability%2Cprecipitation%2Cwind_speed_10m%2Cwind_gusts_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=UTC"
 req[e['id']]=dict(url=url,coords=co)
(P/'weather_forecast_requests.json').write_text(json.dumps(req,indent=2)+'\n');(P/'weather_coords.json').write_text(json.dumps(coords,indent=2)+'\n');urls=sorted({x['url']for x in req.values()});d=pathlib.Path('/tmp/weekly-wx');d.mkdir(exist_ok=True)
for i in range(0,len(urls),5):(d/f'batch-{i//5:02d}.txt').write_text('\n'.join(urls[i:i+5]))
print('forecastbatches',(len(urls)+4)//5,'events',len(req))
