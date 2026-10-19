let cfbLoaded=false;
async function loadInlineCfb(){
 if(cfbLoaded)return;
 const host=document.getElementById('cfbInline');
 try{
  const r=await fetch('cfb-board-2026-week7.html?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(r.status);
  const doc=new DOMParser().parseFromString(await r.text(),'text/html');
  const data=JSON.parse(doc.getElementById('board-data').textContent);
  doc.querySelectorAll('.chip').forEach(c=>{if(c.textContent.trim()==='VALIDATION PENDING')c.textContent='VALIDATION PENDING - OCT 11, SUPERSEDED';});
  doc.querySelectorAll('p,div,span').forEach(el=>{if(el.children.length===0){const t=el.textContent;
   if(t.includes('2026-inclusive repaired model, validation pending'))el.textContent='2026-inclusive repaired model. Oct 11 label "validation pending" is historical - the Week 7 forward test was graded Oct 18: no AP adoption (see banner).';
   if(t.includes('Winner-first improvement is unproven; Week7 forward test is sealed.'))el.textContent=t.textContent.replace('Winner-first improvement is unproven; Week7 forward test is sealed.','Week 7 forward test was sealed Oct 11 and graded Oct 18 - the AP variant did not beat the no-AP reference; no adoption.');}});
  const fresh=await fetch('cfb_current_status.json?ts='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()});const wrap=doc.querySelector('.wrap');const board=wrap.querySelector('section[data-week]');
  const games=board.querySelectorAll('details.game');
  const half=x=>{const n=Math.round(Math.abs(x)*2)/2;return n.toFixed(n%1?1:0);};
  const line=(g,x)=>Math.abs(x)<0.25?'PK':`${x>0?g.home:g.away} -${half(x)}`;
  const numberRow=(label,value)=>{const row=document.createElement('div');row.className='bgrid';const a=document.createElement('span');a.className='bg-lab';a.textContent=label;const b=document.createElement('span');b.className='bnum';b.textContent=value;row.append(a,b);return row;};
  const detailText=(parent,text)=>{const p=document.createElement('p');p.className='muted';p.textContent=text;parent.appendChild(p);};
  games.forEach((game,i)=>{
   const g=data.games[i],live=fresh.events[g.event_id];game.dataset.started=String(live?.state!=='pre');game.dataset.frozen=String(!!g.book_frozen_pregame);game.dataset.name=g.name.toLowerCase();game.dataset.date=g.date.slice(0,10);game.dataset.wx=String(!!g.weather_context||!!live?.weather_note);
   const summary=game.querySelector('summary');const update=document.createElement('p');update.className='muted';update.textContent=(live?.state==='post'?'Final - sealed pregame prediction retained':live?.state==='in'?'In progress - sealed pregame prediction retained':'Upcoming - kickoff rechecked')+(live?.weather_note?' · '+live.weather_note:'');summary.appendChild(update);const numbers=document.createElement('div');numbers.className='cfb-values';summary.querySelectorAll('.bgrid').forEach(n=>{numbers.appendChild(n);});summary.appendChild(numbers);
   if(live?.current_stats){
    const cr=live.current_stats;
    if(Math.abs(cr.difference_raw)>1e-8)numbers.appendChild(numberRow('STATS UNPROVEN',line(g,cr.current_stats_research_margin_home_raw)));
    if(live.weather_experiment)numbers.appendChild(numberRow('WX UNPROVEN',line(g,live.weather_experiment.weather_margin_home_raw)));
    const box=document.createElement('div');box.className='cfb-current-inputs';
    detailText(box,'Current inputs checked '+new Date(fresh.checked_at).toLocaleString()+'. Frozen Week7 research baseline and original evaluation unchanged.');
    detailText(box,'Stats:455/455 completed FBS-involving games archived;7 new Week7 finals and3 stale nonfinal payloads repaired. Current stats research uses original fitted coefficients, not a Week7 refit. '+(Math.abs(cr.difference_raw)>1e-8?'This game changed after an old missing final was restored.':'Current stats number is unchanged.'));
    detailText(box,'Current stats research home margin (unrounded): '+cr.current_stats_research_margin_home_raw.toFixed(3)+'. Sealed baseline (unrounded): '+cr.sealed_baseline_margin_home_raw.toFixed(3)+'.');
    const w=live.weather;
    detailText(box,w.venue.indoor?'Weather: indoor venue. No outdoor weather delta.':'Weather: '+w.venue.fullName+'; '+w.location.name+', '+w.location.admin1+' city forecast, not stadium microclimate. Kickoff '+w.temperature_f+' F; five-hour window rain max '+w.rain_chance_max+'%, accumulated rain '+w.rain_inches.toFixed(2)+'in, sustained wind max '+w.wind_max+'mph, gust '+w.gust_max+'mph.');
    detailText(box,'WX UNPROVEN = unchanged sealed baseline plus failed-validation weather candidate. Not an adopted improvement, not a bet signal.2024 error worsened;2025 comparison inconclusive; historical observed weather differs from pregame forecasts. No injury adjustment or weather total.');
    const av=document.createElement('details');const sum=document.createElement('summary');sum.textContent='Availability: '+live.injury_coverage;av.appendChild(sum);
    for(const t of live.injuries){
     const h=document.createElement('h4');h.textContent=t.team;av.appendChild(h);
     detailText(av,t.source_type+(t.report_day?' · '+t.report_day:'')+'. Listed statuses only; unlisted is not inferred healthy. No numeric injury delta.');
     const ul=document.createElement('ul');for(const pl of t.items){const li=document.createElement('li');li.textContent=pl.position+' '+pl.player+' - '+(pl.status||pl.status_text);ul.appendChild(li);}av.appendChild(ul);
     if(!t.items.length)detailText(av,'No player entries in this source snapshot. That is not proof of full availability.');
     if(t.source){const a=document.createElement('a');a.href=t.source;a.textContent='Availability source';a.target='_blank';a.rel='noopener noreferrer';av.appendChild(a);}
    }
    box.appendChild(av);const source=document.createElement('a');source.href='tools/cfb/current_inputs_20261016/README.md';source.textContent='Stats, weather and availability audit';box.appendChild(source);game.appendChild(box);
   }
   if(live?.state==='pre'&&live.injury_coverage){detailText(summary,'Availability: '+live.injury_coverage);}
   const hint=document.createElement('div');hint.className='cfb-card-hint';hint.textContent=g.book_frozen_pregame?'Frozen pregame · tap for quote and sources':'Tap for lines, weather and sources';summary.appendChild(hint);
   game.querySelectorAll('.bfoot table').forEach(table=>{const labels=[...table.querySelectorAll('th')].map(x=>x.textContent);table.querySelectorAll('tr').forEach(tr=>tr.querySelectorAll('td').forEach((td,k)=>td.dataset.label=labels[k]||''));});
  });
  const notes=[...wrap.querySelectorAll('.note-card')].map(n=>n.outerHTML).join('');
  host.innerHTML=`<div class="cfb-fresh">Week 7 final - 59/59 sealed games graded. Forward gate: no AP adoption (no-AP 40/59 winners, MAE 11.97; AP variant 38/59, MAE 12.16). Sealed predictions unchanged. Previous quote capture: ${doc.getElementById('updated').textContent}</div><div class="cfb-stats"><div><strong>${data.games.length}</strong><span>Games covered</span></div><div><strong>${data.games.filter(g=>fresh.events[g.event_id]?.state==='pre').length}</strong><span>Upcoming</span></div><div><strong>${data.games.length}</strong><span>Sealed forecasts</span></div><div><strong>Graded</strong><span>Week 7 forward test</span></div></div><div class="cfb-warning">Oct 16 pregame audit retained for context: stats 455/455 completed FBS-involving games (7 new Week7 finals, 3 repaired nonfinals); weather snapshots for all 52 then-remaining games; availability 64/104 official reports, 40/104 secondary-only. No adopted injury or weather adjustment.</div><div class="cfb-warning">Forward test complete: on the untouched Week 7 holdout the AP variant picked 38/59 winners vs the no-AP reference 40/59 (winner CI95 [-0.085, 0.000]) - no adoption; AP stays research-only and the no-AP spec is the reference for Week 8. Book comparison only, not picks.</div><div id="cfbParlay"></div><div class="cfb-toolbar"><input id="cfbSearch" aria-label="Search CFB teams" placeholder="Search teams..."><div class="cfb-filter"><button class="active" data-cfb-filter="all">All games</button><button data-cfb-filter="upcoming">Upcoming</button><button data-cfb-filter="frozen">Frozen</button><button data-cfb-filter="weather">Weather</button></div></div><div id="cfbCount" class="cfb-count"></div><div id="cfbGames"></div><p id="cfbEmpty" hidden>No games match. Try another team or filter.</p><details class="cfb-method"><summary>Model, sources and limits</summary>${notes}<p>${data.weather_context_note||''}</p></details>`;
  host.querySelector('#cfbGames').appendChild(board);
  try{
   const pr=await fetch('tools/cfb/parlay_20261017/parlay_candidates.json?ts='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null);
   const slot=host.querySelector('#cfbParlay');
   if(pr&&slot){
    const legRow=l=>'<div class="cfb-leg"><div class="bgrid"><span class="bg-lab">'+l.kickoff_ct+' CT</span><span class="bnum">'+l.leg+'</span></div><p class="muted">'+l.model+(l.context?' · '+l.context:'')+'</p></div>';
    const ticket=(t,title)=>'<div class="cfb-ticket"><h4>'+title+'</h4>'+t.legs.map(legRow).join('')+'<p class="cfb-price">$'+t.payout_at_captured_prices.stake+' returns $'+t.payout_at_captured_prices.total_return+' (about '+t.payout_at_captured_prices.approx_american+') at FanDuel IL prices captured 10:03-10:10 AM CT Oct 17 - TN not verified, confirm in app</p></div>';
    slot.innerHTML='<details class="cfb-parlay" open><summary><span>Model parlay research - Sat Oct 17</span><span class="cfb-parlay-head">3-leg $10 → $'+pr.three_leg_model_favorite.payout_at_captured_prices.total_return+' · 4-leg $10 → $'+pr.four_leg_long_shot.payout_at_captured_prices.total_return+' · research only, validation pending</span></summary>'+ticket(pr.three_leg_model_favorite,'3-leg - model favorite')+ticket(pr.four_leg_long_shot,'4-leg long shot')+'<p class="muted cfb-parlay-caveats">'+pr.caveats.join(' ')+'</p></details>';
   }
  }catch(e){}
  let mode='all';function filter(){const q=host.querySelector('#cfbSearch').value.toLowerCase();let n=0;games.forEach(g=>{const show=g.dataset.name.includes(q)&&(mode==='all'||mode==='upcoming'&&g.dataset.started==='false'||mode==='frozen'&&g.dataset.frozen==='true'||mode==='weather'&&g.dataset.wx==='true');g.hidden=!show;if(show)n++;});board.querySelectorAll('.day-label').forEach(label=>{let node=label.nextElementSibling,visible=false;while(node&&!node.classList.contains('day-label')){if(node.matches('details.game')&&!node.hidden)visible=true;node=node.nextElementSibling;}label.hidden=!visible;});host.querySelector('#cfbCount').textContent=`${n} games · WEEK 7 FINAL / BOOK IL`;host.querySelector('#cfbEmpty').hidden=n!==0;}
  host.querySelector('#cfbSearch').oninput=filter;host.querySelectorAll('[data-cfb-filter]').forEach(b=>b.onclick=()=>{mode=b.dataset.cfbFilter;host.querySelectorAll('[data-cfb-filter]').forEach(x=>x.classList.toggle('active',x===b));filter();});filter();
  window.inlineCfbData=data;cfbLoaded=true;
 }catch(e){host.innerHTML='<div class="cfb-warning">The board could not load. Refresh to try again. No numbers have been replaced.</div>';}
}
document.querySelector('[data-tab="cfb"]').addEventListener('click',loadInlineCfb);
