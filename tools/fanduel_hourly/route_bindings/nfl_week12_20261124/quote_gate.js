const known={"/football/nfl/green-bay-packers-@-los-angeles-rams-35607031":{"event_id":"401873079","kickoff":"2026-11-26T01:00Z","frozen":false,"conflict":false},"/football/nfl/chicago-bears-@-detroit-lions-35607159":{"event_id":"401873081","kickoff":"2026-11-26T18:00Z","frozen":false,"conflict":false},"/football/nfl/philadelphia-eagles-@-dallas-cowboys-35599534":{"event_id":"401873080","kickoff":"2026-11-26T21:30Z","frozen":false,"conflict":false}};

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
return{at:new Date().toISOString(),url:location.href,state_evidence:(()=>{const x=document.evaluate("//text()[contains(.,'authorized by the Illinois Gaming Board')]",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);return Array.from({length:x.snapshotLength},(_,i)=>x.snapshotItem(i).textContent)})(),rows,excluded,schedule_gate:'known verified kickoff strictly future, no frozen/conflicting state'};
