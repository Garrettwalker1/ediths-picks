let cfbLoaded=false;
async function loadInlineCfb(){
 if(cfbLoaded)return;
 const host=document.getElementById('cfbInline');
 try{
  const r=await fetch('cfb-board-2026-week6.html?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(r.status);
  const doc=new DOMParser().parseFromString(await r.text(),'text/html');
  const data=JSON.parse(doc.getElementById('board-data').textContent);
  const wrap=doc.querySelector('.wrap');const board=wrap.querySelector('section[data-week]');
  const games=board.querySelectorAll('details.game');
  games.forEach((game,i)=>{
   const g=data.games[i];game.dataset.frozen=String(!!g.book_frozen_pregame);game.dataset.name=g.name.toLowerCase();game.dataset.date=g.date.slice(0,10);game.dataset.wx=String(!!g.weather_context);
   const summary=game.querySelector('summary');const numbers=document.createElement('div');numbers.className='cfb-values';summary.querySelectorAll('.bgrid').forEach(n=>{numbers.appendChild(n);});summary.appendChild(numbers);
   const hint=document.createElement('div');hint.className='cfb-card-hint';hint.textContent=g.book_frozen_pregame?'Frozen pregame · tap for quote and sources':'Tap for lines, weather and sources';summary.appendChild(hint);
   game.querySelectorAll('.bfoot table').forEach(table=>{const labels=[...table.querySelectorAll('th')].map(x=>x.textContent);table.querySelectorAll('tr').forEach(tr=>tr.querySelectorAll('td').forEach((td,k)=>td.dataset.label=labels[k]||''));});
  });
  const notes=[...wrap.querySelectorAll('.note-card')].map(n=>n.outerHTML).join('');
  host.innerHTML=`<div class="cfb-fresh">${doc.getElementById('updated').textContent}</div><div class="cfb-stats"><div><strong>${data.games.length}</strong><span>Games covered</span></div><div><strong>${data.games.filter(g=>!g.book_frozen_pregame).length}</strong><span>Upcoming</span></div><div><strong>${data.games.filter(g=>g.book_frozen_pregame).length}</strong><span>Frozen pregame</span></div><div><strong>v2.2</strong><span>Baseline unchanged</span></div></div><div class="cfb-warning">Measurement only, not picks. WX UNPROVEN failed validation. The official MODEL and grading stay unchanged; book lines are comparison only.</div><div class="cfb-toolbar"><input id="cfbSearch" aria-label="Search CFB teams" placeholder="Search teams..."><div class="cfb-filter"><button class="active" data-cfb-filter="all">All games</button><button data-cfb-filter="upcoming">Upcoming</button><button data-cfb-filter="frozen">Frozen</button><button data-cfb-filter="weather">Weather</button></div></div><div id="cfbCount" class="cfb-count"></div><div id="cfbGames"></div><p id="cfbEmpty" hidden>No games match. Try another team or filter.</p><details class="cfb-method"><summary>Model, sources and limits</summary>${notes}<p>${data.weather_context_note||''}</p></details>`;
  host.querySelector('#cfbGames').appendChild(board);
  let mode='all';function filter(){const q=host.querySelector('#cfbSearch').value.toLowerCase();let n=0;games.forEach(g=>{const show=g.dataset.name.includes(q)&&(mode==='all'||mode==='upcoming'&&g.dataset.frozen==='false'||mode==='frozen'&&g.dataset.frozen==='true'||mode==='weather'&&g.dataset.wx==='true');g.hidden=!show;if(show)n++;});board.querySelectorAll('.day-label').forEach(label=>{let node=label.nextElementSibling,visible=false;while(node&&!node.classList.contains('day-label')){if(node.matches('details.game')&&!node.hidden)visible=true;node=node.nextElementSibling;}label.hidden=!visible;});host.querySelector('#cfbCount').textContent=`${n} games · MODEL / BOOK IL / WX UNPROVEN`;host.querySelector('#cfbEmpty').hidden=n!==0;}
  host.querySelector('#cfbSearch').oninput=filter;host.querySelectorAll('[data-cfb-filter]').forEach(b=>b.onclick=()=>{mode=b.dataset.cfbFilter;host.querySelectorAll('[data-cfb-filter]').forEach(x=>x.classList.toggle('active',x===b));filter();});filter();
  window.inlineCfbData=data;cfbLoaded=true;
 }catch(e){host.innerHTML='<div class="cfb-warning">The board could not load. Refresh to try again. No numbers have been replaced.</div>';}
}
document.querySelector('[data-tab="cfb"]').addEventListener('click',loadInlineCfb);
