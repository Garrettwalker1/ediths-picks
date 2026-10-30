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
  const children=[...log.children],start=children.findIndex(n=>n.tagName==='H2'&&n.textContent.includes('Week 8 NFL book references'));
  if(start>=0){const board=document.createElement('section');board.id='currentNflBoard';board.className='current-board';const flag=document.createElement('div');flag.className='section-status';flag.textContent='WEEK 8 BOARD · RESEARCH, NOT A PROVEN BETTING EDGE';board.append(flag);
   for(let i=start;i<children.length;i++){const n=children[i];if(i>start&&n.tagName==='H2')break;board.append(n);}
   model.insertBefore(board,summary);
   const h=board.querySelector('h2');if(h)h.textContent='Model vs book';
   const sub=model.querySelector(':scope > .sub');if(sub)sub.textContent='The current board comes first. Model limits stay beside the numbers; performance tests and earlier learning records follow below.';
   const research=document.createElement('h2');research.className='research-divider';research.textContent='Performance and learning record';summary.before(research);
  }
 }
 const states={model:['Week 8 board','Scores-only baseline · injury experiment unproven'],tracker:['Your results','Actual ticket accounting · dollars and historical units'],fantasy:['Fantasy rosters','Status coverage varies · no designation is not clearance'],players:['Older generic snapshot','Usage through Week6 · Oct20 build · not Week8 forecasts'],touchdowns:['TD research','Baseline and trial are separate · no proven betting edge'],cfb:['CFB board','Research status and source times remain with each game'],cfbtop25:['CFB ratings','Model ratings · not a poll or betting recommendation']};
 const status=document.createElement('div');status.className='view-status';status.setAttribute('aria-live','polite');tabs.after(status);
 function update(){const b=tabs.querySelector('button.active'),key=b?.dataset.tab||'model',a=states[key]||states.model;status.replaceChildren();const label=document.createElement('b');label.textContent=a[0];const note=document.createElement('span');note.textContent=a[1];status.append(label,note);tabs.querySelectorAll('button').forEach(n=>n.setAttribute('aria-current',n===b?'page':'false'));}
 tabs.addEventListener('click',()=>setTimeout(update,0));update();
 const top=document.createElement('button');top.className='back-top';top.textContent='Back to top ↑';top.setAttribute('aria-label','Back to dashboard navigation');top.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));document.body.append(top);const visibility=()=>{top.hidden=window.scrollY<700};window.addEventListener('scroll',visibility,{passive:true});visibility();
};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);else ready();
})();
