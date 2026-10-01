#!/bin/bash
# usage: cap_w4.sh OUTDIR   (captures FanDuel IL PIT@CLE props tabs, read-only lease)
OUT=${1:-/tmp/w4cap}; mkdir -p $OUT
U=${W4_URL:-https://sportsbook.fanduel.com/football/nfl/pittsburgh-steelers-@-cleveland-browns-36104915}
HERE=$(dirname "$0")
r=$(tools cloud_browser_scheduler acquire --task-description 'FanDuel IL props read' --mode read --json); L=$(echo "$r"|jq -r .lease_id);T=$(echo "$r"|jq -r .tab_id)
for tab in passing-props receiving-props rushing-props td-scorer-props; do
 tools cloud_browser navigate --lease-id $L --tab-id $T --url "$U?tab=$tab" --wait-until load >/dev/null; sleep 6
 tools cloud_browser execute-js --lease-id $L --tab-id $T --script "$(cat $HERE/exp.js)" > $OUT/$tab.json
done
tools cloud_browser navigate --lease-id $L --tab-id $T --url "$U?tab=td-scorer-props" --wait-until load >/dev/null; sleep 5
tools cloud_browser execute-js --lease-id $L --tab-id $T --script "[...document.querySelectorAll('[role=button],div,span')].filter(e=>/^Show more\$/i.test((e.innerText||'').trim())&&e.children.length==0).slice(0,1).forEach(e=>e.click());await new Promise(r=>setTimeout(r,2500));return {captured_at:new Date().toISOString(),text:document.body.innerText}" > $OUT/td-all.json
tools cloud_browser_scheduler release --lease-id $L >/dev/null
