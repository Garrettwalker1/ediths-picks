#!/usr/bin/env python3
"""Current-season RESUME Top 25, per owner Oct 19 2026 steering
(phonemsg-01M5AS78XZ42N25T6F6QJH3FAA and phonemsg-01M5ATE7XWYJ85K7JT18CTM34K):
wins and losses are the big thing, with strength of schedule, quality wins and
losses, and head-to-head results; current-season stats support rather than outweigh
results. No preseason talent, returning-production, portal, draft or AP inputs.

Method (fixed, not tuned to AP):
- 75%: opponent-adjusted win-loss rating (Colley). Every 2026 final counts;
  beating a strong team is worth more, losing to a weak team costs more, and
  strength of schedule is an output of the results themselves.
- 25%: the opponent-adjusted performance composite (standardized, equally
  weighted scoring-margin and total-yardage-margin least-squares ratings), so
  underlying stats separate similar resumes without outweighing them.
- Head-to-head: when two teams sit within 1.5 rating points, this season's
  head-to-head winner ranks ahead (constraints applied transitively; circular
  cases - A beat B beat C beat A - fall back to the full-season resume and are
  disclosed). Affected rows carry an h2h_note.
Values are an UNVALIDATED rating scale, not a calibrated expected margin;
calibration would require freezing this composite's own pregame outputs and
grading them separately. Sealed fixed-coefficient forecasts and the AP research
fit are carried from fixed_reference_ratings.json as labeled comparison columns.
"""
import sys, json, pathlib, heapq
import numpy as np, pandas as pd

sys.setrecursionlimit(10000)
R = pathlib.Path(__file__).resolve().parents[2]
WEEK_DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else R / 'tools/cfb/week8_20261019'
AS_OF = sys.argv[2] if len(sys.argv) > 2 else '2026-10-19'
H2H_THRESHOLD = 1.5  # rating points; head-to-head applies only inside this near-tie window

# Merged current boxstore: originals, then Oct16 replacements, then latest refresh.
by = {}
folders = ['tools/cfb/boxscores', 'tools/cfb/current_inputs_20261016/boxscores'] + sorted(str(d.relative_to(R)) for d in (R / 'tools/cfb').glob('week*_20*/boxscores'))
for folder in folders:
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
    hs = float(comp['home']['score']); as_ = float(comp['away']['score'])
    games.append(dict(
        event_id=eid, date=hd['date'][:10],
        home=comp['home']['team']['displayName'], away=comp['away']['team']['displayName'],
        winner=comp['home']['team']['displayName'] if hs > as_ else comp['away']['team']['displayName'],
        loser=comp['away']['team']['displayName'] if hs > as_ else comp['home']['team']['displayName'],
        margin=hs - as_, ymargin=yds.get('home', 0.0) - yds.get('away', 0.0),
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

# Colley win-loss rating (opponent-adjusted; no margin).
C = np.zeros((n, n)); bvec = np.ones(n)
for r in g.itertuples():
    h, a = idx[r.winner], idx[r.loser]
    C[h, h] += 1; C[a, a] += 1; C[h, a] -= 1; C[a, h] -= 1; bvec[h] += 0.5; bvec[a] -= 0.5
C += 2 * np.eye(n)
colley = pd.Series(np.linalg.solve(C, bvec), index=teams)

# Records from the same standings snapshot used by the Week 8 build.
stand = json.load(open(WEEK_DIR / 'sources/standings.json')); srec = {}
def walk(j):
    for e in j.get('standings', {}).get('entries', []):
        srec[e['team']['displayName']] = {s['name']: s for s in e['stats']}
    for c in j.get('children', []): walk(c)
walk(stand)
played = pd.concat([g[['home']].rename(columns={'home': 't'}), g[['away']].rename(columns={'away': 't'})]).value_counts('t')

# AP poll comparison (Week 8, Oct 18).
_apfiles = sorted((R / 'tools/model_cfb_v2/ap_poll').glob('ap-2026-week*.json'), key=lambda f: int(f.stem.split('week')[1]))
ap = next(p for p in json.load(open(_apfiles[-1]))['rankings'] if p.get('type') == 'ap')
apr = {r['team']['location'] + ' ' + r['team']['name']: r['current'] for r in ap['ranks']}

# FBS membership frozen; sealed reference + AP research fit from the archived snapshot.
members = sorted(json.load(open(WEEK_DIR / 'fbs_members.json')))
ref = {t['team']: t for t in json.load(open(WEEK_DIR / 'fixed_reference_ratings.json'))}

pts = pts - pts[members].mean()
yds = yds - yds[members].mean()
z = lambda v: (v - v[members].mean()) / v[members].std()
perf_blend = (z(pts) + z(yds)) / 2.0
rating = (0.75 * z(colley) + 0.25 * perf_blend) * 10.0  # display scale
base = list(rating.sort_values(ascending=False).index)
basepos = {t: i for i, t in enumerate(base)}

# Head-to-head near-tie constraints, cycle-safe.
cons = set()
for r in g.itertuples():
    w, l = r.winner, r.loser
    if w != l and basepos[w] > basepos[l] and (rating[l] - rating[w]) < H2H_THRESHOLD:
        cons.add((w, l))
adj = {}
for w, l in cons: adj.setdefault(w, []).append(l)
index_counter = [0]; stack = []; lowlink = {}; index = {}; on_stack = set(); sccs = []
def strongconnect(v):
    index[v] = lowlink[v] = index_counter[0]; index_counter[0] += 1
    stack.append(v); on_stack.add(v)
    for w_ in adj.get(v, []):
        if w_ not in index:
            strongconnect(w_); lowlink[v] = min(lowlink[v], lowlink[w_])
        elif w_ in on_stack:
            lowlink[v] = min(lowlink[v], index[w_])
    if lowlink[v] == index[v]:
        scc = []
        while True:
            w_ = stack.pop(); on_stack.discard(w_); scc.append(w_)
            if w_ == v: break
        sccs.append(scc)
for v in list(adj):
    if v not in index: strongconnect(v)
cyclic = set()
for scc in sccs:
    if len(scc) > 1:
        ss = set(scc)
        for w, l in cons:
            if w in ss and l in ss: cyclic.add((w, l))
cons -= cyclic
indeg = {t: 0 for t in base}; adj2 = {}
for w, l in cons:
    adj2.setdefault(w, []).append(l); indeg[l] += 1
avail = [(basepos[t], t) for t in base if indeg[t] == 0]; heapq.heapify(avail)
order = []
while avail:
    _, t = heapq.heappop(avail); order.append(t)
    for m in adj2.get(t, []):
        indeg[m] -= 1
        if indeg[m] == 0: heapq.heappush(avail, (basepos[m], m))
assert len(order) == len(base)
final_rank = {t: i + 1 for i, t in enumerate(order)}

h2h_note = {}
for w, l in cons:
    if basepos[w] > basepos[l]:
        h2h_note[w] = 'Beat ' + l + ' head-to-head'
        h2h_note[l] = 'Lost head-to-head to ' + w
for w, l in sorted(cyclic):
    h2h_note[w] = h2h_note.get(w, '') + (' ' if h2h_note.get(w) else '') + 'Circular head-to-head vs ' + l + ': resume decides'

rows = []
for t in members:
    p = ref.get(t, {})
    rows.append({
        'team': t,
        'rating': float(rating[t]),
        'rank': final_rank[t],
        'base_rank': basepos[t] + 1,
        'record': srec.get(t, {}).get('overall', {}).get('displayValue'),
        'ap_rank': apr.get(t),
        'games_used': int(played.get(t, 0)),
        'resume_wl_rating': float(colley[t]),
        'points_rating': float(pts[t]),
        'yards_rating': float(yds[t]),
        'h2h_note': h2h_note.get(t),
        'ap_model_rating': p.get('ap_model_rating'),
        'ap_model_rank': p.get('ap_model_rank'),
        'fixed_reference_rating': p.get('fixed_reference_rating'),
        'fixed_reference_rank': p.get('fixed_reference_rank'),
    })
rows.sort(key=lambda r: r['rank'])

out = {
    'model': 'CFB current-season resume rating: opponent-adjusted W/L (75%) + scoring/yardage composite (25%), head-to-head near-tie rule',
    'model_as_of': AS_OF,
    'records_as_of': AS_OF,
    'ap_date': ap['date'], 'ap_last_updated': ap['lastUpdated'],
    'home_field_points': round(hfa, 2),
    'h2h_threshold_rating_points': H2H_THRESHOLD,
    'h2h_constraints_applied': len(cons),
    'h2h_circular_dropped': sorted([w + ' over ' + l for w, l in cyclic]),
    'method': ('Resume-first ranking over every 2026 FBS final through ' + AS_OF + ' (' + str(len(g)) + ' games). '
               '75% opponent-adjusted win-loss rating (Colley: quality wins count more, bad losses cost more, strength of '
               'schedule is an output of results); 25% opponent-adjusted scoring/yardage performance composite, so stats '
               'support results rather than drive the ranking. Head-to-head: inside a ' + format(H2H_THRESHOLD, '.1f') + '-rating-point '
               'near-tie, this season\'s head-to-head winner ranks ahead, applied transitively; circular cases fall back to '
               'the full-season resume. Current-season performance only: no preseason talent, returning-production, portal, '
               'draft or AP-poll inputs, and no prior-season results. Values are an unvalidated rating scale, not a calibrated '
               'expected margin. The AP-fit column is a separately trained research variant that failed its Week 7 gate; the '
               'fixed-reference column is the sealed Oct 11 forecast specification (which does use preseason inputs) shown '
               'for audit only. Neither is a validated betting edge.'),
    'sources': [*[f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?year=2026&seasontype=2&week={w}&groups=80&limit=400' for w in range(1, 9)],
                json.load(open(WEEK_DIR / 'fetch_audit.json'))['standings_url']],
    'teams': rows,
}
(WEEK_DIR / 'power_ratings.json').write_text(json.dumps(out, indent=2) + '\n')
print('WROTE', WEEK_DIR / 'power_ratings.json', 'games', len(g), 'h2h constraints', len(cons), 'cyclic', len(cyclic))
print('TOP5', [(r['team'], round(r['rating'], 1), r['record']) for r in rows[:5]])
print('OREGON', [(r['rank'], round(r['rating'], 1)) for r in rows if r['team'] == 'Oregon Ducks'])
ap25 = {k for k, v in apr.items() if v <= 25}
print('AP_TOP25_OVERLAP', len([r for r in rows[:25] if r['team'] in ap25]))
print('MAX', round(rows[0]['rating'], 1))
