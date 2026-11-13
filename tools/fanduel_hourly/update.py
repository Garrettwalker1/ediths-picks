#!/usr/bin/env python3
"""Publish browser-captured public game comparisons only. Never modify model/seals."""
import json,re,sys,datetime,unicodedata
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def load(p):
 d=json.load(open(p));return json.loads(d['content']) if 'content'in d else d
def parse(d):
 assert d['state_evidence'] and all('Illinois Gaming Board' in s for s in d['state_evidence'])
 out=[]
 for r in d['rows']:
  teams=[x for x in r['teams'].splitlines() if not x.isdigit()]
  if len(teams)!=2:continue
  ls=r['text'].splitlines();i=next((i for i,s in enumerate(ls) if s.startswith('O ')),None)
  try:
   assert i is not None
   vals=dict(away_line=float(ls[i-3]),away_price=int(ls[i-2]),away_ml=int(ls[i-1]),total=float(ls[i][2:]),over_price=int(ls[i+1]),home_line=float(ls[i+2]),home_price=int(ls[i+3]),home_ml=int(ls[i+4]),under_total=float(ls[i+5][2:]),under_price=int(ls[i+6]))
   assert ls[i+5].startswith('U ') and vals['total']==vals['under_total'] and vals['away_line']==-vals['home_line']
  except (AssertionError,ValueError,IndexError,TypeError):continue
  out.append(dict(away=teams[0],home=teams[1],captured_at=d['at'],state='IL',provider='FanDuel',source_url=r['url'],kickoff_text=ls[i+7],**vals))
 return out
def norm(s):
 s=''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c))
 s=s.lower().replace('&','').replace("'",'').replace('.','').replace('state','st')
 aliases={'connecticut':'uconn','miami ohio':'miami oh','appalachian st':'app st','hawaii':'hawaii','florida international':'fiu','sam houston st':'sam houston','massachusetts':'umass','louisiana monroe':'ul monroe'}
 s=s.replace('florida international','fiu').replace('miami florida','miami')
 return aliases.get(s,s)
def match(short,long):
 a,b=norm(short),norm(long);return a==b or b.startswith(a+' ')
def line(q):
 x=q['home_line'];return 'PK' if x==0 else (q['home'] if x<0 else q['away'])+' -'+str(abs(x)).removesuffix('.0')
def validday(q,kick):
 # Raw book clock can differ minutes from schedule; calendar date must agree.
 dt=datetime.datetime.fromisoformat(kick.replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('America/Chicago'));cap=datetime.datetime.fromisoformat(q['captured_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('America/Chicago'));t=q['kickoff_text'];days=['MON','TUE','WED','THU','FRI','SAT','SUN']
 if any(t.startswith(x) for x in days):return t.startswith(days[dt.weekday()]) and 0<=(dt.date()-cap.date()).days<7
 if re.match(r'^\d',t):return dt.date()==cap.date()
 return False

def main(nfl,cfb):
 docs={s:load(p) for s,p in [('NFL',nfl),('CFB',cfb)]};parsed={s:parse(d) for s,d in docs.items()};now=max(d['at'] for d in docs.values());outpath=R/'fanduel_comparisons.json';old=json.load(open(outpath)) if outpath.exists() else {'nfl':{},'cfb':{}}
 out={'checked_at':now,'state':'IL','scope':'NFL/CFB game sides, moneylines and totals only. Public signed-out Illinois; not Tennessee. No player-market hourly coverage. Model/sealed evaluation references unchanged.','nfl':{},'cfb':{},'coverage':{}}
 sd=json.load(open(R/'tools/nfl/week10_2026/espn_week10.json'));sched=[]
 for e in sd['events']:
  c=e['competitions'][0]['competitors'];a=next(x for x in c if x['homeAway']=='away');h=next(x for x in c if x['homeAway']=='home');sched.append((a['team']['displayName'],h['team']['displayName'],a['team']['abbreviation'].replace('LAR','LA')+' at '+h['team']['abbreviation'].replace('LAR','LA'),e['date'],e['id']))
 root=(R/'index.html').read_text();current=json.JSONDecoder().raw_decode(root.split('const D=',1)[1])[0]['current']
 assert {x[2] for x in sched}=={g['matchup'] for g in current},'NFL slate changed: validate new source schedule before running'
 cg=json.load(open(R/'tools/cfb/week11_20261108/week11_sealed_research.json'))['games']
 for sport,games,key in [('NFL',sched,'nfl'),('CFB',[(g['away'],g['home'],g['event_id'],g['date'],g['event_id']) for g in cg],'cfb')]:
  counts={'matched':0,'missing':0,'frozen':0,'unrestorable_started':0}
  for a,h,k,kick,eid in games:
   if datetime.datetime.fromisoformat(kick.replace('Z','+00:00'))<=datetime.datetime.fromisoformat(now.replace('Z','+00:00')):
    if k in old[key] and old[key][k]['captured_at'] < kick:out[key][k]=dict(old[key][k],frozen=True);counts['frozen']+=1
    else:counts['unrestorable_started']+=1
    continue
   qs=[q for q in parsed[sport] if match(q['away'],a) and match(q['home'],h) and validday(q,kick)]
   if len(qs)!=1:
    counts['missing']+=1
    if k in old[key]:out[key][k]=dict(old[key][k],unavailable_at=now)
    continue
   q=dict(qs[0],kickoff=kick,event_id=eid,frozen=False);q['display']=line(q)+' · O/U '+str(q['total']);out[key][k]=q;counts['matched']+=1
  out['coverage'][sport]=dict(counts,returned=len(docs[sport]['rows']),parsed=len(parsed[sport]))
 stamp=now.replace(':','').replace('-','').replace('.','');folder=R/'tools/fanduel_hourly/captures'/stamp;folder.mkdir(parents=True,exist_ok=False)
 for sport,d in docs.items():(folder/(sport.lower()+'.json')).write_text(json.dumps(d,indent=2)+'\n')
 (folder/'comparison.json').write_text(json.dumps(out,indent=2)+'\n');outpath.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['coverage'],indent=2))
if __name__=='__main__':main(*sys.argv[1:])
