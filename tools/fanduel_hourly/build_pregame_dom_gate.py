"""Build a fail-closed DOM quote gate from existing verified schedule/state. No network."""
import datetime,hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parents[2]
def build(repo):
 repo=pathlib.Path(repo); overlay=json.loads((repo/'fanduel_comparisons.json').read_text()); verified=json.loads((repo/'cfb_schedule_verified.json').read_text()).get('events',{});routes={};conflicts=[]
 for sport in ('nfl','cfb'):
  for key,row in overlay[sport].items():
   url=row.get('source_url'); kickoff=row.get('kickoff'); eid=str(row.get('event_id',''))
   if not url:continue
   route='/'+'/'.join(url.split('/')[3:]).split('?')[0].rstrip('/')
   v=verified.get(eid,{}) if sport=='cfb' else {}
   verified_kick=v.get('kickoff') or v.get('date')
   conflict=bool(verified_kick and kickoff and datetime.datetime.fromisoformat(verified_kick.replace('Z','+00:00'))!=datetime.datetime.fromisoformat(kickoff.replace('Z','+00:00')))
   if conflict:conflicts.append(eid)
   rec={'event_id':eid,'kickoff':kickoff,'frozen':bool(row.get('frozen')),'conflict':conflict}
   if route in routes and routes[route]!=rec:rec['conflict']=True;conflicts.append(eid)
   routes[route]=rec
 # Optional current-slate bindings are re-derived from metadata, never blindly trusted.
 for metadata_path in sorted((repo/'tools/fanduel_hourly/route_bindings').glob('*/metadata.json')):
  from bind_current_cfb_routes import bind
  metadata=json.loads(metadata_path.read_text())
  for row in bind(repo,metadata)['accepted']:
   route='/'+'/'.join(row['url'].split('/')[3:]).split('?')[0].rstrip('/')
   rec={'event_id':str(row['event_id']),'kickoff':row['kickoff'],'frozen':False,'conflict':False}
   if route in routes and routes[route]!=rec:rec['conflict']=True;conflicts.append(str(row['event_id']))
   routes[route]=rec
 return routes,conflicts
JS=r'''
const rows=[],excluded=[];
const route=location.href.includes('ncaaf')?'/football/ncaa-football-games/':'/football/nfl/';
function mayReadQuote(href,now){
 let path;try{path=new URL(href,location.href).pathname.replace(/\/$/,'');}catch{return false;}
 const s=known[path];if(!s||s.frozen||s.conflict)return false;
 const kick=Date.parse(s.kickoff);return Number.isFinite(kick)&&now<kick;
}
for(const a of document.querySelectorAll('a[href]')){
 if(!a.href.includes(route))continue;
 // No link text, parent text, prices or descendants are read until the schedule gate passes.
 if(!mayReadQuote(a.href,Date.now())){excluded.push({url:a.href,reason:'unknown, conflicting, frozen or started schedule'});continue;}
 if(!a.innerText.includes('\n'))continue;
 let p=a;for(let i=0;p&&i<9;i++,p=p.parentElement){
  // A broad page ancestor can contain live games; never inspect its aggregate price text.
  const eventPaths=new Set(Array.from(p.querySelectorAll?p.querySelectorAll('a[href]'):[]).map(x=>{try{return new URL(x.href,location.href).pathname.replace(/\/$/,'');}catch{return '';}}).filter(x=>x.includes(route)));
  if(eventPaths.size>1){excluded.push({url:a.href,reason:'ambiguous multi-event ancestor'});break;}
  const t=p.innerText;if(/\nO \d/.test(t)&&/\nU \d/.test(t)&&/\d+:\d+.*CT/.test(t)){rows.push({teams:a.innerText,text:t,url:a.href});break;}}
}
return{at:new Date().toISOString(),url:location.href,state_evidence:document.body.innerText.split('\n').filter(x=>x.includes('Illinois Gaming Board')),rows,excluded,schedule_gate:'known verified kickoff strictly future, no frozen/conflicting state'};
'''
def generate(repo):
 routes,conflicts=build(repo)
 return 'const known='+json.dumps(routes,separators=(',',':'))+';\n'+JS,{'routes':len(routes),'conflicts':conflicts,'input_sha256':hashlib.sha256((pathlib.Path(repo)/'fanduel_comparisons.json').read_bytes()).hexdigest()}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--repo',default=str(R));p.add_argument('--output',required=True);a=p.parse_args();script,meta=generate(a.repo);pathlib.Path(a.output).write_text(script);print(json.dumps(meta))
