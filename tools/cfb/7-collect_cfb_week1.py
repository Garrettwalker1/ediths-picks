#!/usr/bin/env python3
"""Collect 2026 CFB Week 1 games + box scores from ESPN.

Input: a directory of raw ESPN scoreboard day responses (JSON) fetched out of band
(web_fetch or cloud browser; sandbox egress to site.api.espn.com is unreliable).
Merges them into the tracker artifact and lists event_ids that went final since the
last run and still need a box-score pull (summary?event=<id>).

Usage: collect_cfb_week1.py DAYS_DIR TRACKER_JSON BOXSCORE_DIR
Never deletes history. Games are keyed by event_id; re-runs update status/scores only.
"""
import json, os, sys, datetime

def main(days_dir, tracker_path, box_dir):
    games = {}
    if os.path.exists(tracker_path):
        old = json.load(open(tracker_path))
        games = {g['event_id']: g for g in old.get('games', [])}
    had_box = {f[:-5].split('-', 1)[-1] for f in os.listdir(box_dir) if f.endswith('.json')} if os.path.isdir(box_dir) else set()
    for fn in sorted(os.listdir(days_dir)):
        if not fn.endswith('.json'): continue
        try: d = json.load(open(os.path.join(days_dir, fn)))
        except Exception: continue
        for e in d.get('events', []):
            comp = e['competitions'][0]
            st = comp['status']['type']
            teams = {c['homeAway']: c for c in comp['competitors']}
            games[str(e['id'])] = {
                'event_id': str(e['id']), 'date': comp.get('date', ''), 'name': e.get('name', ''),
                'away': teams.get('away', {}).get('team', {}).get('displayName', ''),
                'home': teams.get('home', {}).get('team', {}).get('displayName', ''),
                'away_score': teams.get('away', {}).get('score', ''),
                'home_score': teams.get('home', {}).get('score', ''),
                'status': st.get('description', ''), 'state': st.get('state', ''),
                'completed': bool(st.get('completed'))}
    gs = sorted(games.values(), key=lambda g: (g['date'], g['event_id']))
    need_box = [g['event_id'] for g in gs if g['completed'] and g['event_id'] not in had_box]
    built = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    doc = {
        'schema_version': '1.0.0', 'season': 2026, 'week': 1, 'built_at': built,
        'purpose': 'Track every FBS college football game from 2026 Week 1 (season started 2026-09-03) with results and, once final, box-score stats. These facts feed the CFB model; book lines never do.',
        'scope': 'FBS only (ESPN groups=80). FCS excluded.',
        'source': 'ESPN scoreboard API site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard per date, window 2026-08-29..2026-09-08',
        'known_gaps': ['2026-09-02 fetch timed out twice; assumed 0 FBS games (Wednesday before kickoff). Re-verify on next cadence run.'],
        'coverage': {'games': len(gs),
                     'final': sum(1 for g in gs if g['completed']),
                     'in_progress': sum(1 for g in gs if g['state'] == 'in'),
                     'scheduled': sum(1 for g in gs if g['state'] == 'pre'),
                     'boxscores_collected': len(had_box)},
        'games': gs}
    tmp = tracker_path + '.tmp'
    json.dump(doc, open(tmp, 'w'), indent=1)
    os.replace(tmp, tracker_path)
    print(json.dumps({'games': len(gs), 'final': doc['coverage']['final'],
                      'boxscores_collected': len(had_box), 'need_boxscore': need_box}))

if __name__ == '__main__':
    main(*sys.argv[1:4])
