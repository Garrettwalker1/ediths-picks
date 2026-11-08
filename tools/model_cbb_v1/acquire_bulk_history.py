#!/usr/bin/env python3
"""Bounded public SportsDataverse season assets. No model fitting or evaluation.
Three release metadata requests, at most 12 sequential assets. Cache verified files.
Stop on 403/429 or any download error, never bypass challenges or retry bursts.
"""
import pathlib,json,urllib.request,hashlib,datetime,time,argparse
R=pathlib.Path(__file__).resolve().parent/'data/bulk'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fetch(u):
 req=urllib.request.Request(u,headers={'User-Agent':'edith-cbb-research (public bulk collection)'})
 with urllib.request.urlopen(req,timeout=90) as r:return r.read()
def main():
 R.mkdir(parents=True,exist_ok=True);p=R/'manifest.json';m=json.loads(p.read_text()) if p.exists() else {'source':'SportsDataverse ESPN-derived public release assets','season_key':'Ending year, 2023 means 2022-23','assets':{},'warning':'Postgame historical data, not authenticated point-in-time features. No held-out evaluation.'}
 for kind,prefix in [('schedules','mbb_schedule'),('team_boxscores','team_box'),('player_boxscores','player_box')]:
  tag='espn_mens_college_basketball_'+kind;url='https://api.github.com/repos/sportsdataverse/sportsdataverse-data/releases/tags/'+tag
  release=json.loads(fetch(url));time.sleep(1)
  for year in range(2023,2027):
   name=f'{prefix}_{year}.parquet';dest=R/name;old=m['assets'].get(name)
   if old and dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==old['sha256']:continue
   a=next(a for a in release['assets'] if a['name']==name);started=now();b=fetch(a['browser_download_url']);assert len(b)==a['size'];assert b[:4]==b'PAR1';dest.write_bytes(b)
   m['assets'][name]={'url':a['browser_download_url'],'release_url':release['html_url'],'asset_updated_at':a['updated_at'],'requested_at':started,'received_at':now(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};m['updated_at']=now();p.write_text(json.dumps(m,indent=2));print(name,len(b),flush=True);time.sleep(1)
if __name__=='__main__':main()
