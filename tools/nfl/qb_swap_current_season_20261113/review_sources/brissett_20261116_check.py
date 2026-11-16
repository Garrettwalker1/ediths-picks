import pathlib,requests,pandas as pd,json,hashlib,numpy as np
P=pathlib.Path('/tmp/edith/tools/nfl/qb_swap_current_season_20261113');W=pathlib.Path('/tmp/deep-research/brissett')
u='https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv';r=requests.get(u);r.raise_for_status();(W/'fresh_sp2026.csv').write_bytes(r.content)
s=pd.read_csv(W/'fresh_sp2026.csv');o=pd.read_csv(P/'raw/sp2026.csv');print(s[s.player_display_name.str.contains('Brissett',na=False)][['player_id','team','week','attempts','completions','passing_yards','passing_tds','passing_interceptions','sacks_suffered','passing_epa']].to_string(index=False))
# Execute definitions only, no historical rebuild or output edits.
ns={'__file__':str(P/'build_cs.py')};exec((P/'build_cs.py').read_text().split('out=[]')[0],ns)
C=pd.Timestamp('2026-11-13');S=2026;G=ns['G'];Q=ns['Q'];q=ns['q'];k,s2,tau=ns['KS'][2026];pid=o[o.player_display_name.str.contains('Brissett',na=False)].player_id.unique();assert len(pid)==1;pid=pid[0]
cols=['player_id','team','week','attempts','sacks_suffered','passing_epa'];a=o[(o.player_id==pid)&(o.season_type=='REG')][cols].reset_index(drop=True);b=s[(s.player_id==pid)&(s.season_type=='REG')][cols].reset_index(drop=True);pd.testing.assert_frame_equal(a,b)
h=list(G[(G.season==S)&(G.date<C)&((G.home_team=='BAL')|(G.away_team=='BAL'))&G.home_score.notna()].game_id)
emb=ns['embedded'](h,'BAL',C,S);quality,n,w=Q(pid,C,S)
R=pd.read_csv(P/'out/qbswap_cs_rows.csv',parse_dates=['date']);R=R[R.core.notna()&R.d_open.notna()&R.d_last.notna()&(R.date<C)]
beta=float((R.d_open*R.resid).sum()/(R.d_open**2).sum());bs=[float(((t.d_open*t.resid).sum())/(t.d_open**2).sum()) for t in (R.sample(len(R),replace=True,random_state=i) for i in range(2000))];lo,hi=np.percentile(bs,[2.5,97.5]);delta=quality-emb;swing=beta*delta
hist=q[q.game_id.isin(h)&(q.team=='BAL')].groupby(['player_id','player_display_name']).agg(db=('db','sum'),epa=('passing_epa','sum')).reset_index().to_dict('records')
core=json.load(open(P.parent/'current_season_20261113/current_forecasts.json'));g=next(g for g in core['games'] if g['game_id']=='2026_10_LAC_BAL');print(g)
out=dict(player_id=pid,sample_rows=len(a),season_dropbacks=float(n),data_weight=float(w),quality=float(quality),embedded=float(emb),k=k,beta=beta,beta_ci95=[lo,hi],delta=float(delta),swing=float(swing),swing_coef_only_ci95=sorted([lo*delta,hi*delta]),baseline_raw=g['raw_margin_home'],scenario_raw=g['raw_margin_home']+swing,scenario_display=round((g['raw_margin_home']+swing)*2)/2,embedded_history=hist,core_history_game_ids=h,source_url=u,fresh_stats_sha256=hashlib.sha256(r.content).hexdigest(),fresh_Brissett_rows_equal_original=True)
(W/'calculation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
