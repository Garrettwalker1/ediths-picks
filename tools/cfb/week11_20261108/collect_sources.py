import pathlib,json,gzip,urllib.request,hashlib,datetime,concurrent.futures
R=pathlib.Path(__file__).resolve().parents[3];P=R/'tools/cfb/week11_20261108';(P/'sources').mkdir(parents=True,exist_ok=True);(P/'boxscores').mkdir(exist_ok=True);manifest=[]
def get(u,dest):
 st=datetime.datetime.now(datetime.timezone.utc).isoformat();b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'edith-research'}),timeout=40).read();j=json.loads(b);dest.write_bytes(gzip.compress(b) if dest.suffix=='.gz' else b);manifest.append({'url':u,'requested_at':st,'received_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(b).hexdigest(),'file':str(dest.relative_to(P))});return j
slates={}
for w in range(1,12):slates[w]=get(f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week={w}&groups=80&limit=400',P/'sources'/f'week{w}.json')
standurl='https://site.api.espn.com/apis/v2/sports/football/college-football/standings?season=2026&type=0&level=3';get(standurl,P/'sources/standings.json')
get('https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings?season=2026&seasontype=2&week=11',P/'sources/ap_rankings.json')
existing={}
for f in list((R/'tools/cfb').rglob('boxscore-*.json'))+list((R/'tools/cfb/saturday_20261107/sources').glob('boxscore-*.json.gz')):
 try:
  d=json.load(gzip.open(f,'rt') if f.suffix=='.gz' else open(f));c=d['header']['competitions'][0]
  if c['status']['type']['completed']:existing[str(d['header']['id'])]=f
 except:pass
finals={e['id']:e for s in slates.values() for e in s['events'] if e['competitions'][0]['status']['type']['completed']};missing=set(finals)-set(existing);fails=[]
def one(eid):
 try:get('https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event='+eid,P/'boxscores'/('boxscore-'+eid+'.json'));return eid
 except Exception as e:fails.append({'event_id':eid,'error':str(e)})
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(one,sorted(missing)))
audit={'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'finals':len(finals),'ids':sorted(finals),'new_fetched':len(missing)-len(fails),'failures':fails,'not_final_week10':[e['id'] for e in slates[10]['events'] if not e['competitions'][0]['status']['type']['completed']],'standings_url':standurl,'source_count':len(manifest)};(P/'fetch_audit.json').write_text(json.dumps(audit,indent=2));(P/'source_manifest.json').write_text(json.dumps(manifest,indent=2));print(audit)
for name in ['fbs_members.json','fixed_reference_ratings.json']:(P/name).write_bytes((R/'tools/cfb/week10_20261101'/name).read_bytes())
