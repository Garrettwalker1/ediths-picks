#!/usr/bin/env python3
"""Current-season performance Top 25 (opponent-adjusted), per owner Oct 19 2026
correction (phonemsg-01M5AS78XZ42N25T6F6QJH3FAA): rankings must be based on team
performance just this season - no preseason talent, returning-production, portal,
draft or AP priors. Least-squares scoring-margin ratings over every 2026 final
with a home-field term (neutral-site games carry no HFA); ratings are centered to
mean zero across the 138-team FBS set, so values are points vs the average FBS
team on a neutral field. AP research fit and the sealed fixed-coefficient
reference are carried as labeled comparison columns only.
"""
import sys, json, pathlib, tempfile, datetime
import numpy as np, pandas as pd

R = pathlib.Path(__file__).resolve().parents[2]
WEEK_DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else R / 'tools/cfb/week8_20261019'
AS_OF = sys.argv[2] if len(sys.argv) > 2 else '2026-10-19'

# Merged current boxstore: originals, then Oct16 replacements, then latest refresh.
by = {}
for folder in ['tools/cfb/boxscores', 'tools/cfb/current_inputs_20261016/boxscores', WEEK_DIR.name and str(WEEK_DIR.relative_to(R) / 'boxscores')]:
    for f in (R / folder).glob('*.json'):
        d = json.load(open(f)); by[str(d['header']['id'])] = f

games = []
for eid, f in sorted(by.items()):
    d = json.load(open(f)); hd = d['header']['competitions'][0]
    if not hd['status']['type']['completed']:
        continue
    comp = {c['homeAway']: c for c in hd['competitors']}
    games.append(dict(
        event_id=eid, date=hd['date'][:10],
        home=comp['home']['team']['displayName'], away=comp['away']['team']['displayName'],
        margin=float(comp['home']['score']) - float(comp['away']['score']),
        neutral=bool(hd.get('neutralSite'))))
g = pd.DataFrame(games)
teams = sorted(set(g.home) | set(g.away)); idx = {t: i for i, t in enumerate(teams)}; n = len(teams)
A = np.zeros((len(g), n + 1))
for k, r in enumerate(g.itertuples()):
    A[k, idx[r.home]] = 1; A[k, idx[r.away]] = -1; A[k, n] = 0 if r.neutral else 1
A2 = np.vstack([A, np.append(np.ones(n), 0)]); y2 = np.append(g.margin.to_numpy(), 0.0)
sol, _, _, _ = np.linalg.lstsq(A2, y2, rcond=None)
hfa = float(sol[n]); rating = pd.Series(sol[:n], index=teams)

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
members = set(json.load(open(WEEK_DIR / 'fbs_members.json')))
# Carry the sealed fixed-coefficient reference and AP research fit as labeled comparisons.
# On first run the previous power_ratings.json is the sealed build's output; on later
# runs it already carries these columns.
prev = json.load(open(WEEK_DIR / 'power_ratings.json'))
prev_by_team = {t['team']: t for t in prev['teams']}
rating = rating - rating[[t for t in members]].mean()  # center on the FBS average

rows = []
for t in sorted(members):
    p = prev_by_team.get(t, {})
    rows.append({
        'team': t,
        'rating': float(rating[t]),
        'record': srec.get(t, {}).get('overall', {}).get('displayValue'),
        'ap_rank': apr.get(t),
        'games_used': int(played.get(t, 0)),
        'ap_model_rating': p.get('ap_model_rating'),
        'ap_model_rank': p.get('ap_model_rank'),
        'fixed_reference_rating': p.get('rating'),
        'fixed_reference_rank': p.get('rank'),
    })
rows.sort(key=lambda r: -r['rating'])
for i, r in enumerate(rows, 1): r['rank'] = i

out = {
    'model': 'CFB current-season performance rating, opponent-adjusted',
    'model_as_of': AS_OF,
    'records_as_of': AS_OF,
    'ap_date': ap['date'], 'ap_last_updated': ap['lastUpdated'],
    'home_field_points': round(hfa, 2),
    'method': ('Least-squares opponent-adjusted scoring-margin rating over every 2026 FBS final through '
               + AS_OF + ' (' + str(len(g)) + ' games, all opponents connected through the full schedule). Only the '
               + str(len(members)) + '-team FBS set is ranked. Current-season results only: no preseason talent, '
               'returning-production, portal, draft or AP-poll inputs. Ratings are centered across '
               + str(len(members)) + ' FBS teams and read as points vs the average FBS team on a neutral field; fitted home-field is '
               + format(hfa, '.1f') + ' points. The AP-fit column is a separately trained research variant that failed its '
               'Week 7 gate; the fixed-reference column is the sealed Oct 11 forecast specification (which does use '
               'preseason inputs) shown for audit only. Neither is a validated betting edge.'),
    'sources': prev.get('sources'),
    'teams': rows,
}
(WEEK_DIR / 'power_ratings.json').write_text(json.dumps(out, indent=2) + '\n')
print('WROTE', WEEK_DIR / 'power_ratings.json', 'games', len(g), 'teams', n, 'hfa', round(hfa, 2))
print('TOP5', [(r['team'], round(r['rating'], 1), r['record']) for r in rows[:5]])
print('OREGON', [(r['rank'], round(r['rating'], 2)) for r in rows if r['team'] == 'Oregon Ducks'])
overlap = set(r['team'] for r in rows[:25]) & set(apr.get(t) and t for t in apr if apr[t] and apr[t] <= 25)
print('AP_TOP25_OVERLAP', len([t for t in rows[:25] if t['team'] in {k for k, v in apr.items() if v <= 25}]))
