import urllib.request,json,pathlib,datetime,hashlib,concurrent.futures
P=pathlib.Path(__file__).parent/'sources';P.mkdir(exist_ok=True)
def fetch(url,path):
 raw=urllib.request.urlopen(url,timeout=30).read();path.write_bytes(raw);return {'url':url,'file':str(path.name),'received_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest()}
u='https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week=11&groups=80&limit=400';m=[fetch(u,P/'week11.json')];d=json.load(open(P/'week11.json'));events=d['events'];fin=[e for e in events if e['competitions'][0]['status']['type']['completed']];print('finals',len(fin),'events',len(events))
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 jobs=[pool.submit(fetch,'https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event='+e['id'],P/('boxscore-'+e['id']+'.json'))for e in fin]
 for job in jobs:m.append(job.result())
(P/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print('done',len(m))
