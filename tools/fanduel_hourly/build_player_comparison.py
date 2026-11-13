"""Build strict, event-local player comparisons from an actual rendered capture.
No collection, model change or publication side effects on import.
"""
import argparse, collections, datetime, hashlib, json, pathlib
from player_label_candidate import parse_label, attach_identity
R = pathlib.Path(__file__).resolve().parents[2]
MARKETS = {'anytime_td','passing_yards','passing_tds','rushing_yards','receiving_yards','receptions'}

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def stamp(value):
    result = datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return result

def build_event(archive, game, expected_url, td, primary, generic, as_of):
    archive = pathlib.Path(archive)
    x = load(archive/'rendered.json')
    if 'content' in x:
        x = json.loads(x['content'])
    if x['url'] != expected_url or not expected_url.startswith('https://sportsbook.fanduel.com/football/nfl/'):
        raise ValueError('capture URL does not match verified event URL')
    if not any('authorized by the Illinois Gaming Board' in s for s in x['state_evidence']):
        raise ValueError('actual Illinois footer required')
    captured, kickoff = stamp(x['at']), stamp(game['date'])
    if captured >= kickoff or captured > as_of:
        raise ValueError('post-kickoff or future capture not permitted')
    if not x['markets'] or not all(m['expanded']=='true' and not m['show_more'] for m in x['markets']):
        raise ValueError('target accordions must all be expanded with no show-more left')
    manifest = load(archive/'manifest.json')
    idx = {}
    teams = {game['home_abbr'], game['away_abbr']}
    for team in teams:
        roster_path = archive/(team+'.json')
        provenance = [m for m in manifest if m['team']==team]
        if len(provenance)!=1:
            raise ValueError('unique roster manifest required')
        provenance = provenance[0]
        if hashlib.sha256(roster_path.read_bytes()).hexdigest()!=provenance['sha256']:
            raise ValueError('roster hash mismatch')
        if stamp(provenance['retrieved_at']) > captured:
            raise ValueError('roster retrieved after source capture')
        roster = load(roster_path)
        if roster['season']['year']!=game['season']:
            raise ValueError('roster season mismatch')
        if not provenance['url'].startswith('https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/'):
            raise ValueError('unsupported roster source')
        for group in roster['athletes']:
            for athlete in group['items']:
                cross = [r for r in td['rows'] if r['team']==team and str(r.get('espn_id'))==athlete['id'] and r.get('player_id')]
                if len(cross)!=1:
                    continue
                idx.setdefault(athlete['displayName'],[]).append(dict(player_id=cross[0]['player_id'],espn_id=athlete['id'],team_id=team))
    parsed = []
    for market in x['markets']:
        parsed.extend(r for r in (parse_label(s['label']) for s in market['selections']) if r)
    if len({(r['player_name'],r['market'],r['side']) for r in parsed})!=len(parsed):
        raise ValueError('duplicate rendered selection')
    if {r['market'] for r in parsed} != MARKETS:
        raise ValueError('all six standard market categories must be observed')
    joined, gaps = attach_identity(parsed, game['event_id'], game['date'], 'IL', x['at'], x['url'], idx)
    by = {}
    pr = {r['player_id']:r for r in primary['ranked']}
    gp = {r['player_id']:r for r in generic['players']}
    for row in joined:
        key = row['player_id'], row['market']
        z = by.setdefault(key, {k:row[k] for k in ['player_id','espn_id','team_id','player_name','market','event_id','kickoff','state','captured_at','source_url']})
        z.setdefault('selections',[]).append({k:row[k] for k in ['side','line','price']})
    for z in by.values():
        pid, market = z['player_id'], z['market']
        z.update(model_value=None, model_label='Unavailable: no compatible published player projection')
        if market=='anytime_td' and pid in pr:
            p = pr[pid]
            opponent = next(t for t in teams if t!=z['team_id'])
            if p['team']==z['team_id'] and p['opp']==opponent and stamp(p['kick'])==kickoff:
                z.update(model_value=p['primary'],model_kind='probability',model_label='Owner-adopted Oct29 TD model; unvalidated',model_captured_at=primary['generated_at'])
        elif market in ['rushing_yards','receiving_yards','receptions'] and pid in gp:
            p = gp[pid]
            if p['team']==z['team_id']:
                z.update(model_value=p[market]['median'],model_kind='median',model_label='Dated generic median, not current matchup/personnel adjusted',model_captured_at=generic['generated_at'])
        if market!='anytime_td' and not (len(z['selections'])==2 and {s['side'] for s in z['selections']}=={'over','under'} and len({s['line'] for s in z['selections']})==1):
            raise ValueError('standard over/under pair incomplete or different lines')
    return dict(checked_at=x['at'],state='IL',event_id=str(game['event_id']),matchup=game['away']+' at '+game['home'],kickoff=game['date'],source_url=x['url'],coverage=dict(rendered_target_accordions=len(x['markets']),parsed_selections=len(parsed),joined_selections=len(joined),unmatched_selections=len(gaps),market_player_rows=dict(collections.Counter(z['market'] for z in by.values()))),rows=list(by.values()),identity_gaps=gaps)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', required=True, type=pathlib.Path)
    p.add_argument('--event-id', required=True)
    p.add_argument('--source-url', required=True, help='Owning-source URL independently checked against this event')
    p.add_argument('--output', required=True, type=pathlib.Path)
    p.add_argument('--as-of', help='Explicit timestamp for reproducible archive replay, not a new capture time')
    args = p.parse_args()
    slate = load(R/'tools/nfl/current_season_20261113/current_forecasts.json')['games']
    games = [g for g in slate if str(g['event_id'])==args.event_id]
    if len(games)!=1:
        raise ValueError('event not unique in current core slate')
    event = build_event(args.archive,games[0],args.source_url,load(R/'tools/nfl/week10_2026/td_projection_snapshot.json'),load(R/'tools/nfl/week10_2026/td_week10_primary.json'),load(R/'player_projections.json'),stamp(args.as_of) if args.as_of else datetime.datetime.now(datetime.timezone.utc))
    # Event output only. A separate publisher must merge with per-event freezes.
    args.output.write_text(json.dumps(event,indent=2)+'\n')
    print(json.dumps(event['coverage'],indent=2))

if __name__=='__main__':
    main()
