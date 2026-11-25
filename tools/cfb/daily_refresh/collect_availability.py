from zoneinfo import ZoneInfo
import pathlib,json,requests,datetime,gzip,hashlib,concurrent.futures,unicodedata,re,bs4,collections,sys
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(sys.argv[1]);D=P/'sources/injuries';D.mkdir(exist_ok=True);root=D/'discovery';root.mkdir(exist_ok=True);checked=datetime.datetime.now(datetime.timezone.utc).isoformat();slate=P/'sources/slate.json.gz';slate=slate if slate.exists()else P/'sources/week12.json.gz';events=[e for e in json.load(gzip.open(slate,'rt'))['events']if e['competitions'][0]['status']['type']['state']=='pre'];teams={}
primary_receipts=[]
def normalized(v):
 if isinstance(v,dict):return{k:normalized(x)for k,x in v.items()if not any(n in k.lower()for n in ['image','logo','font','color','style'])}
 if isinstance(v,list):return[normalized(x)for x in v]
 return v
raw=requests.get('https://kickoffstatus.com/',timeout=25);raw.raise_for_status();(root/'kickoff.html').write_bytes(raw.content)
for conf,file in [('SEC','sec-publish.json'),('ACC','ACC-publish.json')]:
 r=requests.post('https://app.hdintelligence.com/api/public-load',json=dict(conference_param=conf,sport_param='Football',type_param='report',referrer='',source=conf),timeout=25);r.raise_for_status();assert r.json().get('public')
 r=requests.post('https://app.hdintelligence.com/api/get-publish-public',json=dict(sport='Football',organization=conf,conference=conf),timeout=25);r.raise_for_status();body=json.dumps(normalized(r.json()),sort_keys=True,separators=(',',':')).encode();(root/file).write_bytes(body);primary_receipts.append(dict(conference=conf,original_response_sha256=hashlib.sha256(r.content).hexdigest(),normalized_data_sha256=hashlib.sha256(body).hexdigest(),normalization='Presentation image/logo/font/color/style fields omitted only; all report data retained. Not a raw-byte archive.'))

def norm(x):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower())
for e in events:
 for c in e['competitions'][0]['competitors']:
  t=c['team']
  for k in ['displayName','shortDisplayName','location']:teams[norm(t[k])]=t['displayName']
for k,v in {'Miami (FL)':'Miami Hurricanes','Florida St.':'Florida State Seminoles','Hawaiʻi':"Hawai'i Rainbow Warriors",'FIU':'Florida International Panthers','Texas A&M':'Texas A&M Aggies'}.items():teams[norm(k)]=v
s=bs4.BeautifulSoup((root/'kickoff.html').read_text(),'html.parser');links={a['href'] for a in s.find_all('a',href=True)if any(a['href'].startswith('/games/'+datetime.datetime.fromisoformat(e['competitions'][0]['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Chicago')).date().isoformat()+'-')for e in events)};manifest=[]
def read(href):
 u='https://kickoffstatus.com'+href;raw=requests.get(u,timeout=25);raw.raise_for_status();s=bs4.BeautifulSoup(raw.text,'html.parser');fn=href.strip('/').split('/')[-1]+'.html.gz';(D/fn).write_bytes(gzip.compress(raw.content,mtime=0));entry=dict(url=u,received_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_sha256=hashlib.sha256(raw.content).hexdigest(),storage_path='sources/injuries/'+fn);manifest.append(entry);out=[];text=s.get_text(' ',strip=True);m=re.search(r'Latest: (.*?) Who',text);posted=m.group(1)if m else 'Report time unavailable';source=[a['href'] for a in s.find_all('a',href=True)if a.get_text(' ',strip=True).startswith('view it on')]
 for h in s.find_all('h3'):
  a=h.find('a',href=True)
  if not a or not a['href'].startswith('/teams/'):continue
  key=norm(a.get_text(' ',strip=True));assert key in teams,(key,u);tm=teams[key];tab=h.parent.find('table');rows=[]
  if tab:
   for tr in tab.select('tbody tr'):
    cells=tr.find_all('td');assert len(cells)>=3
    rows.append(dict(player=cells[0].get_text(' ',strip=True),position=cells[1].get_text(' ',strip=True),status=cells[2].get_text(' ',strip=True)))
  out.append(dict(team=tm,rows=rows,evidence_level='secondary_republication_unverified_against_primary',source_url=u,claimed_primary_url=source[0]if source else None,report_posted_text=posted,site_updated_at=s.find('time').get('datetime')if s.find('time')else None,checked_at=entry['received_at'],coverage='listed_designations_only'if rows else 'no_published_designations_unknown_not_healthy',numeric_adjustment=None))
 return out
allrows=[];fail=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as ex:
 fs={ex.submit(read,h):h for h in sorted(links)}
 for f in concurrent.futures.as_completed(fs):
  try:allrows.extend(f.result())
  except Exception as e:fail.append(dict(path=fs[f],error=str(e)))
primary=[]
for conf,file,source in [('SEC','sec-publish.json','https://www.secsports.com/fbreports'),('ACC','ACC-publish.json','https://theacc.com/sports/2025/8/28/availability-reporting-football.aspx')]:
 raw=(root/file).read_bytes();(D/(conf+'-official-public.json.gz')).write_bytes(gzip.compress(raw,mtime=0));d=json.loads(raw)
 for rid,r in d.items():
  for t in r['games']:
   key=norm(t['teamName']);
   if key not in teams:continue
   source_names={norm(x['teamName'])for x in r['games']};matches=[e for e in events if datetime.datetime.fromisoformat(e['competitions'][0]['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Chicago')).date().isoformat()==r['footer']['date']and {teams.get(n,n)for n in source_names}=={c['team']['displayName']for c in e['competitions'][0]['competitors']}];
   if len(matches)!=1:continue
   primary.append(dict(team=teams[key],rows=[dict(player=x['name'],status=x['status'],position=None)for x in t['rows']],evidence_level='primary_conference_public_distributor',source_url=source,distributor_url='https://app.hdintelligence.com/api/get-publish-public',public_read_parameters=dict(sport='Football',organization=conf,conference=conf),report_id=rid,report_type=r['ReportType'],report_date=r['publishDate'],report_time=r['postedTime'],report_timezone=r['conferenceTimeZone'],checked_at=checked,coverage='listed_designations_only',numeric_adjustment=None))
by={x['team']:x for x in allrows};by.update({x['team']:x for x in primary});allteams=sorted({c['team']['displayName']for e in events for c in e['competitions'][0]['competitors']});missing=[t for t in allteams if t not in by]
for t in missing:by[t]=dict(team=t,rows=[],evidence_level='unavailable',coverage='unknown_not_healthy',checked_at=checked,numeric_adjustment=None)
games=[]
for e in events:
 c=e['competitions'][0];t={z['homeAway']:z['team']['displayName']for z in c['competitors']};games.append(dict(event_id=e['id'],date=c['date'],home=t['home'],away=t['away'],teams=[by[t['away']],by[t['home']]],numeric_adjustment=None))
out=dict(generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Current listed availability designations only, not injury severity, confirmed starters, replacement quality or an adjusted forecast. Secondary reports labeled; missing/unlisted never inferred healthy. Unofficial stale notes excluded.',games=games,coverage=dict(upcoming_games=len(games),teams=len(allteams),primary_teams=sum(x['evidence_level'].startswith('primary')for x in by.values()),secondary_teams=sum(x['evidence_level'].startswith('secondary')for x in by.values()),teams_with_designations=sum(bool(x['rows'])for x in by.values()),no_designations=sum(not x['rows']for x in by.values()),missing_source_teams=missing,fetch_failures=fail),manifest=manifest)

for g in games:
 for t in g['teams']:
  t['explicit_available_count']=sum(x['status']=='Available'for x in t['rows']);t['exempt_count_not_health_clearance']=sum(x['status']=='Exempt'for x in t['rows']);t['rows']=[x for x in t['rows']if x['status']not in ['Available','Exempt']]
by={t['team']:t for g in games for t in g['teams']};out['coverage']['teams_with_designations']=sum(bool(x['rows'])for x in by.values());out['coverage']['no_designations']=sum(not x['rows']for x in by.values());out['coverage']['listed_nonavailable_players']=sum(len(x['rows'])for x in by.values());
# Pending schedules are not issued reports, and future publication times carry no clearance.
for g in games:
 for t in g['teams']:
  if t.get('report_id'):
   conf=t['public_read_parameters']['conference'];t['raw_source_path']='sources/injuries/'+conf+'-official-public.json.gz'
   zone=ZoneInfo('America/Chicago' if t['report_timezone']=='CT' else 'America/New_York')
   posted=datetime.datetime.fromisoformat(t['report_date']+'T'+t['report_time']).replace(tzinfo=zone)
   if 'pending' in t['report_type'].lower() or posted>datetime.datetime.fromisoformat(t['checked_at']):
    assert not t['rows'],'Pending/future report unexpectedly has rows'
    t.update(evidence_level='unavailable',coverage='official_report_pending_not_issued_not_health_clearance',primary_schedule_pending=True)
  if not t['rows'] and not t.get('primary_schedule_pending'):
   t['coverage']='no_current_listed_designations_not_health_clearance'
by={t['team']:t for g in games for t in g['teams']}
out['coverage'].update(primary_teams=sum(t['evidence_level'].startswith('primary')for t in by.values()),official_pending_teams=sum(bool(t.get('primary_schedule_pending'))for t in by.values()),status_counts=dict(collections.Counter(r['status']for t in by.values()for r in t['rows'])))
(P/'injury_designations.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['coverage'],indent=2));print('status counts',collections.Counter(r['status']for x in by.values()for r in x['rows']));print('pending',[x['team']for x in by.values()if not x['rows']])

(P/'injury_primary_source_receipts.json').write_text(json.dumps(primary_receipts,indent=2)+'\n')
for f in root.iterdir():f.unlink()
root.rmdir()
