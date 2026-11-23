import pathlib,json,hashlib,bs4,urllib.parse,collections,csv,gzip
P=pathlib.Path('/tmp/cfb-beyond-review');out={}
for slug,prefix in [('unt','North Texas'),('houston','Houston')]:
 h=json.load(open(P/(slug+'_official_lineup_harvest.json')));raw=[]
 for m in h['manifest']:
  b=(P/(slug+'-official-lineups')/(m['boxscore_id']+'.html')).read_bytes();assert hashlib.sha256(b).hexdigest()==m['sha256'];s=bs4.BeautifulSoup(b,'html.parser')
  for t in s.find_all('table'):
   label=t.get('aria-label','');import re
   if not re.sub(r'^#\d+\s+','',label).startswith(prefix+' ')or not any(k in label for k in['Starters','Player Participation']):continue
   for tr in t.select('tbody tr'):
    c=[x.get_text(' ',strip=True)for x in tr.find_all('td')]
    if not c:continue
    a=tr.find('a',href=True);raw.append(dict(source_url=m['url'],boxscore_id=m['boxscore_id'],table=label,jersey=c[0],name=c[1],position=c[2]if len(c)>2 else None,athlete_source_url=urllib.parse.urljoin(m['url'],a['href'])if a else None))
 assert raw==h['rows'];out[slug]={'games':len(h['manifest']),'rows':len(raw),'raw_rows_exact':True}
a=json.load(open(P/'two_team_official_lineup_adapter.json'))
for team in a['teams']:
 out[team['team_id']]={'rows':team['total_rows'],'matched':team['unique_matches'],'unresolved':[r for r in team['rows']if not r['espn_id']],'quality':team['quality_flags']}
r=json.load(open(P/'unt_verified_role_lineup_evidence.json'));stats=list(csv.DictReader(open('/tmp/edith/tools/cfb/current_season_20261123/current_player_games.csv')))
for b in r['baseline_passing']:
 rows=[x for x in stats if x['team']==b['team']and x['event_id']in b['history_event_ids']and x['date']<b['cutoff']];tot=collections.Counter()
 for x in rows:tot[x['player_id']]+=float(x['pass_att'])
 assert sum(tot.values())==b['passing_total'];assert all(tot[p['espn_id']]==p['pass_att']for p in b['passers'])
out['baseline_exact_live']=True;out['role_override_event_scope']=a['role_overrides'];out['rush_phase']=r['emergency_phase'];(P/'independent_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k!='rush_phase'},indent=2))
