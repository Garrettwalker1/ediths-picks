"""Limited observational same-week Out skill component. No healthy-roster claim."""
import datetime, hashlib, json, pathlib, math
import pandas as pd
P=pathlib.Path(__file__).resolve().parent
R=P.parents[2]
core_path=R/'tools/nfl/current_season_20261113/current_forecasts.json'
stats_path=core_path.parent/'sources/player_stats_2026.csv'
core=json.loads(core_path.read_text());initial=json.loads((P/'review_sources/current_bundle.json').read_text())
coef=pd.read_csv(P/'review_sources/residual_coefs.csv').set_index('term').loc['d_injOut_SKILL']
b,se=float(coef.coef),float(coef.se)
assert b==-7.08 and se==5.2005
D=pd.read_csv(stats_path,low_memory=False);D=D[(D.season==2026)&(D.season_type=='REG')]
G=pd.read_csv(core_path.parent/'sources/games.csv',low_memory=False)
prior=G[(G.season==2026)&(G.game_type=='REG')&(G.gameday<'2026-11-13')&G.home_score.notna()&G.away_score.notna()]
keys=set(prior.game_id);D=D[D.game_id.isin(keys)]
assert not D.duplicated(['team','player_id','week']).any()
D['volume']=D[['attempts','carries','receptions']].fillna(0).sum(axis=1)
by={g['game_id']:g for g in core['games']};games=[]
for gid,source in initial['verified_applied'].items():
 if not source['included'] or gid=='2026_10_MIN_GB':continue
 g=by[gid];hs=0.;aws=0.;included=[]
 for p in source['included']:
  team=D[D.team==p['team']];rows=team[team.player_id==p['gsis']]
  assert len(rows)>=2 and set(rows.position)=={p['pos']} and set(rows.player_display_name)=={p['name']}
  vol=float(rows.volume.sum());total=float(team.volume.sum());share=vol/total;assert share>=.02
  if p['team']==g['home_abbr']:hs+=share
  elif p['team']==g['away_abbr']:aws+=share
  else:raise ValueError('team mismatch')
  included.append(dict(p,prior_appearances=len(rows),player_volume=vol,team_volume=total,trailing_share=share,status='Out'))
 d=hs-aws;delta=b*d;raw=g['raw_margin_home'];corrected=raw+delta;width=1.96*se*abs(d)
 games.append(dict(game_id=gid,event_id=g['event_id'],home=g['home_abbr'],away=g['away_abbr'],kickoff=g['date'],raw_baseline_home_margin=raw,baseline_display_margin_home=g['display_margin_home'],home_out_share=hs,away_out_share=aws,d_share=d,delta_home_margin=delta,corrected_home_margin=corrected,display_margin_home=math.copysign(math.floor(abs(corrected)*2+.5)/2,corrected),coefficient_only_delta_band=[delta-width,delta+width],coefficient_only_corrected_home_band=[corrected-width,corrected+width],included=included))
out=dict(generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_checked_at='2026-11-13T21:58:30Z',contract=dict(b=b,coefficient_se=se,deployment_precision='Reviewed four-decimal CSV precision chosen explicitly; shares/baselines/deltas not rounded',formula='core home margin + b * (home_out_share - away_out_share)',scope='Experimental observational same-week explicitly Out established RB/WR/TE only; >=2 prior stat-row appearances, >=2% trailing team attempts+carries+receptions share; strictly pregame same-season team history',fit='2021-26 chronological core-refit residuals n=1208; mixed realized-history reference, not healthy baseline',weak_signal='Coefficient-only 95% interval includes zero. Every displayed correction is consistent with zero effect. Not causal or proof of improved accuracy.',uncertainty='Bands are coefficient-only, not predictive intervals; exclude status, role, replacement and confounding uncertainty.',exclusions='IR/reserve-only, pending/unknown, Doubtful/Questionable, departures, unestablished players, QB, OL and defense are outside scope, not zero actual effect. No QB-scenario stacking.',core_sha256=hashlib.sha256(core_path.read_bytes()).hexdigest(),stats_sha256=hashlib.sha256(stats_path.read_bytes()).hexdigest()),games=games,withheld=[dict(game_id='2026_10_MIN_GB',event_id=by['2026_10_MIN_GB']['event_id'],reason='Whole skill scenario withheld: Vikings opponent table lists Josh Jacobs Out, but GB owning report has Friday blank / Game Status UNSPECIFIED. Known possible cancellation with Hockenson. Existing separate QB conditional unchanged.',sources=['https://www.vikings.com/news/packers-injury-report-week-10-2026-nfl-season','https://www.packers.com/team/injury-report/']),dict(game_id='2026_10_SF_DAL',event_id=by['2026_10_SF_DAL']['event_id'],reason='Formal same-week owning-source Out designation not established for Ferguson/Goodson; no zero-effect scenario published.')])
(P/'injury_overlay.json').write_text(json.dumps(out,indent=2)+'\n')
for g in games:print(g['game_id'],g['raw_baseline_home_margin'],g['corrected_home_margin'],g['display_margin_home'],g['coefficient_only_corrected_home_band'])
