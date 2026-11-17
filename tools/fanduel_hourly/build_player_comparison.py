"""Build strict, event-local player comparisons from an actual rendered capture.
No collection, model change or publication side effects on import.
"""
import argparse, collections, csv, datetime, hashlib, json, pathlib
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
    # Current core nflverse uses WAS; ESPN roster/TD/generic packages use WSH.
    # This explicit abbreviation crosswalk changes no game or player identity.
    teams = {'WAS':'WSH'}.get(game['home_abbr'],game['home_abbr']), {'WAS':'WSH'}.get(game['away_abbr'],game['away_abbr'])
    teams = set(teams)
    for team in teams:
        roster_path = archive/(team+'.json')
        provenance = [m for m in manifest if m.get('team')==team]
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
    identity_file = archive/'identity_evidence.json'
    if identity_file.exists():
        evidence = load(identity_file)
        checks = [m for m in manifest if m.get('kind')=='identity_evidence']
        if len(checks)!=1 or hashlib.sha256(identity_file.read_bytes()).hexdigest()!=checks[0]['sha256'] or stamp(checks[0]['retrieved_at'])>captured:
            raise ValueError('supplemental identity evidence provenance mismatch')
        crosswalk_path=R/'tools/nfl/current_season_20261117/sources/players.csv'
        if hashlib.sha256(crosswalk_path.read_bytes()).hexdigest()!=evidence['crosswalk_source_sha256']:
            raise ValueError('stable-ID source crosswalk hash mismatch')
        with crosswalk_path.open() as source:
            crosswalk=list(csv.DictReader(source))
        for item in evidence['identities']:
            if item['team_id'] not in teams or not item['evidence_note']:
                raise ValueError('supplemental identity team/evidence missing')
            roster=load(archive/(item['team_id']+'.json'))
            members=[a for group in roster['athletes'] for a in group['items'] if a['id']==item['espn_id'] and a['displayName']==item['roster_name']]
            matches=[r for r in crosswalk if r.get('espn_id','').removesuffix('.0')==item['espn_id'] and r.get('gsis_id')==item['player_id']]
            if len(members)!=1 or len(matches)!=1 or item['crosswalk_espn_id']!=item['espn_id'] or item['crosswalk_gsis_id']!=item['player_id']:
                raise ValueError('supplemental identity does not match roster/crosswalk')
            identity={k:item[k] for k in ['player_id','espn_id','team_id']}
            if item['book_name'] in idx and idx[item['book_name']]!=[identity]:
                raise ValueError('supplemental identity conflicts')
            idx[item['book_name']]=[identity]
    parsed = []
    for market in x['markets']:
        parsed.extend(r for r in (parse_label(s['label']) for s in market['selections']) if r)
    if len({(r['player_name'],r['market'],r['side']) for r in parsed})!=len(parsed):
        raise ValueError('duplicate rendered selection')
    present_markets = {r['market'] for r in parsed}
    category_coverage = None
    if present_markets != MARKETS:
        audit_path=archive/'availability_audit.json'
        if not audit_path.exists():
            raise ValueError('all six standard market categories must be observed')
        audit=load(audit_path)
        proof=[m for m in manifest if m.get('kind')=='availability_audit']
        if len(proof)!=1 or hashlib.sha256(audit_path.read_bytes()).hexdigest()!=proof[0]['sha256']:
            raise ValueError('partial-category audit hash mismatch')
        if audit['url']!=expected_url or not audit['full_dom_after_bottom_scroll'] or not any('authorized by the Illinois Gaming Board' in s for s in audit['state_evidence']):
            raise ValueError('partial-category audit source mismatch')
        if abs((stamp(audit['at'])-captured).total_seconds())>600 or stamp(audit['at'])>as_of:
            raise ValueError('partial-category audit outside collection window')
        expected=set()
        suffixes={'Passing Yds':'passing_yards','Passing TDs':'passing_tds','Rushing Yds':'rushing_yards','Receiving Yds':'receiving_yards','Total Receptions':'receptions'}
        for h in audit['headers']:
            label=h['text']
            if label=='Touchdown Scorers' and any(s.startswith('Any Time Touchdown Scorer, ') for s in audit.get('player_labels',[])):expected.add('anytime_td')
            for suffix,market in suffixes.items():
                if label.endswith(' - '+suffix):expected.add(market)
        if not present_markets or expected!=present_markets:
            raise ValueError('partial capture omitted a category visible in full DOM audit')
        category_coverage=dict(present=sorted(present_markets),not_observed=sorted(MARKETS-present_markets),status='PARTIAL categories',audit_at=audit['at'],note='Missing standard categories were not observed in the checked full-DOM header, expanded selection and event-tab inventory after scrolling to the bottom. This is not a guarantee about later availability.')
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
    event=dict(checked_at=x['at'],state='IL',event_id=str(game['event_id']),matchup=game['away']+' at '+game['home'],kickoff=game['date'],source_url=x['url'],coverage=dict(rendered_target_accordions=len(x['markets']),parsed_selections=len(parsed),joined_selections=len(joined),unmatched_selections=len(gaps),market_player_rows=dict(collections.Counter(z['market'] for z in by.values()))),rows=list(by.values()),identity_gaps=gaps)
    if category_coverage:event['category_coverage']=category_coverage
    return event

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', required=True, type=pathlib.Path)
    p.add_argument('--event-id', required=True)
    p.add_argument('--source-url', required=True, help='Owning-source URL independently checked against this event')
    p.add_argument('--output', required=True, type=pathlib.Path)
    p.add_argument('--as-of', help='Explicit timestamp for reproducible archive replay, not a new capture time')
    args = p.parse_args()
    slate = load(R/'tools/nfl/current_season_20261117/current_forecasts.json')['games']
    games = [g for g in slate if str(g['event_id'])==args.event_id]
    if len(games)!=1:
        raise ValueError('event not unique in current core slate')
    event = build_event(args.archive,games[0],args.source_url,load(R/'tools/nfl/week11_2026/td_projection_snapshot.json'),load(R/'tools/nfl/week11_2026/td_week11_primary.json'),load(R/'player_projections.json'),stamp(args.as_of) if args.as_of else datetime.datetime.now(datetime.timezone.utc))
    # Event output only. A separate publisher must merge with per-event freezes.
    args.output.write_text(json.dumps(event,indent=2)+'\n')
    print(json.dumps(event['coverage'],indent=2))

if __name__=='__main__':
    main()
