#!/usr/bin/env python3
"""Build current-season (2026) NFL offensive/defensive efficiency rankings from nflverse play-by-play.

Provisional descriptive rankings, not validated game predictors. Builder v2 (2026-11-23):
per-side denominators, fully input-derived metadata, built-in consistency checks.

Usage: python3 build_current_rankings_nfl.py PBP_PARQUET OUT_PREFIX [SOURCE_LAST_UPDATED]
SOURCE_LAST_UPDATED should come from the release timestamp.json fetched at download time;
if omitted it is recorded as "not recorded at build time", never guessed.

Pinned definitions (chosen before inspecting results):
- Accepted plays: play_type in {pass, run}; two_point_attempt excluded. Verified on the 2026-11-23
  snapshot: qb_kneel and qb_spike are distinct play_type values, so the play_type filter removes them
  (249/59 plays that snapshot); the qb_kneel/qb_spike flags find zero inside pass/run (checked at build).
  Sacks are play_type pass. Scrambles are play_type run (587 on the 2026-11-23 snapshot, zero as pass),
  so the pass split is dropbacks incl. sacks and the run split is designed runs plus scrambles.
  no_play rows (penalty-only/offsetting etc.) are excluded; penalties on live scrimmage plays remain.
- Success (distance-based, matches the CFB provisional metric): 1st down: yards_gained >= 50% of ydstogo;
  2nd: >= 70%; 3rd/4th: >= 100%. Plays with unusable success inputs are excluded from success and counted.
- EPA: nflfastR's modeled epa column; null epa excluded from EPA and counted. (On the 2026-11-23 snapshot
  both exclusion counts are zero, so EPA and success share identical per-team samples and denominators.)
- No garbage-time adjustment (stated limit; same as the CFB provisional tables).
- Opponent adjustment: per metric, one weighted ridge over team-game rows.
  Row = one team's offensive game: y = play-weighted mean rate, weight = accepted plays.
  Features: intercept, home indicator (posteam == home_team; nominal home team on neutral sites),
  offense dummy (posteam), defense dummy (defteam). Ridge penalty 20 on team effects only
  (intercept and home unpenalized), equivalent to 20 prior plays at the league rate. Fixed, not tuned.
  Adjusted offensive rate = intercept + offense effect; adjusted defensive rate = intercept + defense effect.
  Offense: higher is better (rank descending). Defense: lower allowed is better (rank ascending).
  Denominators are per side: offensive columns use plays with posteam == team; defensive columns use
  plays with defteam == team. They differ (opponents run different numbers of plays against a team).
- Splits: pass plays and run plays are separate filters with their own regressions and per-side counts.

Cutoff/coverage: whatever the source file contains at build time; games by week are derived from the
input and recorded. Games not final in the source are absent; check the nflverse schedules data for
pending games at integration time.
"""
import csv, hashlib, json, sys, collections, datetime

import pyarrow.parquet as pq
import numpy as np

if len(sys.argv) < 3:
    sys.exit('usage: build_current_rankings_nfl.py PBP_PARQUET OUT_PREFIX [SOURCE_LAST_UPDATED]')
PBP_PATH = sys.argv[1]
OUT_PREFIX = sys.argv[2]
SOURCE_LAST_UPDATED = sys.argv[3] if len(sys.argv) > 3 else 'not recorded at build time'
SOURCE_URL = 'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet'
RIDGE = 20.0

COLS = ['game_id', 'week', 'posteam', 'defteam', 'home_team', 'play_type',
        'qb_kneel', 'qb_spike', 'qb_scramble', 'two_point_attempt', 'down', 'ydstogo', 'yards_gained', 'epa']

t = pq.read_table(PBP_PATH, columns=COLS)
n_total = t.num_rows
d = {c: t.column(c).to_pylist() for c in COLS}

play_type_counts = collections.Counter(str(x) for x in d['play_type'])
kneel_leak = sum(1 for i in range(n_total) if d['play_type'][i] in ('pass', 'run') and d['qb_kneel'][i] == 1)
spike_leak = sum(1 for i in range(n_total) if d['play_type'][i] in ('pass', 'run') and d['qb_spike'][i] == 1)
scramble_by_type = collections.Counter(str(d['play_type'][i]) for i in range(n_total) if d['qb_scramble'][i] == 1)

plays = []  # (game_id, week, posteam, defteam, home, is_pass, success or None, epa or None)
excluded = collections.Counter()
for i in range(n_total):
    pt = d['play_type'][i]
    if pt not in ('pass', 'run'):
        excluded['play_type_not_pass_run'] += 1
        continue
    if d['two_point_attempt'][i] == 1:
        excluded['two_point_attempt'] += 1
        continue
    posteam, defteam = d['posteam'][i], d['defteam'][i]
    if not posteam or not defteam:
        excluded['missing_team'] += 1
        continue
    down, ytg, yg = d['down'][i], d['ydstogo'][i], d['yards_gained'][i]
    if down is None or ytg is None or yg is None or ytg <= 0 or down not in (1, 2, 3, 4):
        succ = None
        excluded['success_unusable'] += 1
    else:
        need = {1: 0.5, 2: 0.7, 3: 1.0, 4: 1.0}[down]
        succ = 1.0 if yg >= need * ytg else 0.0
    if d['epa'][i] is None:
        excluded['epa_null'] += 1
    home = 1.0 if posteam == d['home_team'][i] else 0.0
    plays.append((d['game_id'][i], d['week'][i], posteam, defteam, home, pt == 'pass', succ, d['epa'][i]))

accepted_total = len(plays)
games_by_week = collections.Counter()
seen_games = set()
for p in plays:
    if p[0] not in seen_games:
        seen_games.add(p[0])
        games_by_week[p[1]] += 1

teams = sorted(set(p[2] for p in plays) | set(p[3] for p in plays))


def build_metric(rows, value_idx):
    """value_idx: 6 success, 7 epa. Per-side denominators: off by posteam, def by defteam."""
    tg = collections.defaultdict(lambda: [0.0, 0.0])  # (game, off team) -> [sum, n]
    opp = {}
    home_map = {}
    off_plays = collections.Counter(); def_plays = collections.Counter()
    off_games = collections.defaultdict(set); def_games = collections.defaultdict(set)
    off_sum = collections.Counter(); def_sum = collections.Counter()
    for (gid, wk, off, dfn, home, is_pass, succ, epa) in rows:
        v = succ if value_idx == 6 else epa
        if v is None:
            continue
        tg[(gid, off)][0] += v
        tg[(gid, off)][1] += 1.0
        opp[(gid, off)] = dfn
        home_map[(gid, off)] = home
        off_plays[off] += 1; def_plays[dfn] += 1
        off_games[off].add(gid); def_games[dfn].add(gid)
        off_sum[off] += v; def_sum[dfn] += v
    if not tg:
        return None
    tidx = {tm: k for k, tm in enumerate(teams)}
    p = 2 + 2 * len(teams)
    XtWX = np.zeros((p, p))
    XtWy = np.zeros(p)
    for (gid, off), (s, n) in tg.items():
        x = np.zeros(p)
        x[0] = 1.0
        x[1] = home_map[(gid, off)]
        x[2 + tidx[off]] = 1.0
        x[2 + len(teams) + tidx[opp[(gid, off)]]] = 1.0
        y = s / n
        XtWX += n * np.outer(x, x)
        XtWy += n * x * y
    for k in range(2, p):
        XtWX[k, k] += RIDGE
    b = np.linalg.solve(XtWX, XtWy)
    out = {}
    for tm in teams:
        k = tidx[tm]
        out[tm] = {
            'off_games': len(off_games[tm]), 'def_games': len(def_games[tm]),
            'off_plays': off_plays[tm], 'def_plays': def_plays[tm],
            'raw_off': (off_sum[tm] / off_plays[tm]) if off_plays[tm] else None,
            'raw_def': (def_sum[tm] / def_plays[tm]) if def_plays[tm] else None,
            'adj_off': b[0] + b[2 + k],
            'adj_def': b[0] + b[2 + len(teams) + k],
            'home_effect': b[1], 'intercept': b[0],
        }
    return out


def ranks(metric_res, key, higher_better):
    vals = [(tm, r[key]) for tm, r in metric_res.items() if r[key] is not None]
    vals.sort(key=lambda x: x[1], reverse=higher_better)
    return {tm: i + 1 for i, (tm, _) in enumerate(vals)}


pass_rows = [p for p in plays if p[5]]
run_rows = [p for p in plays if not p[5]]

metrics = {
    'success': build_metric(plays, 6),
    'epa': build_metric(plays, 7),
    'pass_success': build_metric(pass_rows, 6),
    'pass_epa': build_metric(pass_rows, 7),
    'rush_success': build_metric(run_rows, 6),
    'rush_epa': build_metric(run_rows, 7),
}

rank_maps = {}
for name, res in metrics.items():
    if res is None:
        sys.exit(f'no rows for metric {name}')
    rank_maps[name + '_off_rank'] = ranks(res, 'adj_off', True)
    rank_maps[name + '_def_rank'] = ranks(res, 'adj_def', False)

# ---- built-in consistency checks (abort on failure) ----
failures = []
if len(teams) != 32:
    failures.append(f'team count {len(teams)} != 32')
for name, res in metrics.items():
    so = sum(r['off_plays'] for r in res.values())
    sd = sum(r['def_plays'] for r in res.values())
    if so != sd:
        failures.append(f'{name}: off plays {so} != def plays {sd}')
    for side in ('off', 'def'):
        rk = sorted(rank_maps[f'{name}_{side}_rank'].values())
        if rk != list(range(1, len(teams) + 1)):
            failures.append(f'{name} {side} ranks are not 1..{len(teams)}')
    for tm in teams:
        if res[tm]['off_plays'] == 0 or res[tm]['def_plays'] == 0:
            failures.append(f'{name}: {tm} has zero plays on a side')
        if res[tm]['off_games'] != res[tm]['def_games']:
            failures.append(f'{name}: {tm} off games {res[tm]["off_games"]} != def games {res[tm]["def_games"]}')
# success and epa accepted samples should be identical unless exclusions say otherwise
if excluded.get('epa_null', 0) == 0 and excluded.get('success_unusable', 0) == 0:
    for tm in teams:
        for side in ('off_plays', 'def_plays'):
            if metrics['success'][tm][side] != metrics['epa'][tm][side]:
                failures.append(f'{tm} {side}: success {metrics["success"][tm][side]} != epa {metrics["epa"][tm][side]} despite zero null exclusions')
if kneel_leak or spike_leak:
    failures.append(f'kneel/spike flags found inside pass/run: {kneel_leak}/{spike_leak}')
if failures:
    sys.exit('CHECK FAILURES:\n' + '\n'.join(failures))

fieldnames = ['team', 'games']
for name in metrics:
    fieldnames += [f'{name}_plays', f'{name}_raw', f'{name}_adj', f'{name}_rank']

off_path = OUT_PREFIX + '_offense.csv'
def_path = OUT_PREFIX + '_defense.csv'
with open(off_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for tm in teams:
        row = {'team': tm, 'games': metrics['epa'][tm]['off_games']}
        for name, res in metrics.items():
            r = res[tm]
            row[f'{name}_plays'] = r['off_plays']
            row[f'{name}_raw'] = round(r['raw_off'], 6) if r['raw_off'] is not None else ''
            row[f'{name}_adj'] = round(r['adj_off'], 6)
            row[f'{name}_rank'] = rank_maps[name + '_off_rank'][tm]
        w.writerow(row)
with open(def_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for tm in teams:
        row = {'team': tm, 'games': metrics['epa'][tm]['def_games']}
        for name, res in metrics.items():
            r = res[tm]
            row[f'{name}_plays'] = r['def_plays']
            row[f'{name}_raw'] = round(r['raw_def'], 6) if r['raw_def'] is not None else ''
            row[f'{name}_adj'] = round(r['adj_def'], 6)
            row[f'{name}_rank'] = rank_maps[name + '_def_rank'][tm]
        w.writerow(row)

sha = hashlib.sha256(open(PBP_PATH, 'rb').read()).hexdigest()
meta = {
    'generated_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'builder': 'build_current_rankings_nfl.py v2',
    'kind': 'provisional_descriptive_rankings_not_validated_predictors',
    'team_count': len(teams),
    'source': {
        'url': SOURCE_URL,
        'sha256': sha,
        'source_last_updated': SOURCE_LAST_UPDATED,
        'license': 'CC BY 4.0 (nflverse)',
    },
    'coverage': {
        'total_pbp_rows': n_total,
        'accepted_plays_pass_run': accepted_total,
        'games_by_week': {str(k): games_by_week[k] for k in sorted(games_by_week)},
        'games_total': len(seen_games),
        'note': 'Derived from the input file at build time. Games not final in the source are absent; check nflverse schedules for pending games at integration time.',
    },
    'excluded_play_types': dict(play_type_counts),
    'excluded_from_accepted': dict(excluded),
    'classification_checks': {
        'qb_kneel_or_spike_flags_inside_pass_run': [kneel_leak, spike_leak],
        'qb_scramble_by_play_type': dict(scramble_by_type),
        'note': 'scrambles are play_type run (sacks are pass; scrambles excluded from pass split); no_play excluded; penalties on live scrimmage plays remain included',
    },
    'definitions': {
        'accepted_plays': 'play_type in {pass, run}; two_point_attempt excluded; kneels/spikes are distinct play_type values removed by that filter; sacks are pass; scrambles are run',
        'success': 'distance-based: 1st down >=50% of ydstogo, 2nd >=70%, 3rd/4th >=100%',
        'epa': 'nflfastR modeled epa; null epa excluded from EPA metrics only',
        'garbage_time': 'no adjustment (stated limit)',
        'opponent_adjustment': 'one weighted ridge per metric over team-game rows; features intercept + home + offense dummy + defense dummy; penalty 20 on team effects only; adjusted = intercept + effect',
        'rank_direction': 'offense descending (higher better); defense ascending (lower allowed better)',
        'denominators': 'per side: offensive columns use posteam plays, defensive columns use defteam plays; they differ by team',
        'splits': 'pass/run filters computed separately with own regressions and per-side play counts',
    },
}
meta_path = OUT_PREFIX + '_metadata.json'
with open(meta_path, 'w') as f:
    json.dump(meta, f, indent=2)

print(json.dumps({
    'teams': len(teams), 'accepted_plays': accepted_total, 'games': len(seen_games),
    'games_by_week': dict(sorted(games_by_week.items())),
    'excluded_from_accepted': dict(excluded),
    'scramble_by_play_type': dict(scramble_by_type),
    'denominator_check': {'ARI_off': metrics['epa']['ARI']['off_plays'], 'ARI_def': metrics['epa']['ARI']['def_plays'],
                          'ATL_off': metrics['epa']['ATL']['off_plays'], 'ATL_def': metrics['epa']['ATL']['def_plays']},
    'offense_top5_adj_epa': sorted(((tm, round(r['adj_off'], 4)) for tm, r in metrics['epa'].items()), key=lambda x: -x[1])[:5],
    'defense_top5_adj_epa': sorted(((tm, round(r['adj_def'], 4)) for tm, r in metrics['epa'].items()), key=lambda x: x[1])[:5],
    'files': [off_path, def_path, meta_path],
}, indent=2))
