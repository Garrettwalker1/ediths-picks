import json, numpy as np, pandas as pd
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__)); RAW=HERE+'/raw/'; OUT=HERE+'/out/'; os.makedirs(OUT,exist_ok=True)
T=pd.DataFrame(json.load(open(RAW+'training_features.json')))
prov={p['game_id']:p for p in json.load(open(RAW+'feature_provenance.json'))}
fs=[c for c in T.columns if c.startswith('d_')]+['home_field']
T['date']=pd.to_datetime(T['date'])
# ---- QB game table
sp=pd.concat([pd.read_csv(RAW+f'sp{y}.csv',usecols=['player_id','player_display_name','position','team','season','week','season_type','attempts','sacks_suffered','passing_epa']) for y in range(2020,2027)])
sp=sp[(sp.season_type=='REG')]
sp['db']=sp.attempts.fillna(0)+sp.sacks_suffered.fillna(0)
q=sp[(sp.db>0)&sp.passing_epa.notna()].copy()
G=pd.read_csv(RAW+'games.csv'); G=G[(G.season>=2020)&(G.game_type=='REG')].copy()
G['date']=pd.to_datetime(G.gameday)
gm=G.set_index('game_id')
# map (season,week,team)->game_id
rows=[]
for r in G.itertuples():
    rows+= [(r.season,r.week,r.home_team,r.game_id,r.date),(r.season,r.week,r.away_team,r.game_id,r.date)]
M=pd.DataFrame(rows,columns=['season','week','team','game_id','date'])
q=q.merge(M,on=['season','week','team'],how='left'); q=q[q.game_id.notna()]
q['x']=q.passing_epa/q.db

# ---- current-season-only quality; k per season from PRIOR seasons' within-season data only (variance components, no player stats carried)
def kfor(season):
    d=q[q.season<season]
    if d.season.nunique()<1: return None
    s2n=0;dn=0;recs=[]
    for (ss,pid),x in d.groupby(['season','player_id']):
        n=x.db.sum(); e=x.passing_epa.sum()
        if len(x)>=2:
            xb=e/n; s2n+=(x.db*(x.x-xb)**2).sum(); dn+=len(x)-1
        if n>=200: recs.append((n,e/n))
    s2=s2n/dn; n=np.array([r[0] for r in recs]); m=np.array([r[1] for r in recs]); mb=np.average(m,weights=n)
    tau2=np.average((m-mb)**2,weights=n)-np.mean(s2/n)
    return s2/tau2,s2,tau2
KS={s:kfor(s) for s in range(2021,2027)}
print({s:[round(float(v),3) for v in k] for s,k in KS.items()})
q=q.sort_values('date')
def Qcs(pid,cut,season):
    d=q[(q.season==season)&(q.date<cut)]
    mu=d.passing_epa.sum()/d.db.sum()
    p=d[d.player_id==pid]; n=p.db.sum(); e=p.passing_epa.sum()
    k=KS[season][0]
    return (e+k*mu)/(n+k), n, n/(n+k)
cache={}
def Q(pid,cut,season=None):
    season=season or pd.Timestamp(cut).year if False else season
    key=(pid,cut,season)
    if key not in cache: cache[key]=Qcs(pid,cut,season)
    return cache[key]
qg={}
for r in q.itertuples(): qg.setdefault((r.game_id,r.team),[]).append((r.player_id,r.db))
def embedded(hist,team,cut,SEASON):
    num=den=0
    for gid in hist:
        for pid,db in qg.get((gid,team),[]):
            num+=db*Q(pid,cut,SEASON)[0]; den+=db
    return num/den if den else np.nan
def lastgame_starter(team,cut,season):
    gg=G[(G.season==season)&(G.date<cut)&((G.home_team==team)|(G.away_team==team))].sort_values('date')
    if not len(gg): return None
    r=gg.iloc[-1]; return r.home_qb_id if r.home_team==team else r.away_qb_id
out=[]
for r in T.itertuples():
    if r.season<2021: continue
    gid=r.game_id; cut=r.date; p=prov[gid]; ro=gm.loc[gid]
    rec=dict(game_id=gid,season=r.season,date=cut,margin=r.margin)
    for side,team,hist,sid in (('h',r.home,p['home_history'],ro.home_qb_id),('a',r.away,p['away_history'],ro.away_qb_id)):
        emb=embedded(hist,team,cut,r.season)
        qs,ns,_w=Q(sid,cut,r.season) if isinstance(sid,str) else (np.nan,0,0)
        lg=lastgame_starter(team,cut,r.season)
        ql=Q(lg,cut,r.season)[0] if isinstance(lg,str) else np.nan
        # dropback leader (actual workload) for label check
        lead=max(qg.get((gid,team),[(None,0)]),key=lambda t:t[1])[0]
        rec.update({f'emb_{side}':emb,f'q_open_{side}':qs,f'n_open_{side}':ns,f'q_last_{side}':ql,f'open_is_leader_{side}':(lead==sid)})
    out.append(rec)
R=pd.DataFrame(out)
R['d_open']=(R.q_open_h-R.emb_h)-(R.q_open_a-R.emb_a)
R['d_last']=(R.q_last_h-R.emb_h)-(R.q_last_a-R.emb_a)
# ---- chronological core residuals: refit core on rows strictly earlier date
X=T[fs].to_numpy(); y=T.margin.to_numpy(); dates=T.date.values
pred=np.full(len(T),np.nan)
for dt in np.unique(dates):
    tr=dates<dt
    if tr.sum()<200: continue
    Xm=np.vstack([X[tr],-X[tr]]); ym=np.r_[y[tr],-y[tr]]
    sd=Xm.std(0); sd[sd==0]=1; Z=Xm/sd
    w=np.linalg.solve(Z.T@Z+10*np.eye(Z.shape[1]),Z.T@ym)
    idx=dates==dt; pred[idx]=(X[idx]/sd)@w
R['core']=pred[(T.season.values>=2021)]; R['resid']=R.margin-R.core
R.to_csv(OUT+'qbswap_cs_rows.csv',index=False)
json.dump({str(a):b for a,b in KS.items()},open(OUT+'eb_cs_params.json','w'))
print(R[['d_open','d_last']].describe()); print('open==dropback leader share',R[['open_is_leader_h','open_is_leader_a']].mean().to_dict())
print('rows with core',R.core.notna().sum())

Xm=np.vstack([X,-X]); ym=np.r_[y,-y]; sd=Xm.std(0); w=np.linalg.solve((Xm/sd).T@(Xm/sd)+10*np.eye(16),(Xm/sd).T@ym)
meta=json.load(open(RAW+'current_forecasts.json'))['metadata']
print('core coef reconstruction max abs diff',np.abs(w-np.array(meta['coefficients'])).max())
