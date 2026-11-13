import pathlib,json,urllib.request,concurrent.futures,datetime,hashlib
P=pathlib.Path(__file__).parent;D=P/'sources/rosters';D.mkdir(exist_ok=True);events=json.load(open(P/'sources/week11.json'))['events'];teams={c['team']['id']:c['team']['displayName']for e in events if e['competitions'][0]['status']['type']['state']=='pre'for c in e['competitions'][0]['competitors']};m=[]
def fetch(it):
 tid,name=it;url='https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/'+tid+'/roster?season=2026&limit=500'
 try:
  raw=urllib.request.urlopen(url,timeout=20).read();d=json.loads(raw);(D/(tid+'.json')).write_bytes(raw);ath=[a for group in d.get('athletes',[])for a in group.get('items',[])];return dict(team=name,team_id=tid,url=url,received_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),season=d.get('season'),player_count=len(ath),player_ids=[str(a['id'])for a in ath])
 except Exception as e:return dict(team=name,team_id=tid,url=url,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:m=list(pool.map(fetch,teams.items()))
(P/'current_roster_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print('rosters',len(m),'failed',sum('error'in x for x in m),'empty',sum(not x.get('player_count')for x in m))
