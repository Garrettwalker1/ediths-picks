"""Merge actual event captures without relabeling old prices as fresh.
The caller supplies only source-verified event artifacts from build_player_comparison.
"""
import argparse, collections, datetime, json, pathlib
from build_player_comparison import load, stamp, R

NOTE = ('Book listing and roster membership are not game clearance. Model figures retain their own older source times and have no new injury/workload adjustment. Book prices are comparisons only; no betting edge or current TN offer claimed.')

def merge(previous, incoming, slate, as_of):
    games = {str(g['event_id']):g for g in slate}
    events = {e['event_id']:dict(e) for e in previous.get('events',[])}
    if not events and previous.get('event_id'):
        event = {k:previous[k] for k in ['checked_at','state','event_id','matchup','kickoff','source_url','coverage','rows','identity_gaps']}
        event['coverage'] = {k:v for k,v in event['coverage'].items() if k!='other_events_not_captured'}
        events[event['event_id']] = event
    seen=set()
    for event in incoming:
        eid=event['event_id']
        if eid in seen or eid not in games:
            raise ValueError('duplicate incoming or unknown event')
        seen.add(eid)
        if stamp(event['kickoff'])!=stamp(games[eid]['date']):
            raise ValueError('event kickoff changed: reconcile before merge')
        if stamp(event['checked_at'])>=stamp(event['kickoff']) or stamp(event['checked_at'])>as_of:
            raise ValueError('not actual pregame capture')
        # Once an event has kicked off, never backfill a new closing snapshot.
        if stamp(event['kickoff'])<=as_of:
            raise ValueError('cannot replace kicked-off event')
        old=events.get(eid)
        if old:
            gap=(stamp(event['checked_at'])-stamp(old['checked_at'])).total_seconds()
            if gap<3600:
                raise ValueError('event refresh is not at least 60 minutes after previous capture')
        if any(r['event_id']!=eid or r['captured_at']!=event['checked_at'] or r['source_url']!=event['source_url'] for r in event['rows']):
            raise ValueError('row provenance differs from event')
        events[eid]=event
    ordered=[]
    for eid,game in games.items():
        if eid not in events:continue
        event=events[eid]
        if stamp(event['kickoff'])!=stamp(game['date']):
            raise ValueError('previous event kickoff changed: reconcile')
        event['frozen']=stamp(event['kickoff'])<=as_of
        ordered.append(event)
    rows=[r for e in ordered for r in e['rows']]
    gaps=[dict(r,event_id=e['event_id']) for e in ordered for r in e['identity_gaps']]
    coverage={k:sum(e['coverage'][k] for e in ordered) for k in ['rendered_target_accordions','parsed_selections','joined_selections','unmatched_selections']}
    coverage.update(market_player_rows=dict(collections.Counter(r['market'] for r in rows)),events_captured=len(ordered),events_total=len(games),other_events_not_captured=len(games)-len(ordered))
    prefix='PARTIAL' if len(ordered)<len(games) else 'All scheduled events captured'
    return dict(assembled_at=as_of.isoformat(),checked_at=max((e['checked_at'] for e in ordered),key=stamp) if ordered else None,scope=f'{prefix}: {len(ordered)} of {len(games)} NFL events. Source times and pregame freezes are per event; a rebuilt board is not a fresh price capture. Recurring full-slate coverage remains unverified.',state='IL',model_inputs_changed=False,availability_note=NOTE,coverage=coverage,events=ordered,rows=rows,identity_gaps=gaps)

def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True,type=pathlib.Path);p.add_argument('--event',action='append',default=[],type=pathlib.Path);p.add_argument('--output',required=True,type=pathlib.Path);p.add_argument('--as-of')
    args=p.parse_args();now=stamp(args.as_of) if args.as_of else datetime.datetime.now(datetime.timezone.utc)
    result=merge(load(args.previous),[load(path) for path in args.event],load(R/'tools/nfl/current_season_20261113/current_forecasts.json')['games'],now)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['coverage'],indent=2))

if __name__=='__main__':main()
