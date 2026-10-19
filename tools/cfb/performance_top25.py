#!/usr/bin/env python3
"""Current-season performance Top 25 (opponent-adjusted), per owner Oct 19 2026
correction (phonemsg-01M5AS78XZ42N25T6F6QJH3FAA): rankings must be based on team
performance just this season - no preseason talent, returning-production, portal,
draft or AP priors. Two least-squares ratings over every 2026 final - scoring
margin and total-yardage margin, each with a home-field term (neutral-site games
carry no HFA) - are standardized, equally weighted, and shown on the scoring
rating's point scale, centered on the 138-team FBS set. The composite reads as the
model's projected margin vs the average FBS team on a neutral field; specific
game projections stay on the sealed game board. The sealed fixed-coefficient
forecast specification and the AP research fit are carried from
fixed_reference_ratings.json as labeled comparison columns only.
"""
import sys, json, pathlib
import numpy as np, pandas as pd

R = pathlib.Path(__file__).resolve().parents[2]
WEEK_DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else R / 'tools/cfb/week8_20261019'
AS_OF = sys.argv[2] if len(sys.argv) > 2 else '2026-10-19'

# Merged current boxstore: originals, then Oct16 replacements, then latest refresh.
by = {}
for folder in ['tools/cfb/boxscores', 'tools/cfb/current_inputs_20261016/boxscores', str(WEEK_DIR.relative_to(R) / 'boxscores')]:
    for f in (R / folder).glob('*.json'):
        d = json.load(open(f)); by[str(d['header']['id'])] = f

games = []
for eid, f in sorted(by.items()):
    d = json.load(open(f)); hd = d['header']['competitions'][0]
    if not hd['status']['type']['completed']:
        continue
    comp = {c['homeAway']: c for c in hd['competitors']}
    yds = {}
    for t in d['boxscore']['teams']:
        stats = {st['name']: st['displayValue'] for st in t['statistics']}
        yds[t['homeAway']] = float(stats.get('totalYards', 0))
    games.append(dict(
        event_id=eid, date=hd['date'][:10],
        home=comp['home']['team']['displayName'], away=comp['away']['team']['displayName'],
        margin=float(comp['home']['score']) - float(comp['away']['score']),
        ymargin=yds.get('home', 0.0) - yds.get('away', 0.0),
        neutral=bool(hd.get('neutralSite'))))
g = pd.DataFrame(games)
teams = sorted(set(g.home) | set(g.away)); idx = {t: i for i, t in enumerate(teams)}; n = len(teams)

def ls_rating(target):
    A = np.zeros((len(g), n + 1))
    for k, r in enumerate(g.itertuples()):
        A[k, idx[r.home]] = 1; A[k, idx[r.away]] = -1; A[k, n] = 0 if r.neutral else 1
    A2 = np.vstack([A, np.append(np.ones(n), 0)]); y2 = np.append(g[target].to_numpy(), 0.0)
    sol, _, _, _ = np.linalg.lstsq(A2, y2, rcond=None)
    return float(sol[n]), pd.Series(sol[:n], index=teams)

hfa, pts = ls_rating('margin')
_, yds = ls_rating('ymargin')

# Records from the same standings snapshot used by the Week 8 build.
stand = json.load(open(WEEK_DIR / 'sources/standings.json')); srec = {}
def walk(j):
    for e in j.get('standings', {}).get('entries', []):
        srec[e['team']['displayName']] = {s['name']: s for s in e['stats']}
    for c in j.get('children', []): walk(c)
walk(stand)
played = pd.concat([g[['home']].rename(columns={'home': 't'}), g[['away']].rename(columns={'away': 't'})]).value_counts('t')

# AP poll comparison (Week 8, Oct 18).
ap = next(p for p in json.load(open(R / 'tools/model_cfb_v2/ap_poll/ap-2026-week8.json'))['rankings'] if p.get('type') == 'ap')
apr = {r['team']['location'] + ' ' + r['team']['name']: r['current'] for r in ap['ranks']}

# FBS membership is frozen in fbs_members.json (from the sealed Week 8 build), so
# rerunning this script never lets a prior output widen the ranked universe.
members = sorted(json.load(open(WEEK_DIR / 'fbs_members.json')))
# Sealed fixed-coefficient reference and AP research fit, from the archived snapshot.
ref = {t['team']: t for t in json.load(open(WEEK_DIR / 'fixed_reference_ratings.json'))}

pts = pts - pts[members].mean()   # center on the FBS average
yds = yds - yds[members].mean()
z = lambda v: (v - v[members].mean()) / v[members].std()
blend = (z(pts) + z(yds)) / 2.0
rating = blend * pts[members].std()   # display on the scoring rating's point scale

rows = []
for t in members:
    p = ref.get(t, {})
    rows.append({
        'team': t,
        'rating': float(rating[t]),
        'points_rating': float(pts[t]),
        'yards_rating': float(yds[t]),
        'record': srec.get(t, {}).get('overall', {}).get('displayValue'),
        'ap_rank': apr.get(t),
        'games_used': int(played.get(t, 0)),
        'ap_model_rating': p.get('ap_model_rating'),
        'ap_model_rank': p.get('ap_model_rank'),
        'fixed_reference_rating': p.get('fixed_reference_rating'),
        'fixed_reference_rank': p.get('fixed_reference_rank'),
    })
rows.sort(key=lambda r: -r['rating'])
for i, r in enumerate(rows, 1): r['rank'] = i

out = {
    'model': 'CFB current-season performance rating, opponent-adjusted (scores + yards composite)',
    'model_as_of': AS_OF,
    'records_as_of': AS_OF,
    'ap_date': ap['date'], 'ap_last_updated': ap['lastUpdated'],
    'home_field_points': round(hfa, 2),
    'method': ('Composite of two least-squares opponent-adjusted ratings - scoring margin and total-yardage '
               'margin, standardized and equally weighted, shown on a points-style rating scale - over every 2026 FBS final through '
               + AS_OF + ' (' + str(len(g)) + ' games, all opponents connected through the full schedule). Only the '
               + str(len(members)) + '-team FBS set is ranked. Current-season performance only: no preseason talent, '
               'returning-production, portal, draft or AP-poll inputs, and no prior-season results. Values sit on a '
               'points-style rating scale centered on the average FBS team, not yet validated as a calibrated '
               'expected margin; fitted home-field is '
               + format(hfa, '.1f') + ' points. The AP-fit column is a separately trained research variant that failed its '
               'Week 7 gate; the fixed-reference column is the sealed Oct 11 forecast specification (which does use '
               'preseason inputs) shown for audit only. Neither is a validated betting edge.'),
    'sources': json.load(open(WEEK_DIR / 'fixed_reference_ratings.json')) and [
        *[f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week={w}&groups=80&limit=400' for w in range(1, 9)],
        json.load(open(WEEK_DIR / 'fetch_audit.json'))['standings_url']],
    'teams': rows,
}
(WEEK_DIR / 'power_ratings.json').write_text(json.dumps(out, indent=2) + '\n')
print('WROTE', WEEK_DIR / 'power_ratings.json', 'games', len(g), 'teams', n, 'hfa', round(hfa, 2), 'scale_std', round(float(pts[members].std()), 2))
print('TOP5', [(r['team'], round(r['rating'], 1), r['record']) for r in rows[:5]])
print('OREGON', [(r['rank'], round(r['rating'], 2), 'pts#' + str(sorted(rows, key=lambda r: -r['points_rating']).index(r) + 1), 'yds#' + str(sorted(rows, key=lambda r: -r['yards_rating']).index(r) + 1)) for r in rows if r['team'] == 'Oregon Ducks'])
ap25 = {k for k, v in apr.items() if v <= 25}
print('AP_TOP25_OVERLAP', len([r for r in rows[:25] if r['team'] in ap25]))
print('MAX', round(rows[0]['rating'], 1), 'MIN25', round(rows[24]['rating'], 1))
