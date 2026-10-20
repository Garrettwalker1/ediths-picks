#!/usr/bin/env python3
"""Leg-level spread/total performance from actual logged tickets (bets.json).
Rules: only legs on settled logged tickets; a leg counts only with its own explicit hit boolean already recorded on the leg; ticket outcomes are never imputed to legs; identical legs duplicated across tickets (same event+market+selection+line) count once. Not a validated-edge claim; sample is small and self-selected (these are legs Garrett chose to play)."""
import json,pathlib,datetime,re
R=pathlib.Path(__file__).resolve().parents[2]
d=json.load(open(R/'bets.json'))
SCOPE=re.compile(r'spread|total',re.I)
def sport_of(b,leg):
    e=str(leg.get('event') or leg.get('game') or b.get('game',''))
    return b.get('sport') or ''
seen={}
for b in d['bets']:
    if b.get('status')!='settled':continue
    for leg in b.get('legs',[]):
        m=str(leg.get('market',''))
        if not SCOPE.search(m):continue
        ev=leg.get('event') or leg.get('game') or b.get('game')
        key=(ev,m,leg.get('selection'),leg.get('line'))
        hit=leg.get('hit')
        rec=dict(event=ev,market=m,selection=leg.get('selection'),line=leg.get('line'),sport=b.get('sport'),ticket=b['bet'],ticket_date=b['date'][:10],ticket_result=b['result'],hit=hit)
        if key in seen and seen[key]['hit'] is None and hit is not None:seen[key]=rec
        elif key not in seen:seen[key]=rec
legs=list(seen.values())
def tally(rows):
    w=sum(1 for r in rows if r['hit'] is True);l=sum(1 for r in rows if r['hit'] is False);u=sum(1 for r in rows if r['hit'] is None)
    return dict(graded=w+l,wins=w,losses=l,ungraded=u)
out=dict(generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 scope='Legs on settled logged tickets whose market mentions spread or total (alt and standard). Legs count only with an explicit per-leg hit flag; ticket outcomes never imputed; duplicate legs across tickets counted once.',
 caveat='Small, self-selected sample of legs Garrett played. Performance context, not a validated edge or model-quality proof.',
 totals=tally(legs),
 by_sport={s:tally([r for r in legs if r['sport']==s]) for s in sorted({r['sport'] for r in legs})},
 nfl_alt=tally([r for r in legs if r['sport']=='NFL' and 'alternate' in r['market'].lower()]),
 nfl_standard=tally([r for r in legs if r['sport']=='NFL' and 'alternate' not in r['market'].lower()]),
 legs=sorted(legs,key=lambda r:r['ticket_date']))
json.dump(out,open(R/'tools/ledger/leg_level_spread_total_performance.json','w'),indent=1)
print('totals',out['totals']);print('by_sport',out['by_sport']);print('nfl_alt',out['nfl_alt']);print('nfl_standard',out['nfl_standard'])
for r in legs:
    if r['sport']=='NFL' and 'alternate' in r['market'].lower():print(r['ticket_date'],r['event'],r['market'],r['selection'],r['line'],'hit' if r['hit'] else 'MISS' if r['hit'] is False else 'ungraded')
