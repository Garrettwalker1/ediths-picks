import json,pathlib,hashlib,datetime,gzip,collections,math
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent
for p in R.glob('tools/**/*sealed_research.sha256'):assert hashlib.sha256(p.with_suffix('.json').read_bytes()).hexdigest()==p.read_text().split()[0],str(p)
for m in json.load(open(P/'source_manifest.json')):
 f=P/m['file'];raw=gzip.decompress(f.read_bytes())if f.suffix=='.gz'else f.read_bytes();assert hashlib.sha256(raw).hexdigest()==m['sha256']
by={}
folders=['tools/cfb/boxscores','tools/cfb/current_inputs_20261016/boxscores','tools/cfb/saturday_20261107/sources']+sorted(str(p.relative_to(R))for p in (R/'tools/cfb').glob('week*_20*/boxscores'))
for folder in folders:
 for f in sorted(list((R/folder).glob('boxscore-*.json'))+list((R/folder).glob('boxscore-*.json.gz'))):
  d=json.load(gzip.open(f,'rt')if f.suffix=='.gz'else open(f));by[str(d['header']['id'])]=d
finals={e['id']:e for w in range(1,11)for e in json.load(open(P/f'sources/week{w}.json'))['events']if e['competitions'][0]['status']['type']['completed']};assert set(finals)==set(by);assert len(finals)==685
wins=collections.Counter();losses=collections.Counter()
for eid,e in finals.items():
 c=by[eid]['header']['competitions'][0];assert c['status']['type']['completed'];a={t['homeAway']:(t['team']['displayName'],float(t['score']))for t in c['competitors']};b={t['homeAway']:(t['team']['displayName'],float(t['score']))for t in e['competitions'][0]['competitors']};assert a==b,eid
 win,loss=sorted(a.values(),key=lambda t:t[1],reverse=True);wins[win[0]]+=1;losses[loss[0]]+=1
power=json.load(open(P/'power_ratings.json'));assert set(power['source_game_ids'])==set(finals);assert len(power['teams'])==138
for t in power['teams']:assert t['record']==f"{wins[t['team']]}-{losses[t['team']]}",t
assert len({r['rank']for r in power['teams']})==138
sealed=json.load(open(P/'week11_sealed_research.json'));freeze=json.load(open(P/'week11_dog_bucket_freeze.json'));assert len(sealed['games'])==67;assert len(freeze['games'])==67
cut=datetime.datetime.fromisoformat(sealed['protocol']['sealed_at']);members=set(json.load(open(P/'fbs_members.json')))
for g in sealed['games']:
 assert datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00'))>cut;assert g['home']in members and g['away']in members
 assert g['model_total'] is None and g['injury_adjusted_margin_home']is None and g['weather_adjusted_margin_home']is None
 assert 'd_ap_points'not in g['features'];assert all(math.isfinite(v)for v in g['features'].values());assert not any('book'in k or 'odds'in k for k in g['features'])
grade=json.load(open(P/'week10_forward_grade.json'));assert grade['all']['n']==62;assert len(grade['games'])==62
assert grade['all']['model_winner_hits']==sum(g['model_winner_hit']for g in grade['games'])
assert grade['all']['book_favorite_hits']==sum(g['book_winner_hit']for g in grade['games'])
assert grade['selection_time_dog_bucket']['n']==11 and grade['selection_time_dog_bucket']['model_winner_hits']==2
assert json.load(open(P/'week10_ap_forward_comparison.json'))['adopted']is False
print('PASS: all seals, source hashes, 685 scoreboard/boxscore IDs and scores, 138 records, current ranking coverage, 67 pregame forecasts, no AP/book features, null unsupported effects, Week10 grades and dog bucket')
