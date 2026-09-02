#!/usr/bin/env python3
import csv,json,re,sys,uuid,datetime,os,tempfile
FIELDS='capture_id quote_id captured_at source source_updated_at state sport event_id event_name kickoff book market_id market_type market_name player_id player_name selection_id selection line american_price decimal_price implied_probability quote_status opening_line opening_price first_observed closing_line closing_price result net_units model_version'.split()
NORMAL=[('passing_touchdowns',r'passing (?:tds|touchdowns)'),('passing_yards',r'passing yards'),('rushing_yards',r'rushing yards'),('receiving_yards',r'receiving yards'),('receptions',r'(?:^| )receptions(?: |$)'),('anytime_touchdown',r'anytime touchdown')]
LINE_REQUIRED={'passing_yards','passing_touchdowns','rushing_yards','receiving_yards','receptions'}
def norm(name):
 s=name.lower()
 for k,p in NORMAL:
  if re.search(p,s) and not re.search(r'\bmost\b|\bleader\b|\bto lead\b',s):return k
 return None
def parse_runner(name,mt):
 m=re.match(r'^(.*?)\s+(Over|Under)\s+(-?\d+(?:\.\d+)?)$',name,re.I)
 if m:return m.group(1).strip(),m.group(2).lower(),float(m.group(3))
 if mt=='anytime_touchdown':
  n=re.sub(r'\s+(?:Anytime Touchdown(?: Scorer)?|To Score(?: a)? Touchdown).*$', '', name, flags=re.I).strip()
  return n,'yes',None
 return '',name.strip(),None
def american_imp(a):return 100/(a+100) if a>0 else -a/(-a+100)
def extract(doc,state='VA',captured=None):
 captured=captured or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
 if state!='VA':raise ValueError('Fail closed: only verified VA catalog supported')
 att=doc.get('attachments') or {}; markets=att.get('markets'); events=att.get('events')
 if not isinstance(markets,dict) or not isinstance(events,dict):raise ValueError('Fail closed: missing FanDuel attachments markets/events')
 cap=str(uuid.uuid4()); rows=[]; skipped={}
 for mid,m in markets.items():
  mt=norm(str(m.get('marketName','')))
  if not mt:continue
  eid=m.get('eventId'); ev=events.get(str(eid),{})
  required=[state,eid,mid,m.get('marketName'),ev.get('name'),m.get('marketTime') or ev.get('openDate')]
  if any(x in (None,'') for x in required):raise ValueError(f'Fail closed: incomplete identity for market {mid}')
  runners=m.get('runners')
  if not isinstance(runners,list) or not runners:raise ValueError(f'Fail closed: no runners for {mid}')
  for r in runners:
   sid=r.get('selectionId'); rn=r.get('runnerName'); odds=r.get('winRunnerOdds') or {}
   amer=((odds.get('americanDisplayOdds') or {}).get('americanOddsInt'))
   dec=(((odds.get('trueOdds') or {}).get('decimalOdds') or {}).get('decimalOdds'))
   if sid in (None,'') or not rn:raise ValueError(f'Fail closed: missing selection identity for {mid}')
   if amer is None or not isinstance(amer,(int,float)) or amer==0:raise ValueError(f'Fail closed: malformed price {mid}/{sid}')
   pn,sel,line=parse_runner(rn,mt)
   if not pn:raise ValueError(f'Fail closed: cannot parse player for {mid}/{sid}: {rn}')
   if mt in LINE_REQUIRED and line is None:raise ValueError(f'Fail closed: required line absent {mid}/{sid}')
   rows.append(dict(capture_id=cap,quote_id=str(uuid.uuid4()),captured_at=captured,source='FanDuel Sportsbook structured market feed',source_updated_at='',state=state,sport='NFL',event_id=eid,event_name=ev['name'],kickoff=m.get('marketTime') or ev.get('openDate'),book='FanDuel',market_id=mid,market_type=mt,market_name=m['marketName'],player_id='',player_name=pn,selection_id=sid,selection=sel,line='' if line is None else line,american_price=int(amer),decimal_price=dec or '',implied_probability=american_imp(amer),quote_status=str(m.get('marketStatus') or r.get('runnerStatus') or '').lower(),opening_line='',opening_price='',first_observed=captured,closing_line='',closing_price='',result='',net_units='',model_version='v3-forward-measurement'))
 if not rows:raise ValueError('Fail closed: zero eligible NFL player-prop rows')
 # sanity: at least two stable IDs and all six requested base fields
 for x in rows:
  if not all(x[k] not in ('',None) for k in ('state','event_id','market_id','selection_id','american_price','captured_at')):raise ValueError('Fail closed: required row field blank')
 return rows
def append_atomic(rows,path):
 old=[]
 if os.path.exists(path):
  with open(path,newline='') as f:
   rd=csv.DictReader(f)
   if rd.fieldnames!=FIELDS:raise ValueError('Fail closed: existing ledger schema mismatch')
   old=list(rd)
 key=lambda r:(r['captured_at'],r['state'],r['book'],str(r['event_id']),str(r['market_id']),str(r['selection_id']),str(r['line']),str(r['american_price']))
 seen={key(r) for r in old}; add=[r for r in rows if key(r) not in seen]
 d=os.path.dirname(path) or '.'; fd,tmp=tempfile.mkstemp(dir=d,prefix='.fdprops-',text=True);os.close(fd)
 try:
  with open(tmp,'w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(old);w.writerows(add)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 return len(add)
if __name__=='__main__':
 if len(sys.argv)<3:raise SystemExit('usage: fanduel_capture_parser.py INPUT_JSON LEDGER_CSV [STATE]')
 doc=json.load(open(sys.argv[1])); rows=extract(doc,sys.argv[3] if len(sys.argv)>3 else 'VA'); n=append_atomic(rows,sys.argv[2]); print(json.dumps({'eligible_rows':len(rows),'appended':n,'markets':len({r['market_id'] for r in rows}),'players':len({r['player_name'] for r in rows}),'captured_at':rows[0]['captured_at'],'state':'VA'}))
