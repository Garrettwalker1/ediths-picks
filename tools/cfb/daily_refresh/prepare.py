#!/usr/bin/env python3
"""Prepare a new dated CFB stats/roster release. Never overwrite prior releases or publish.
Run once daily; review and publish only after source, chronology, seal and UI checks.
No odds, prior-season feature profiles, preseason talent or injury point guesses.
"""
import pathlib,json,urllib.request,datetime,hashlib,gzip,shutil,concurrent.futures,subprocess,os
from zoneinfo import ZoneInfo
R=pathlib.Path(__file__).resolve().parents[3];day=datetime.datetime.now(ZoneInfo('America/Chicago')).date();tag=day.strftime('%Y%m%d');release=json.load(open(R/'cfb_current_release.json'));old=R/release['forecast_path'];oldp=old.parent
P=R/f'tools/cfb/current_season_{tag}';W=R/f'tools/cfb/week_daily_{tag}'
if P.exists():raise SystemExit('Dated release already exists; inspect it, never overwrite or silently reissue.')
P.mkdir();W.mkdir();(W/'sources').mkdir();(W/'boxscores').mkdir();(P/'sources').mkdir();manifest=[]
def fetch(url,path):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();raw=urllib.request.urlopen(url,timeout=30).read();path.write_bytes(raw);manifest.append(dict(url=url,requested_at=start,received_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),file=str(path.relative_to(R))));return json.loads(raw)
probe=fetch('https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates='+tag+'&groups=80&limit=400',W/'sources/date-probe.json');week=int(probe['week']['number']);year=int(probe['season']['year']);assert year==2026,'Season change requires review, not silent reuse.'
# A full remaining-week slate. If this week is finished, prepare the next week.
score={w:fetch(f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year={year}&seasontype=2&week={w}&groups=80&limit=400',W/f'sources/week{w}.json')for w in range(1,week+1)}
slate=score[week]
if not any(e['competitions'][0]['status']['type']['state']=='pre'for e in slate['events']):
 week+=1;slate=fetch(f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year={year}&seasontype=2&week={week}&groups=80&limit=400',W/f'sources/week{week}.json');score[week]=slate
(P/'sources/slate.json.gz').write_bytes(gzip.compress((json.dumps(slate)+'\n').encode(),mtime=0))
standurl=f'https://site.api.espn.com/apis/v2/sports/football/college-football/standings?season={year}&type=0&level=3';fetch(standurl,W/'sources/standings.json');fetch(f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings?season={year}&seasontype=2&week={week}',W/'sources/ap_rankings.json')
previous_rank=R/release['rankings_path'];known=set(json.load(open(previous_rank))['source_game_ids']);finals={e['id']:e for d in score.values()for e in d['events']if e['competitions'][0]['status']['type']['completed']};assert known<=set(finals),'A prior final vanished from current scoreboard coverage.';missing=sorted(set(finals)-known)
def summary(eid):
 d=fetch('https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event='+eid,W/f'boxscores/boxscore-{eid}.json');assert str(d['header']['id'])==eid and d['header']['competitions'][0]['status']['type']['completed'];assert d['boxscore'].get('players');return eid
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as ex:list(ex.map(summary,missing))
(W/'fetch_audit.json').write_text(json.dumps(dict(collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),finals=len(finals),ids=sorted(finals),new_fetched=len(missing),failures=[],standings_url=standurl),indent=2)+'\n');(W/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Losslessly compress fetched bodies and retain both original and stored hashes.
for row in manifest:
 f=R/row['file'];raw=f.read_bytes();target=f.with_suffix(f.suffix+'.gz');target.write_bytes(gzip.compress(raw,mtime=0));row['storage_path']=str(target.relative_to(R));row['stored_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();f.unlink()
(W/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for f in ['fixed_reference_ratings.json','fbs_members.json']:shutil.copy2(previous_rank.parent/f,W/f)
shutil.copy2(oldp/'canonical_used.json.gz',P/'canonical_input.json.gz')
for name in ['build.py','verify.py','rosters.py']:
 s=(oldp/name).read_text().replace("sources/week12.json","sources/slate.json")
 if name=='build.py':
  s=s.replace("'source_cutoff':'Allcompletedeligible2026FBS-versus-FBSfinalsthroughNov20_2026_at_source_receipt'","'source_cutoff':'Completed eligible 2026 FBS-versus-FBS finals through '+now").replace('2023throughNov20,2026','2023 through the current source cutoff in 2026')
 (P/name).write_text(s)
# Same ranking method, a new source cutoff. No changes to the historical method or archived comparisons.
s=(previous_rank.parent/'performance_top25.py').read_text();import re
s=re.sub(r"SOURCE_CUTOFF_UTC = .*",'SOURCE_CUTOFF_UTC = '+repr(datetime.datetime.now(datetime.timezone.utc).isoformat()),s);s=re.sub(r"AS_OF = .*",'AS_OF = '+repr(str(day)),s);s=s.replace("int(WEEK_DIR.name.split('_')[0].replace('week',''))",str(week+1));(W/'performance_top25.py').write_text(s)
for args in [[str(P/'build.py')],[str(P/'rosters.py')],[str(P/'verify.py')],[str(W/'performance_top25.py'),str(W)]]:subprocess.run(['python',*args],cwd=R,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'},check=True)
print(json.dumps({'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_forecast_dir':str(P),'new_source_dir':str(W),'new_final_ids':missing,'finals':len(finals),'week':week,'not_published':True,'next':'Refresh availability with collect_availability.py, review all coverage and immutable prior releases, add metadata/receipts/seal, then update current-release pointer and rankings embed, render and inspect, publish and verify.'},indent=2))
