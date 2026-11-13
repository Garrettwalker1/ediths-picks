"""Fail-closed rendered selection-label parser. Candidate, NOT hourly coverage."""
import re
MARKETS={'Passing Yds':'passing_yards','Passing TDs':'passing_tds','Rushing Yds':'rushing_yards','Receiving Yds':'receiving_yards','Total Receptions':'receptions'}

def parse_label(label):
    if not isinstance(label,str):return None
    td=re.fullmatch(r'Any Time Touchdown Scorer, (.+), ([+-]\d+)',label)
    if td:
        name,price=td.groups()
        if 'Defense' in name:return None
        return {'player_name':name,'market':'anytime_td','side':'yes','line':0.5,'price':int(price)}
    # Exact duplicate name in market and selection catches association errors.
    prop=re.fullmatch(r'(.+) - (Passing Yds|Passing TDs|Rushing Yds|Receiving Yds|Total Receptions), (.+) (Over|Under), (\d+(?:\.\d+)?), ([+-]\d+)',label)
    if not prop:return None
    name,market,selection_name,side,line,price=prop.groups()
    if name!=selection_name:raise ValueError('selection/player mismatch')
    price=int(price);line=float(line)
    if abs(price)<100 or line*2!=int(line*2):raise ValueError('unsupported odds/line')
    return {'player_name':name,'market':MARKETS[market],'side':side.lower(),'line':line,'price':price}

def attach_identity(rows, event_id, kickoff, state, captured_at, source_url, identities):
    """identities: source-grounded event-local exact name -> list of player/team IDs.

    No fuzzy names, surname-only inference or default healthy status. Unmatched and
    ambiguous names stay explicit gaps, not published rows. Caller must verify
    source/kickoff/state and collection completeness independently.
    """
    published=[];gaps=[];seen=set()
    for row in rows:
        ids=identities.get(row['player_name'],[])
        if len(ids)!=1:
            gaps.append(dict(row,reason='missing_identity'if not ids else'ambiguous_identity'));continue
        identity=ids[0]
        if not identity.get('player_id')or not identity.get('team_id'):raise ValueError('identity missing stable IDs')
        key=(identity['player_id'],row['market'],row['side'])
        if key in seen:raise ValueError('duplicate market selection')
        seen.add(key);published.append(dict(row,**identity,event_id=str(event_id),kickoff=kickoff,state=state,captured_at=captured_at,source_url=source_url))
    return published,gaps
