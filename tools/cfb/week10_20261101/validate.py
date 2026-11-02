import pathlib,json,hashlib,datetime,subprocess,math
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).parent
for p in R.glob('tools/**/*sealed_research.sha256'):
 f=p.with_suffix('.json');assert hashlib.sha256(f.read_bytes()).hexdigest()==p.read_text().split()[0],str(f)
d=json.load(open(P/'week10_sealed_research.json'));seen=set();cut=datetime.datetime.fromisoformat(d['protocol']['sealed_at'])
for g in d['games']:
 assert g['event_id'] not in seen;seen.add(g['event_id']);assert datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00'))>cut
 assert all(math.isfinite(x) for x in g['predicted_margin_home'].values());assert g['model_total'] is None and g['injury_adjusted_margin_home'] is None and g['weather_adjusted_margin_home'] is None
 assert not any('book' in k or 'odds' in k for k in g['features'])
power=json.load(open(P/'power_ratings.json'));assert len(power['teams'])==138
assert len(d['games'])==62 and d['protocol']['coverage']['scheduled']==63
f=P/'week10_dog_bucket_freeze.json';freeze=json.load(open(f));assert len(freeze['games'])==len(d['games']);assert freeze['sealed_at']==d['protocol']['sealed_at']
for g in freeze['games']:
 bl=g['book_home_line'];assert g['dog_bucket']==(None if bl is None or bl==0 else g['model_pick']==g['book_underdog'])
print('PASS: prior seals, pregame chronology, unique events, finite forecasts, null unsupported adjustments/totals, comparison-only book, membership and dog-bucket freeze')
