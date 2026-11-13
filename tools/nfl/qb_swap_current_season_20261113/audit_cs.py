import json
exec(open(__import__('os').path.dirname(__import__('os').path.abspath(__file__))+'/build_cs.py').read().split("# ---- current-season-only")[0])
a={}
raw=pd.concat([pd.read_csv(RAW+f'sp{y}.csv',usecols=['player_id','position','team','season','week','season_type','attempts','sacks_suffered','passing_epa']) for y in range(2020,2027)])
raw=raw[raw.season_type=='REG']; raw['db']=raw.attempts.fillna(0)+raw.sacks_suffered.fillna(0)
cand=raw[(raw.db>0)&raw.passing_epa.notna()]
a['reg_rows']=len(raw); a['passer_rows_db>0_epa_notna']=len(cand)
a['nonQB_position_rows']=int((cand.position!='QB').sum()); a['nonQB_dropback_share']=float(cand[cand.position!='QB'].db.sum()/cand.db.sum())
a['nonQB_by_position']=cand[cand.position!='QB'].position.value_counts().to_dict()
a['dup_player_season_week_team']=int(cand.duplicated(['player_id','season','week','team']).sum())
m=cand.merge(M,on=['season','week','team'],how='left')
a['merge_rows_before']=len(cand); a['merge_rows_after']=len(m); a['merge_unmatched']=int(m.game_id.isna().sum())
a['unmatched_team_codes']=sorted(set(m[m.game_id.isna()].team))[:20]
a['unmatched_dropbacks']=float(m[m.game_id.isna()].db.sum())
a['M_duplicate_keys']=int(M.duplicated(['season','week','team']).sum())
a['team_games_without_qb_rows']=int(len(M)-M.merge(m[['season','week','team']].drop_duplicates(),on=['season','week','team']).shape[0])
a['team_games_without_qb_rows_completed_only']=int(len(M[(M.game_id.isin(G[G.home_score.notna()].game_id))])-M[M.game_id.isin(G[G.home_score.notna()].game_id)].merge(m[['season','week','team']].drop_duplicates(),on=['season','week','team']).shape[0])
a['raw_sha256']={f:__import__('hashlib').sha256(open(RAW+f,'rb').read()).hexdigest() for f in sorted(__import__('os').listdir(RAW))}
json.dump(a,open(OUT+'audit_cs.json','w'),indent=1); print(json.dumps({k:v for k,v in a.items() if k!='raw_sha256'},indent=1))
