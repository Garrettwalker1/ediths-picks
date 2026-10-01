const want=/ - (Passing Yds|Passing TDs|Rushing Yds|Receiving Yds|Total Receptions|Rushing \+ Receiving Yds|Anytime Touchdown Scorer)$/;
const hs=[...document.querySelectorAll('[aria-expanded]')].filter(e=>want.test((e.innerText||'').split('\n')[0].trim())||/^(Most|Anytime|Player to Score|Any Time)/.test((e.innerText||'').split('\n')[0].trim()));
for(const h of hs){if(h.getAttribute('aria-expanded')==='false'){h.click();await new Promise(r=>setTimeout(r,700));}}
await new Promise(r=>setTimeout(r,1500));
const out=[document.body.innerText];

return {captured_at:new Date().toISOString(),n:hs.length,sections:out};
