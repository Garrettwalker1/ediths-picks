#!/usr/bin/env python3
"""Grade immutable pregame Week 4 board against verified final scoreboard tracker."""
import json,math,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=json.loads((R/'tools/cfb/24-cfb_board_2026_week5_initial_v2_2.json').read_text());T=json.loads((R/'tools/cfb/29-cfb_week5_2026_tracker.json').read_text());assert T['coverage']['games']==T['coverage']['final']==T['coverage']['boxscores_collected']==59
F={g['event_id']:g for g in T['games']};rows=[]
for b in B['games']:
 assert b['timing']=='pregame',b['event_id']
 f=F[b['event_id']];assert f['completed'];actual=float(f['home_score'])-float(f['away_score']);pred=float(b['predicted_margin_home']);book=b.get('book_tn') or b.get('book_va');bm=-(book['home_spread']) if book and book.get('home_spread') is not None else None
 rows.append({'event_id':b['event_id'],'name':b['name'],'home':b['home'],'away':b['away'],'frozen_predicted_margin_home':pred,'actual_margin_home':actual,'absolute_error':round(abs(pred-actual),2),'winner_correct':(pred>0)==(actual>0) if pred and actual else None,'book_state':book.get('state') if book else None,'book_captured_at':book.get('captured_at') if book else None,'book_home_spread':book.get('home_spread') if book else None,'ats_result':('push' if actual==bm else 'win' if (actual>bm)==(pred>bm) else 'loss') if bm is not None and pred!=bm else None})
mae=statistics.mean(r['absolute_error'] for r in rows);rmse=math.sqrt(statistics.mean((r['frozen_predicted_margin_home']-r['actual_margin_home'])**2 for r in rows));w=sum(r['winner_correct'] is True for r in rows);n=sum(r['winner_correct'] is not None for r in rows)
from collections import Counter
ats=Counter(r['ats_result'] for r in rows if r['ats_result'])
out={'schema_version':'1.0.0','label':'MEASUREMENT ONLY - not picks. Week 5 frozen pregame numbers versus ESPN finals. Mixed-jurisdiction book line comparison is diagnostic, not closing-line performance.','graded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_board':'tools/cfb/24-cfb_board_2026_week5_initial_v2_2.json','source_results':'tools/cfb/29-cfb_week5_2026_tracker.json','coverage':{'scheduled':T['coverage']['games'],'final':T['coverage']['final'],'frozen_scored':len(rows),'unscored':len(B['errors']),'boxscores':T['coverage']['boxscores_collected']},'metrics':{'mae':round(mae,3),'rmse':round(rmse,3),'winner_correct':w,'winner_decidable':n,'ats_comparison':dict(ats)},'caveat':'Book quotes are per-game available pregame comparison from the frozen board; some are interim Illinois and others Tennessee, and quote time varies. Do not interpret ATS as TN closing or vetted bets. Games without book quotes and ties are omitted from ATS.','games':rows,'unscored':B['errors']}
assert len(rows)+len(B['errors'])==T['coverage']['games'];(R/'tools/cfb/29-cfb_week5_frozen_results.json').write_text(json.dumps(out,indent=1));print(out['coverage'],out['metrics'],Counter(r['book_state'] for r in rows))
