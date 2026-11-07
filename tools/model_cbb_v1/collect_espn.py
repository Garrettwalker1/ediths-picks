#!/usr/bin/env python3
"""Public ESPN collection only. No forecasts, paid feeds, or closing-line claims."""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from zoneinfo import ZoneInfo

BASE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball'
ROOT = Path(__file__).resolve().parent / 'data'
CT = ZoneInfo('America/Chicago')

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with (gzip.open(temp, 'wt') if path.suffix == '.gz' else open(temp, 'w')) as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
    os.replace(temp, path)

def read(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else open(path)) as f:
        return json.load(f)

def get(url):
    error = None
    for attempt in range(3):
        started = now()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (basketball research)'})
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read()
            data = json.loads(raw)
            time.sleep(0.3)
            return data, {'url': url, 'requested_at': started, 'received_at': now(),
                          'payload_sha256': hashlib.sha256(raw).hexdigest()}
        except Exception as e:
            error = str(e)
            time.sleep(1 + attempt)
    return None, {'url': url, 'requested_at': started, 'received_at': now(), 'error': error}

def event(e):
    comp = e.get('competitions', [{}])[0]
    return {k: e.get(k) for k in ('id', 'date', 'name', 'status')} | {
        'competition': {k: comp.get(k) for k in ('id', 'date', 'neutralSite', 'venue', 'competitors', 'status', 'odds')}}

def scoreboard(day):
    d, source = get(f'{BASE}/scoreboard?dates={day}&limit=400&groups=50')
    if d is None:
        return None, source
    events = [event(e) for e in d.get('events', [])]
    write(ROOT / 'scoreboards' / f'{day}.json.gz', {'source': source, 'events': events,
          'coverage': 'ESPN groups=50. Includes D1 teams playing non-D1 opponents; not a strict D1-v-D1 filter.'})
    return events, source

def final(e):
    return bool((e.get('status') or e['competition'].get('status') or {}).get('type', {}).get('completed')) and (e.get('status') or {}).get('type', {}).get('state') == 'post'

def complete_box(d):
    box = d.get('boxscore') or {}
    teams = box.get('teams') or []
    players = box.get('players') or []
    return len(teams) == 2 and all(t.get('statistics') for t in teams) and len(players) == 2 and all(any(g.get('athletes') for g in p.get('statistics', [])) for p in players)

def collect(days, summary_limit):
    records = {}; failures = []; fetched = 0
    for day in days:
        events, source = scoreboard(day)
        if events is None:
            failures.append(source); continue
        for e in events:
            if not final(e):
                continue
            records[e['id']] = e
            out = ROOT / 'summaries' / f"{e['id']}.json.gz"
            if out.exists():
                existing = read(out)
                if complete_box(existing):
                    continue
            if fetched >= summary_limit:
                continue
            d, src = get(f"{BASE}/summary?event={e['id']}")
            if d is None:
                failures.append(src); continue
            # Deliberately exclude news, articles, ads, videos and unrelated prose.
            attempts = read(out).get('collection_attempts', 0) + 1 if out.exists() else 1
            write(out, {'source': src, 'collection_attempts': attempts, 'header': d.get('header'), 'boxscore': d.get('boxscore'),
                        'gameInfo': d.get('gameInfo')})
            fetched += 1
    # Merge keyed finals from all refreshed days. Historical observations are not pregame feature snapshots.
    path = ROOT / 'finals.json.gz'
    all_records = read(path).get('events', {}) if path.exists() else {}
    all_records.update(records)
    write(path, {'updated_at': now(), 'events': all_records,
                'warning': 'Postgame fetch. Ranks, records and rosters are NOT verified historical pregame features.'})
    incomplete = [eid for eid in all_records if (ROOT / 'summaries' / f'{eid}.json.gz').exists() and not complete_box(read(ROOT / 'summaries' / f'{eid}.json.gz'))]
    report = {'summaries_incomplete': incomplete, 'at': now(), 'days': days, 'finals_seen': len(records), 'finals_total': len(all_records),
              'summaries_fetched': fetched, 'summary_limit': summary_limit, 'failures': failures,
              'summaries_missing': [eid for eid in all_records if not (ROOT / 'summaries' / f'{eid}.json.gz').exists()]}
    write(ROOT / 'last_harvest.json', report)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    write(ROOT / 'harvest_runs' / f'{stamp}.json', report)
    return report

def odds(day):
    events, source = scoreboard(day)
    rows = []
    if events is not None:
        for e in events:
            state = (e.get('status') or {}).get('type', {}).get('state')
            row = {'event_id': e['id'], 'name': e['name'], 'scheduled_start': e['date'],
                   'scoreboard_state': state, 'scoreboard_source': source,
                   'competitors': e['competition'].get('competitors')}
            if state != 'pre':
                row.update(result='not_pregame', captured_at=now()); rows.append(row); continue
            d, src = get(f"{BASE}/summary?event={e['id']}")
            row['source'] = src
            if d is None:
                row.update(result='fetch_failed'); rows.append(row); continue
            c = (d.get('header') or {}).get('competitions', [{}])[0]
            summary_state = (c.get('status') or {}).get('type', {}).get('state')
            start = c.get('date') or e['date']
            row.update(summary_state=summary_state, summary_start=start, captured_at=src['received_at'])
            try:
                before_tip = dt.datetime.fromisoformat(src['received_at']) < dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                before_tip = False
            if summary_state != 'pre' or not before_tip:
                row.update(result='not_verified_pregame'); rows.append(row); continue
            lines = d.get('pickcenter') or d.get('odds') or []
            usable = [o for o in lines if isinstance(o, dict) and (o.get('spread') is not None or o.get('overUnder') is not None)]
            row.update(result='captured' if usable else 'no_line', lines=lines,
                       label='Pregame capture, NOT verified closing line. Provider preserved per line.')
            rows.append(row)
    counts = {}
    for row in rows:
        counts[row['result']] = counts.get(row['result'], 0) + 1
    result = {'day': day, 'run_at': now(), 'scoreboard_source': source, 'counts': counts, 'events': rows,
              'warning': 'Missing odds stay missing. Never substitute zero or call a scheduled capture the close.'}
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    write(ROOT / 'odds' / f'{day}_{stamp}.json.gz', result)
    return {'day': day, 'counts': counts, 'scoreboard_failed': events is None}

def backfill(start, end, day_limit, summary_limit):
    manifest = ROOT / 'backfill_progress.json'
    p = read(manifest) if manifest.exists() else {'done_days': []}
    done = set(p['done_days']); pending = []
    d = dt.date.fromisoformat(start); last = dt.date.fromisoformat(end)
    while d <= last and len(pending) < day_limit:
        key = d.strftime('%Y%m%d')
        if key not in done:
            pending.append(key)
        d += dt.timedelta(days=1)
    report = collect(pending, summary_limit)
    for day in pending:
        path = ROOT / 'scoreboards' / f'{day}.json.gz'
        if not path.exists():
            continue
        events = read(path)['events']
        # Retry days with uncollected or empty boxscores; postponed games are not invented finals.
        finals = [e for e in events if final(e)]
        if all((ROOT / 'summaries' / f"{e['id']}.json.gz").exists() and (complete_box(read(ROOT / 'summaries' / f"{e['id']}.json.gz")) or read(ROOT / 'summaries' / f"{e['id']}.json.gz").get('collection_attempts', 0) >= 2) for e in finals):
            done.add(day)
    write(manifest, {'updated_at': now(), 'start': start, 'end': end, 'done_days': sorted(done),
                     'last_batch': pending, 'incomplete_summary_ids': report['summaries_incomplete'], 'warning': 'Collection only. Holdout selection and evaluation remain separate.'})
    return report

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=['daily', 'odds', 'range', 'backfill'])
    ap.add_argument('--day', default=dt.datetime.now(CT).strftime('%Y%m%d'))
    ap.add_argument('--start', default='2024-11-01'); ap.add_argument('--end', default='2026-04-15')
    ap.add_argument('--day-limit', type=int, default=7); ap.add_argument('--summary-limit', type=int, default=100)
    args = ap.parse_args()
    if args.mode == 'odds':
        result = odds(args.day)
    elif args.mode == 'daily':
        today = dt.datetime.now(CT).date()
        result = collect([(today - dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(4, 0, -1)], args.summary_limit)
    elif args.mode == 'backfill':
        result = backfill(args.start, args.end, args.day_limit, args.summary_limit)
    else:
        a = dt.date.fromisoformat(args.start); b = dt.date.fromisoformat(args.end)
        result = collect([(a + dt.timedelta(days=i)).strftime('%Y%m%d') for i in range((b-a).days+1)], args.summary_limit)
    print(json.dumps(result, indent=2))
