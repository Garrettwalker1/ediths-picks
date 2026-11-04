#!/usr/bin/env python3
"""Fail-closed current-season input refresh. Fixed coefficients, never fit/tune."""
import argparse,datetime as dt,hashlib,io,json,os,tempfile,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from engine import build,m,R
from fixed_inference import PARAMETERS
GAMES='https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'
STATS='https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv'
ALIAS={'WAS':'WSH','LAR':'LA'}
def team(s):return ALIAS.get(s,s)
def fetch(url):
 with urllib.request.urlopen(url,timeout=60) as res:return res.read()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def resolve(games,now):
 """Season from dated regular-season slate, including Jan of previous season."""
 g=games[games.game_type.eq('REG')].copy();g['date']=pd.to_datetime(g.gameday).dt.date
 future=g[g.date.ge(now.date())].sort_values(['date','week'])
 if future.empty:raise ValueError('No upcoming regular-season schedule')
 first=future.iloc[0];season,week=int(first.season),int(first.week)
 slate=g[g.season.eq(season)&g.week.eq(week)]
 # Midweek/in-progress slate must not silently advance to next week or consume partial-week stats.
 if slate.date.min()<now.date() or slate[['home_score','away_score']].notna().any().any():raise ValueError('Current slate has begun; weekly refresh requires explicit review')
 if not 1<=len(slate)<=16:raise ValueError('Implausible slate size')
 previous=g[g.season.eq(season)&g.week.lt(week)]
 if previous.empty or previous[['home_score','away_score']].isna().any().any():raise ValueError('Prior weeks not all final or no current-season history')
 return season,week,slate,previous

def prepare(raw,games,season,week,previous):
 raw=raw[raw.season_type.eq('REG')&((raw.season.lt(season))|(raw.season.eq(season)&raw.week.lt(week)))].copy()
 if raw.duplicated(['player_id','season','week']).any():raise ValueError('Duplicate player/week input')
 current=raw[raw.season.eq(season)]
 if current.empty or int(current.week.max())!=week-1:raise ValueError('Current-season weekly stats lag schedule')
 expected={(int(x.week),team(x.home_team)) for x in previous.itertuples()}|{(int(x.week),team(x.away_team)) for x in previous.itertuples()}
 found={(int(x.week),team(x.team)) for x in current.itertuples()}
 if expected-found:raise ValueError('Missing completed-game team stats: '+str(sorted(expected-found)))
 current_ids=set(current.game_id);expected_ids=set(previous.game_id)
 if current_ids!=expected_ids:raise ValueError('Completed game IDs do not match player-stat coverage')
 if raw[list(m.BASE_FEATURES)].isna().any().any():raise ValueError('Required weekly stat fields missing')
 return raw

def validate(o,old):
 p=o['players'];rows=o['matchup_context']['rows']
 if len(p)<150 or len(rows)<100 or len({x['player_id'] for x in p})!=len(p):raise ValueError('Coverage/identity guard')
 if sum(x['fantasy_rostered'] for x in p)<20:raise ValueError('Fantasy matching guard')
 if o['bust_model']!=old['bust_model'] or o['sportsbook']['active']:raise ValueError('Frozen evidence/book guard')
 for x in p:
  if x['position'] not in ['RB','WR','TE']:raise ValueError('Position scope')
  for k in ['anytime_td_probability','boom_probability','bust_probability']:
   if x[k] is not None and not 0<=x[k]<=1:raise ValueError('Probability range')
  for k in ['receiving_yards','rushing_yards','receptions']:
   if not 0<=x[k]['p20']<=x[k]['median']<=x[k]['p80']:raise ValueError('Interval order')
 if len(p)<.75*len(old['players']):raise ValueError('Large unexplained player coverage drop')
 json.dumps(o,allow_nan=False)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--now');ap.add_argument('--output',required=True,help='Candidate path; root production overwrite is forbidden');ap.add_argument('--sources-dir',required=True);a=ap.parse_args()
 out=Path(a.output).resolve();sources=Path(a.sources_dir).resolve()
 if out==(R/'player_projections.json').resolve():raise ValueError('Review separate candidate before production publication')
 sources.mkdir(parents=True,exist_ok=True)
 now=dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(ZoneInfo('America/Chicago'))
 if now.tzinfo is None:raise ValueError('now must have timezone')
 now=now.astimezone(ZoneInfo('America/Chicago'));ts=now.astimezone(dt.timezone.utc).isoformat()
 fantasy=json.loads((R/'fantasy.json').read_text());stamp=dt.datetime.fromisoformat(fantasy['updated_at'].replace('Z','+00:00'))
 expected_leagues={'espn-1242450525','espn-184489982','espn-416480692','espn-14911042','sleeper-1395822791856525312','sleeper-1389357500502917120','sleeper-1387915755609157632','sleeper-1386111628138782720'}
 if len(fantasy['leagues'])!=8 or {x['id'] for x in fantasy['leagues']}!=expected_leagues:raise ValueError('Exact expected eight-league set required')
 if not dt.timedelta(0)<=now-stamp<=dt.timedelta(days=4):raise ValueError('Fantasy snapshot older than four days or future-dated')
 if any(not l.get('players') for l in fantasy['leagues']):raise ValueError('Empty fantasy roster')
 manifest=[]
 def capture(url,name):
  blob=fetch(url);(sources/name).write_bytes(blob);manifest.append({'url':url,'path':name,'observed_at':ts,'sha256':hashlib.sha256(blob).hexdigest()});return blob
 games=pd.read_csv(io.BytesIO(capture(GAMES,'games.csv')));season,week,slate,previous=resolve(games,now)
 history=[]
 for year in range(2023,season+1):
  history.append(pd.read_csv(io.BytesIO(capture(STATS.format(season=year),f'stats_{year}.csv')),usecols=m.COLS,low_memory=False))
 raw=prepare(pd.concat(history,ignore_index=True),games,season,week,previous)
 expected_teams={team(x) for x in pd.concat([games[games.season.eq(season)].home_team,games[games.season.eq(season)].away_team]).unique()}
 if len(expected_teams)!=32:raise ValueError('Expected all 32 teams')
 rosters={}
 for code in sorted(expected_teams):
  url=f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{("lar" if code=="LA" else code.lower())}/roster';j=json.loads(capture(url,f'roster_{code}.json'))
  if team(j.get('team',{}).get('abbreviation'))!=code or not j.get('athletes'):raise ValueError('Roster team identity/coverage mismatch '+code)
  if int(j.get('season',{}).get('year',0))!=season:raise ValueError('Roster season mismatch '+code)
  rosters[code]=j
 opp={}
 for z in slate.itertuples():opp[team(z.home_team)]=team(z.away_team);opp[team(z.away_team)]=team(z.home_team)
 players,omitted,match=build(raw,rosters,fantasy,opp,season,week)
 old=json.loads((R/'player_projections.json').read_text());o=dict(old)
 o.update(generated_at=ts,headline=f'Week {week} generic player baselines: inputs through Week {week-1}',method_note=f'Fixed 2023-25 fitted specification unchanged. Rolling history through completed {season} Week {week-1}. Eight-league snapshot highlights, not live ownership or waiver availability. No refit, tuning, new validation, injury/workload/QB/opponent adjustment or book input. Fixed interval widths are research only. Generic TD logit differs from separate h12/k4 TD board.',players=players,sources=[{k:v for k,v in item.items() if k!='path'} for item in manifest],coverage={'modeled':len(players),'unranked':omitted,'fantasy_leagues':8,'fantasy_snapshot_at':fantasy['updated_at'],'fantasy_scope':'Dated roster highlights only, not live ownership; no fantasy writes','positions':['RB','WR','TE'],'quarterbacks':'Not covered by this generic generator'},matchup_context={'status':'descriptive_only','week':week,'history_seasons':[season],'method':f'Unchanged descriptive calculation using {season} finals through Week {week-1} and Week {week} opponent joins. Pre-game trailing eight-game expectations may include prior seasons. Not used in forecasts or a new validation claim.','heldout_result':old['matchup_context']['heldout_result'],'rows':match})
 validate(o,old)
 dump(sources/'fantasy_snapshot.json',fantasy);dump(sources/'manifest.json',{'season':season,'week':week,'completed_games':len(previous),'slate_games':len(slate),'fixed_parameters_sha256':hashlib.sha256(PARAMETERS.read_bytes()).hexdigest(),'sources':manifest})
 out.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=out.parent,prefix=out.name+'.');os.close(fd)
 try:dump(Path(tmp),o);os.replace(tmp,out)
 finally:
  if Path(tmp).exists():Path(tmp).unlink()
 print(json.dumps({'candidate':str(out),'season':season,'week':week,'players':len(players),'matchups':len(match),'unranked':len(omitted),'fantasy_snapshot_at':fantasy['updated_at']}))
if __name__=='__main__':main()
