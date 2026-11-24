/* Presentation-only enhancements. Model values, data files and rankings are unchanged. */
(()=>{
const ready=()=>{
 const main=document.querySelector('main'),tabs=document.querySelector('.tabs');if(!main||!tabs)return;
 const tdnav=tabs.querySelector('[data-tab=touchdowns]');if(tdnav){tdnav.textContent='TD research';tdnav.setAttribute('aria-label','Touchdown research');}
 tabs.setAttribute('aria-label','Dashboard sections');tabs.setAttribute('role','navigation');
 const title=main.querySelector('h1');if(title){const p=document.createElement('p');p.className='site-subtitle';p.textContent='Football models, player research and your results.';title.after(p);}
 // Lift the existing current board out of the old learning-log wrapper.
 const log=document.getElementById('gameLearning'),model=document.getElementById('modeltab'),summary=document.getElementById('summary');
 if(log&&model&&summary){
  const children=[...log.children],start=children.findIndex(n=>n.tagName==='H2'&&n.textContent.includes('Week 10 NFL book references'));
  if(start>=0){const board=document.createElement('section');board.id='currentNflBoard';board.className='current-board';const flag=document.createElement('div');flag.className='section-status';flag.textContent='HISTORICAL WEEK 10 BOARD · NOT A PROVEN BETTING EDGE';board.append(flag);
   for(let i=start;i<children.length;i++){const n=children[i];if(i>start&&n.tagName==='H2')break;board.append(n);}
   model.insertBefore(board,summary);
   const h=board.querySelector('h2');if(h)h.textContent='Model vs book';
   const sub=model.querySelector(':scope > .sub');if(sub)sub.textContent='The current board comes first. Model limits stay beside the numbers; performance tests and earlier learning records follow below.';
   const research=document.createElement('h2');research.className='research-divider';research.textContent='Performance and learning record';summary.before(research);
  }
 }
 // Current NFL content first; historical material stays accessible in one labeled archive.
 if(model&&log){
  const board=document.createElement('section');board.id='nflQuickBoard';board.className='nfl-quick-board';
  const nav=document.createElement('nav');nav.className='nfl-section-nav';nav.setAttribute('aria-label','NFL sections');
  for(const [label,id]of [['Predictions','nflPredictions'],['Rankings','nflRankings'],['Player lines','nflPlayerLines'],['Record & limits','nflArchive']]){const a=document.createElement('a');a.href='#'+id;a.textContent=label;nav.append(a)}board.append(nav);
  const children=[...log.children],heading=children.findIndex(n=>n.tagName==='H2'&&n.textContent==='Current predictions'),current=document.getElementById('nflCurrentSeason'),eff=document.getElementById('nflEfficiency'),players=document.getElementById('fanduelPlayerComparisons');
  if(heading>=0&&current&&eff&&players){
   const predictions=document.createElement('section');predictions.id='nflPredictions';
   for(let n=children[heading-1];n;){const next=n.nextElementSibling;if(n===eff){n=next;continue}if(n.tagName==='DETAILS'){n=next;continue}predictions.append(n);if(n===current)break;n=next}board.append(predictions);
   const ranks=document.createElement('details');ranks.id='nflRankings';ranks.className='nfl-fold';const rs=document.createElement('summary');rs.textContent='Offense & defense rankings · 32 teams';ranks.append(rs,eff);board.append(ranks);
   const playerSection=document.createElement('section');playerSection.id='nflPlayerLines';const intro=players.previousElementSibling;if(intro?.tagName==='P')intro.textContent='Dated Illinois book snapshots beside separate model baselines. Started games retain their original pregame quotes; current source times, frozen status, identity gaps and category coverage are shown below. Not Tennessee availability or a verified betting edge.';let n=players.previousElementSibling?.previousElementSibling;while(n){const next=n.nextElementSibling;playerSection.append(n);if(n===players)break;n=next}board.append(playerSection);
   const archive=document.createElement('details');archive.id='nflArchive';archive.className='nfl-fold';const as=document.createElement('summary');as.textContent='Historical records, backtests, source notes & model limits';archive.append(as);for(const n of [...model.children])archive.append(n);model.append(board,archive);
   const setNavOffset=()=>{nav.style.top=Math.ceil(tabs.getBoundingClientRect().height)+'px';document.documentElement.style.setProperty('--nfl-anchor-offset',(Math.ceil(tabs.getBoundingClientRect().height)+70)+'px')};setNavOffset();new ResizeObserver(setNavOffset).observe(tabs);nav.addEventListener('click',e=>{const a=e.target.closest('a');if(!a)return;const target=document.querySelector(a.getAttribute('href'));if(target?.tagName==='DETAILS')target.open=true;});
  }
 }
 const states={cbb:['College hoops','56 experimental forecasts · no validation yet'],model:['Week 12 board','Current-season production · partial conditional QB input, not full injury coverage'],tracker:['Your results','Actual ticket accounting · dollars and historical units'],fantasy:['Fantasy rosters','Status coverage varies · no designation is not clearance'],players:['Week12 generic baselines','Inputs through Week11 · no injury/workload adjustment'],touchdowns:['TD research','Baseline and trial are separate · no proven betting edge'],cfb:['CFB board','Research status and source times remain with each game'],cfbtop25:['CFB ratings','Model ratings · not a poll or betting recommendation']};
 const status=document.createElement('div');status.className='view-status';status.setAttribute('aria-live','polite');tabs.after(status);
 function update(){const b=tabs.querySelector('button.active'),key=b?.dataset.tab||'model',a=states[key]||states.model;status.replaceChildren();const label=document.createElement('b');label.textContent=a[0];label.style.marginRight='0.5em';const note=document.createElement('span');note.textContent=a[1];status.append(label,note);tabs.querySelectorAll('button').forEach(n=>n.setAttribute('aria-current',n===b?'page':'false'));}
 tabs.addEventListener('click',()=>setTimeout(update,0));update();
 const top=document.createElement('button');top.className='back-top';top.textContent='Back to top ↑';top.setAttribute('aria-label','Back to dashboard navigation');top.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));document.body.append(top);const visibility=()=>{top.hidden=window.scrollY<700};window.addEventListener('scroll',visibility,{passive:true});visibility();
};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);else ready();
})();
