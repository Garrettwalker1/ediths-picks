// Run with `tools cloud_browser execute-js` on a fantasy.espn.com page in Garrett's logged-in config.
// Replace __IDS__ with the JSON array of ESPN player ids for every rostered player (ESPN rosters + Sleeper espn_id / name match).
// Output: JSON [{id,name,inj,lastNewsDate,detail}] for tools/generate_fantasy.py --injury-status. Read-only; one status call plus one news call per flagged player.
const ids=__IDS__;
const f=JSON.stringify({players:{filterIds:{value:ids},filterStatsForTopScoringPeriodIds:{value:2}}});
const r=await fetch('https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026/segments/0/leagues/1242450525?view=kona_player_info',{credentials:'include',headers:{'x-fantasy-filter':f,'x-fantasy-platform':'kona-PROD','x-fantasy-source':'kona'}});
if(!r.ok) throw new Error('ESPN status '+r.status);
const d=await r.json(); const want=new Set(ids);
const rows=(d.players||[]).filter(x=>want.has(x.id)).map(x=>({id:x.id,name:x.player.fullName,inj:x.player.injuryStatus||null,lastNewsDate:x.player.lastNewsDate||null,detail:null}));
for(const x of rows){ if(!x.inj||x.inj==='ACTIVE') continue;
  try{const n=await (await fetch('https://site.api.espn.com/apis/fantasy/v2/games/ffl/news/players?playerId='+x.id+'&limit=1')).json();
    const t=(((n.feed||[])[0]||{}).story||'').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim(); const last=x.name.split(' ').filter(w=>!/^(Jr\.|Sr\.|II|III|IV)$/.test(w)).pop();
    if(t && t.slice(0,200).includes(last)){ const m=t.slice(0,420).match(/^(.*[a-z0-9\)"][.!?])(?=\s|$)/); x.detail=m?m[1]:null; }
  }catch(e){} }
return JSON.stringify(rows);
