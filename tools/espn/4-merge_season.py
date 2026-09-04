#!/usr/bin/env python3
"""Merge per-date ESPN scoreboard responses into a season game index.

Usage: merge_season.py DAYS_DIR OUT_CSV LEAGUE_LABEL SEASON_YEAR
DAYS_DIR holds files named <league>_<YYYYMMDD>.json (raw scoreboard JSON).
Rows keyed by event_id; re-runs are idempotent. Never deletes rows.
"""
import json, csv, os, sys

def main(days_dir, out_csv, league, year):
    games = {}
    if os.path.exists(out_csv):
        for r in csv.DictReader(open(out_csv, newline='')):
            games[r['event_id']] = r
    days = 0
    for fn in sorted(os.listdir(days_dir)):
        if not fn.endswith('.json'): continue
        try: d = json.load(open(os.path.join(days_dir, fn)))
        except Exception: continue
        days += 1
        for e in d.get('events', []):
            comp = e['competitions'][0]
            st = comp['status']['type']
            teams = {c['homeAway']: c for c in comp['competitors']}
            games[str(e['id'])] = {
                'event_id': str(e['id']), 'league': league, 'season': year,
                'date': comp.get('date', ''), 'name': e.get('name', ''),
                'away': teams.get('away', {}).get('team', {}).get('displayName', ''),
                'home': teams.get('home', {}).get('team', {}).get('displayName', ''),
                'away_score': teams.get('away', {}).get('score', ''),
                'home_score': teams.get('home', {}).get('score', ''),
                'completed': str(bool(st.get('completed'))),
                'status': st.get('description', '')}
    rows = sorted(games.values(), key=lambda r: (r['date'], r['event_id']))
    fields = ['event_id','league','season','date','name','away','home','away_score','home_score','completed','status']
    tmp = out_csv + '.tmp'
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(rows)
    os.replace(tmp, out_csv)
    print(json.dumps({'days_merged': days, 'games': len(rows),
                      'completed': sum(1 for r in rows if r['completed'] == 'True')}))

if __name__ == '__main__':
    main(*sys.argv[1:5])
