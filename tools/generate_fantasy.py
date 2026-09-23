#!/usr/bin/env python3
"""Build the public fantasy.json snapshot without storing credentials.

Authenticated ESPN collection happens in the cloud browser and is passed in as a
normalized JSON file. Sleeper is refreshed from its public API here. The injury
pass consumes Markdown from the current ESPN NFL injury page (saved by the live
web fetch tool) and intersects it with rostered players only.
"""
import argparse, copy, datetime as dt, json, re, sys, urllib.request
from pathlib import Path

SLEEPER_USER = "garrettwalker1"
SLEEPER_LEAGUES = [
    ("1395822791856525312", 8, "FTB Fantasy Re-Draft", "2026-09-07T18:30:00-05:00"),
    ("1389357500502917120", 4, "Billions", None),
    ("1387915755609157632", 4, "National Choochers Association", None),
    ("1386111628138782720", 5, "For The Boys: Fantasy", None),
]
MONTHS = {m:i+1 for i,m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}

def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ediths-picks-fantasy-sync/1.0'})
    with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def write_atomic(path,obj):
    p=Path(path); q=p.with_suffix(p.suffix+'.tmp'); q.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n'); q.replace(p)
def sleeper_snapshot(ts, player_db):
    out=[]
    for lid,rid,fallback,draft_at in SLEEPER_LEAGUES:
        league=get(f'https://api.sleeper.app/v1/league/{lid}')
        rosters=get(f'https://api.sleeper.app/v1/league/{lid}/rosters')
        users=get(f'https://api.sleeper.app/v1/league/{lid}/users')
        roster=next((r for r in rosters if r.get('roster_id')==rid),None)
        if roster is None: raise RuntimeError(f'Sleeper roster {rid} missing in {lid}')
        user=next((u for u in users if u.get('user_id')==roster.get('owner_id')),{})
        team_name=(user.get('metadata') or {}).get('team_name') or user.get('display_name') or SLEEPER_USER
        status=league.get('status') or 'unknown'; week=(league.get('settings') or {}).get('leg')
        match=None
        if week and status in ('in_season','post_season','complete'):
            rows=get(f'https://api.sleeper.app/v1/league/{lid}/matchups/{week}')
            mine=next((x for x in rows if x.get('roster_id')==rid),None)
            opp=next((x for x in rows if mine and x.get('matchup_id')==mine.get('matchup_id') and x.get('roster_id')!=rid),None)
            if mine:
                oname='Opponent TBD'
                if opp:
                    oroster=next((r for r in rosters if r.get('roster_id')==opp.get('roster_id')),{})
                    ouser=next((u for u in users if u.get('user_id')==oroster.get('owner_id')),{})
                    oname=(ouser.get('metadata') or {}).get('team_name') or ouser.get('display_name') or oname
                match={'week':week,'opponent':oname,'score':mine.get('points'),'opponent_score':opp.get('points') if opp else None,'state':('upcoming' if not mine.get('points') and not (opp or {}).get('points') else 'live'),'source':'Sleeper','source_url':f'https://api.sleeper.app/v1/league/{lid}/matchups/{week}','observed_at':ts,'provider_updated_at':None}
        starters=set(roster.get('starters') or []); reserve=set(roster.get('reserve') or []); taxi=set(roster.get('taxi') or [])
        players=[]
        for pid in roster.get('players') or []:
            p=player_db.get(str(pid),{}); name=(p.get('full_name') or ' '.join(x for x in [p.get('first_name'),p.get('last_name')] if x) or str(pid))
            slot='START' if pid in starters else ('IR' if pid in reserve else ('TAXI' if pid in taxi else 'BENCH'))
            players.append({'id':str(pid),'name':name,'position':p.get('position'),'nfl_team':p.get('team'),'slot':slot,'source':'Sleeper','source_url':f'https://api.sleeper.app/v1/league/{lid}/rosters','observed_at':ts,'provider_updated_at':None})
        rec={'id':'sleeper-'+lid,'provider':'Sleeper','account':SLEEPER_USER,'league_id':lid,'league_name':league.get('name') or fallback,'team':{'roster_id':rid,'name':team_name},'status':'pre_draft' if status=='pre_draft' else status,'season':league.get('season'),'week':week,'observed_at':ts,'source':'Sleeper','source_url':f'https://api.sleeper.app/v1/league/{lid}','matchup':match,'players':players}
        if draft_at: rec['draft_at']=draft_at
        out.append(rec)
    return out

def injury_pass(leagues, status_rows, ts):
    """Apply ESPN Fantasy player injury status (collected in Garrett's logged-in ESPN session
    via kona_player_info + ESPN Fantasy player news). Never uses the ESPN NFL injury page."""
    M={'QUESTIONABLE':'Questionable','DOUBTFUL':'Doubtful','OUT':'Out','INJURY_RESERVE':'Injured Reserve','SUSPENSION':'Suspended','DAY_TO_DAY':'Day-To-Day'}
    norm=lambda s: re.sub(r'[^a-z]','',re.sub(r'\b(jr|sr|ii|iii|iv)\b','',str(s).lower()))
    by={norm(r['name']):r for r in status_rows if r.get('name')}
    flags=set()
    for league in leagues:
        for p in league.get('players',[]):
            for f in ('injury_status','injury_detail','injury_estimated_return','injury_source','injury_source_url','injury_observed_at','injury_provider_updated_at'): p.pop(f,None)
            r=by.get(norm(p.get('name','')))
            if not r or r.get('inj') in (None,'ACTIVE','NORMAL'): continue
            pd=dt.datetime.fromtimestamp(r['lastNewsDate']/1000,dt.timezone.utc).strftime('%Y-%m-%d') if r.get('lastNewsDate') else None
            detail=r.get('detail') or None
            p.update({'injury_status':M.get(r['inj'],str(r['inj']).title()),'injury_detail':detail,'injury_source':'ESPN Fantasy player status'+(' · ESPN Fantasy news' if detail else ''),'injury_source_url':f"https://fantasy.espn.com/football/players/card?playerId={r['id']}",'injury_observed_at':ts,'injury_provider_updated_at':pd});flags.add(p['name'])
    return len(flags)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--espn',required=True);ap.add_argument('--injury-status',required=True,help='ESPN Fantasy status JSON: [{id,name,inj,lastNewsDate,detail}]');ap.add_argument('--output',default='fantasy.json');ap.add_argument('--previous',default='fantasy.json');a=ap.parse_args()
    ts=now(); espn=json.load(open(a.espn));
    if espn.get('status')!='ok' or len(espn.get('leagues',[]))!=4: raise SystemExit('ESPN snapshot invalid/auth-expired; preserving prior fantasy.json')
    ids={str(x.get('league_id')) for x in espn['leagues']}
    if ids!={'1242450525','184489982','416480692','14911042'}: raise SystemExit('Unexpected ESPN league set; preserving prior fantasy.json')
    player_db=get('https://api.sleeper.app/v1/players/nfl')
    sleeper=sleeper_snapshot(ts,player_db)
    leagues=espn['leagues']+sleeper
    rows=json.load(open(a.injury_status))
    if not isinstance(rows,list) or len(rows)<50 or not any(r.get('inj') for r in rows): raise SystemExit('ESPN Fantasy injury status invalid; preserving prior fantasy.json')
    count=injury_pass(leagues,rows,ts)
    out={'updated_at':ts,'refresh_note':'Scores, rosters and roster injury flags are regenerated from ESPN, Sleeper and the current injury feed.','providers':[{'name':'ESPN','status':'ok','observed_at':espn.get('observed_at',ts)},{'name':'Sleeper','status':'ok','observed_at':ts}],'injury_check':{'status':'checked','checked_at':ts,'source':'ESPN Fantasy player injury status and player news (logged-in league data)','source_url':'https://fantasy.espn.com/football/','rostered_player_flags':count},'leagues':leagues}
    write_atomic(a.output,out);print(f'wrote {a.output}: {len(leagues)} leagues, {count} unique injury flags')
if __name__=='__main__':main()
