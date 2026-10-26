"""Week 9 WX UNPROVEN overlay: sealed baselines + failed-validation weather candidate delta.
Candidate: residual Ridge(alpha=10, no intercept) on wind/10*d_pass_share and wet(>=.01in)*d_pass_share.
FAILED 2024 validation (MAE delta +0.010, CI95 crosses 0); 2025 inconclusive. Exploratory display only - not a bet signal.
Baselines come from the sealed file and are never modified. Rerun any time to refresh forecast snapshots."""
import json, csv, pathlib, datetime, urllib.request, urllib.parse, time
P=pathlib.Path(__file__).resolve().parent; R=P.parents[2]
COEF=json.load(open(R/'tools/model_cfb_v2/weather_candidate/weather-candidate.json'))['live_raw_coefficients']
sealed=json.load(open(P/'week9_sealed_research.json'))
slate=json.load(open(P/'sources/week9.json'))
feat={r['team']:r for r in csv.DictReader(open(P/'current_team_features.csv'))}
try: coords=json.load(open(R/'tools/cfb/current_inputs_20261016/current-coords.json'))
except FileNotFoundError: coords={}
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'edith-cfb-wx/1.0'})
    return json.load(urllib.request.urlopen(req, timeout=25))
now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def geocode(vid, city, state):
    if vid in coords: return coords[vid], False
    q=urllib.parse.quote(city)
    d=get(f'https://geocoding-api.open-meteo.com/v1/search?name={q}&count=10&language=en&format=json&countryCode=US')
    res=d.get('results') or []
    pick=None
    for r in res:
        if state and r.get('admin1','').lower()==state.lower(): pick=r; break
    if pick is None and res: pick=res[0]
    if pick is None: raise RuntimeError(f'geocode failed for {city}, {state}')
    c={'latitude':pick['latitude'],'longitude':pick['longitude'],'name':pick['name'],'admin1':pick.get('admin1',''),'resolution':'city forecast, not stadium microclimate','geocoding_source':'Open-Meteo geocoding'}
    coords[vid]=c
    return c, True
fcast={}
def forecast(lat, lon):
    key=f'{lat:.4f},{lon:.4f}'
    if key in fcast: return fcast[key]
    d=get(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=UTC')
    fcast[key]=d; time.sleep(0.15); return d
def share(t):
    r=feat[t]; py=float(r['pyf_r4']); ry=float(r['ryf_r4'])
    return py/(py+ry) if (py+ry) else 0.0
games=[]; new_geo=0; missing=[]
slate_by_id={e['id']:e for e in slate['events']}
for g in sealed['games']:
    e=slate_by_id[g['event_id']]; c=e['competitions'][0]; v=c.get('venue') or {}
    vid=str(v.get('id')); addr=v.get('address') or {}
    indoor=bool(v.get('indoor'))
    try:
        loc, isnew=geocode(vid, addr.get('city',''), addr.get('state',''))
        new_geo+=isnew
    except Exception as ex:
        missing.append({'event_id':g['event_id'],'name':g['name'],'reason':str(ex)}); continue
    d=forecast(loc['latitude'], loc['longitude']); h=d['hourly']
    kt=datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00')).replace(tzinfo=None)
    times=[datetime.datetime.fromisoformat(t) for t in h['time']]
    i=min(range(len(times)), key=lambda j:abs((times[j]-kt).total_seconds()))
    win=range(i, min(i+5, len(times)))
    temp=h['temperature_2m'][i]; wind=h['wind_speed_10m'][i]; precip=h['precipitation'][i]
    rain_chance=max(x for x in (h['precipitation_probability'][j] for j in win) if x is not None) if any(h['precipitation_probability'][j] is not None for j in win) else None
    rain_in=sum(h['precipitation'][j] or 0 for j in win)
    wind_max=max(h['wind_speed_10m'][j] or 0 for j in win); gust_max=max(h['wind_gusts_10m'][j] or 0 for j in win)
    sd=share(g['home'])-share(g['away'])
    delta=0.0 if indoor else (wind/10.0)*sd*COEF['wind_pass'] + (1.0 if precip>=0.01 else 0.0)*sd*COEF['wet_pass']
    base=g['predicted_margin_home']['2026_no_ap']
    games.append({'event_id':g['event_id'],'name':g['name'],'date':g['date'],
        'venue':{'id':vid,'fullName':v.get('fullName'),'indoor':indoor,'city':addr.get('city'),'state':addr.get('state')},
        'location':loc,'kickoff_forecast_hour_utc':h['time'][i],
        'temperature_f':temp,'wind_mph_kickoff':wind,'precip_in_kickoff':precip,
        'window':{'rain_chance_max':rain_chance,'rain_inches':round(rain_in,3),'wind_max_mph':wind_max,'gust_max_mph':gust_max},
        'pass_share_diff_home':sd,'baseline_margin_home_raw':base,
        'weather_delta_home_raw':delta,'weather_margin_home_raw':base+delta,
        'label':'WX UNPROVEN','failed_validation':True,
        'note':'Failed 2024 validation (paired MAE delta +0.010, CI95 crosses zero); 2025 comparison inconclusive; historical fit used observed weather, not archived forecasts. Exploratory only - not a bet signal. Baseline sealed forecast unchanged.'})
out={'built_at':now,'source':'Open-Meteo hourly forecast (https://open-meteo.com/en/docs), city resolution, not stadium microclimate','coefficients':COEF,'games':games,'venues_missing_coords':missing}
(P/'week9_weather_overlay.json').write_text(json.dumps(out, indent=1))
json.dump(coords, open(R/'tools/cfb/current_inputs_20261016/current-coords.json','w'), indent=1)
print('games:', len(games), '| new geocodes:', new_geo, '| missing:', len(missing))
big=[x for x in games if abs(x['weather_delta_home_raw'])>=1]
print('games with |delta|>=1:', len(big))
for x in big: print(' ', x['name'], '| wind', x['wind_mph_kickoff'], 'precip', x['precip_in_kickoff'], '| delta', round(x['weather_delta_home_raw'],3))
