"""STRICT-definition absence rebuild (authorized minimal spec, 2026-11-13).
Single self-contained script: panel -> game differentials -> pooled fit. No other steps exist.

EVENT DEFINITION (strict):
- injury absence = established player has NO stat row for the team-game AND the nflverse weekly
  injury report shows report_status == 'Out' for THAT SAME season/team/week/player.
  No Doubtful. No carry-forward. No future-team information used anywhere (no departure class).
- undesignated absence = established player with no stat row and no same-week Out designation.
  Reason UNKNOWN (rest/bench/zero-touch-in-old-era/incomplete 2026 file). Reported, never labeled injury.
- 2025-26 files: zero-volume row presence counts as ACTIVE (observed). 2020-24 files are
  stat-recorder-only: zero-touch games are indistinguishable from absence (disclosed limit;
  the same-week Out designation requirement bounds false injury events to designated players).
- established: >=2 prior appearances AND >=2% of team trailing volume (attempts+carries+receptions),
  strictly pre-game. Histories update only after the game's features are built.
- bye weeks: no team-game row exists, structurally excluded.

SPEC (exact): one row per GAME (home perspective). margin ~ const + home_field +
d_record_strength + d_schedule_strength + d_opponent_score_rating + season indicators
(NOT team-season fixed effects - earlier wording corrected) + d_injOut_SKILL + d_injOut_QB(control)
+ d_undes_SKILL + d_undes_QB(control). Two-way cluster-robust SEs (Cameron-Gelbach-Miller:
home-team bread + away-team bread - home-x-away pair bread).
Rating controls provenance: training_features.json, whose metadata states features are computed
from past-only same-season games with min 3 earlier games per team (pre-game by construction).
Abbreviations: nflverse files use consistent abbreviations across stats/injuries/games
(WAS, LA, JAX, ARI in all three; verified in-script); no normalization applied or needed.
OBSERVATIONAL ASSOCIATION. Not causal. Not player-specific. No current-week application here.
"""
import glob, json
import pandas as pd, numpy as np

VOL=['attempts','carries','receptions']
frames=[]
for y in range(2020,2025):
    frames.append(pd.read_csv(f'/tmp/inj/nflhist/player_stats_{y}.csv',low_memory=False).rename(columns={'recent_team':'team','interceptions':'passing_interceptions'}))
frames.append(pd.read_csv('/tmp/inj/nflhist/stats_player_week_2025.csv',low_memory=False))
frames.append(pd.read_csv('/tmp/inj/nfl/player_stats_2026.csv',low_memory=False))
D=pd.concat(frames,ignore_index=True); D=D[D.season_type=='REG']
for c in VOL: D[c]=pd.to_numeric(D[c],errors='coerce').fillna(0)
D['vol']=D[VOL].sum(axis=1)
D['pos']=D['position'].where(D['position'].isin(['QB','RB','WR','TE']),'OTHER')

games=pd.read_csv('/tmp/inj/nfl/games.csv',low_memory=False)
games=games[(games.game_type=='REG')&(games.season>=2020)][['game_id','season','week','home_team','away_team']]
# abbreviation consistency check (explicit, no silent normalization)
t_stats=set(D.team.dropna().unique()); t_games=set(games.home_team.unique())|set(games.away_team.unique())
print('teams only in stats:',t_stats-t_games,'| only in games:',t_games-t_stats)

# attach game_id to old files (season+week+team join)
key=games.melt(id_vars=['game_id','season','week'],value_vars=['home_team','away_team'],value_name='team')[['season','week','team','game_id']].rename(columns={'game_id':'game_id_joined'})
D=D.merge(key,on=['season','week','team'],how='left')
D['game_id']=D['game_id'].fillna(D['game_id_joined'])
assert D.game_id.notna().all(), 'unjoined stat rows exist'
assert (D[D.season<=2024].game_id==D[D.season<=2024].game_id_joined).all()
assert (D[D.season>=2025].game_id==D[D.season>=2025].game_id_joined).all(), 'new-file game_id disagrees with join'

inj=pd.concat([pd.read_csv(f,low_memory=False) for f in sorted(glob.glob('/tmp/inj/nfl/23*-injuries_20*.csv'))+['/tmp/inj/nfl/injuries_2026.csv']],ignore_index=True)
if 'season_type' not in inj.columns: inj['season_type']=pd.NA
inj['season_type']=inj['season_type'].fillna(inj['game_type']); inj=inj[inj.season_type=='REG']
inj['gsis_id']=inj['gsis_id'].astype(str)
t_inj=set(inj.team.dropna().unique())
print('teams only in injuries:',t_inj-t_games,'| only in games:',t_games-t_inj)
OUTKEY={(int(r.season),str(r.team),int(r.week),str(r.gsis_id)) for r in inj[inj.report_status=='Out'].itertuples()}
print('same-week Out designation keys:',len(OUTKEY))

tf={r['game_id']:r for r in json.load(open('/tmp/inj/nfl/training_features.json'))}

rows=[]  # team-game level
for (season,tm),d in D.groupby(['season','team']):
    tg=games[(games.season==season)&((games.home_team==tm)|(games.away_team==tm))].sort_values('week')
    piv=d.pivot_table(index='week',columns='player_id',values='vol',aggfunc='sum').fillna(0)
    meta=d.groupby('player_id').agg(pos=('pos','last'))
    hist_vol={}; hist_app={}
    for g in tg.itertuples():
        w=g.week
        if w not in piv.index: continue
        tot=sum(hist_vol.values())
        estab={pid:v for pid,v in hist_vol.items() if hist_app.get(pid,0)>=2 and tot>0 and v/tot>=0.02}
        row=piv.loc[w]
        present=set(row[row>0].index)
        if season>=2025: present=set(d[d.week==w].player_id)  # zero-touch rows = active (observed)
        rec={'game_id':g.game_id,'season':season,'team':tm,'home':int(tm==g.home_team),
             'injOut_QB':0.0,'injOut_SKILL':0.0,'undes_QB':0.0,'undes_SKILL':0.0,
             'n_injOut_skill_events':0,'n_undes_skill_events':0}
        for pid,v in estab.items():
            if pid in present: continue
            pos=meta.pos.get(pid,'OTHER')
            if pos=='OTHER': continue
            share=v/tot
            out=(season,tm,int(w),pid) in OUTKEY
            grp='QB' if pos=='QB' else 'SKILL'
            rec[('injOut_' if out else 'undes_')+grp]+=share
            if grp=='SKILL': rec['n_injOut_skill_events' if out else 'n_undes_skill_events']+=1
        for pid in piv.columns:
            if row[pid]>0 or (season>=2025 and pid in present):
                hist_vol[pid]=hist_vol.get(pid,0)+row[pid]; hist_app[pid]=hist_app.get(pid,0)+1
        rows.append(rec)

T=pd.DataFrame(rows)
T=T.merge(pd.DataFrame([{'game_id':k,'margin':v['margin'],'home_field':v['home_field'],
    'd_record_strength':v['d_record_strength'],'d_schedule_strength':v['d_schedule_strength'],
    'd_opponent_score_rating':v.get('d_opponent_score_rating',0.0)} for k,v in tf.items()]),on='game_id',how='inner')

# collapse to game-level differentials (home - away); the previously missing step, now in-script
home=T[T.home==1].set_index('game_id'); away=T[T.home==0].set_index('game_id')
common=home.index.intersection(away.index)
G=pd.DataFrame(index=common)
for c in ['margin','home_field','d_record_strength','d_schedule_strength','d_opponent_score_rating']:
    G[c]=home.loc[common,c]
G['season']=home.loc[common,'season']; G['home_team']=home.loc[common,'team']; G['away_team']=away.loc[common,'team']
for c in ['injOut_QB','injOut_SKILL','undes_QB','undes_SKILL','n_injOut_skill_events','n_undes_skill_events']:
    G['d_'+c]=home.loc[common,c].values-away.loc[common,c].values
    G['s_'+c]=home.loc[common,c].values+away.loc[common,c].values  # totals for counting
G.to_csv('/tmp/inj/overlay/strict_nfl_game_panel.csv',index=True)

counts={'games':int(len(G)),
 'injOut_skill_events':int(T.n_injOut_skill_events.sum()),
 'undes_skill_events':int(T.n_undes_skill_events.sum()),
 'injOut_skill_share_total':float(T.injOut_SKILL.sum()),
 'undes_skill_share_total':float(T.undes_SKILL.sum()),
 'injOut_QB_share_total':float(T.injOut_QB.sum()),
 'games_with_injOut_skill_share':int((G.s_injOut_SKILL>0).sum())}
json.dump(counts,open('/tmp/inj/overlay/strict_nfl_counts.json','w'),indent=1)
print(json.dumps(counts,indent=1))

y=G.margin.values
Xcols=['home_field','d_record_strength','d_schedule_strength','d_opponent_score_rating',
 'd_injOut_SKILL','d_injOut_QB','d_undes_SKILL','d_undes_QB']
sdum=pd.get_dummies(G.season,drop_first=True).astype(float)
X=np.hstack([np.ones((len(G),1)),G[Xcols].values,sdum.values])
names=['const']+Xcols+['season_'+str(c) for c in sdum.columns]
n,k=X.shape; XtX_inv=np.linalg.inv(X.T@X); b=XtX_inv@X.T@y; u=y-X@b
def bread(cl):
    B=np.zeros((k,k))
    for _,idx in G.groupby(cl).indices.items():
        Xc=X[list(idx)]; uc=u[list(idx)]; B+=Xc.T@np.outer(uc,uc)@Xc
    return B
pair=G.home_team+'@'+G.away_team
B=bread('home_team')+bread('away_team')-bread(pair)  # CGM two-way with intersection correction
nc=G.home_team.nunique()
V=XtX_inv@B@XtX_inv*(nc/(nc-1))*((n-1)/(n-k))
se=np.sqrt(np.maximum(np.diag(V),0))
out=pd.DataFrame({'term':names,'coef':b.round(4),'se':se.round(4),'t':(b/se).round(2)})
out.to_csv('/tmp/inj/overlay/strict_nfl_coefs.csv',index=False)
print(out.to_string(index=False))
print('R2',round(1-u@u/((y-y.mean())@(y-y.mean())),4),'n',n)
