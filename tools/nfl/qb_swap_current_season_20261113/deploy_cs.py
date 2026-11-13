import json,os
exec(open(os.path.dirname(os.path.abspath(__file__))+'/build_cs.py').read().split("out=[]")[0])
ROLES=json.load(open(HERE+'/roles_input.json'))
import argparse
args=argparse.ArgumentParser(); args.add_argument('--cutoff',required=True); args.add_argument('--season',required=True,type=int); opts=args.parse_args()
C=pd.Timestamp(opts.cutoff); S=opts.season
R=pd.read_csv(OUT+'qbswap_cs_rows.csv',parse_dates=['date'])
R=R[R.core.notna()&R.d_open.notna()&R.d_last.notna()&(R.date<C)].sort_values('date').reset_index(drop=True)
beta=float((R.d_open*R.resid).sum()/(R.d_open**2).sum())
bs=[float(((t.d_open*t.resid).sum())/((t.d_open**2).sum())) for t in (R.sample(len(R),replace=True,random_state=i) for i in range(2000))]
lo,hi=[float(x) for x in np.percentile(bs,[2.5,97.5])]
k,s2,tau2=KS[S]
names=dict(zip(sp.player_id,sp.player_display_name))
def side(t):
    r=ROLES.get(t)
    if not r: return dict(team=t,status='unknown_no_confirmed_change_not_verified',swing_pts=None)
    pid=r['player_id']
    assert names.get(pid)==r['starter'], 'stable player ID/name mismatch'
    assert S==C.year, 'season/cutoff mismatch'
    h=list(G[(G.season==S)&(G.date<C)&((G.home_team==t)|(G.away_team==t))&G.home_score.notna()].game_id)
    emb=embedded(h,t,C,S); qv,n,w=Q(pid,C,S); d=qv-emb
    post_sd=float((1/tau2+n/s2)**-0.5)
    embq=sorted({(names.get(p,p),int(dd)) for g in h for p,dd in qg.get((g,t),[])},key=lambda x:-x[1])
    prior_dom=bool(w<0.5)
    if prior_dom: st='informational_prior_dominated_no_adjustment'
    elif r['role_status'] in ('source_confirmed','named_starter_team_source'): st='eligible_source_confirmed_unilateral'
    else: st='conditional_scenario_unilateral'
    return dict(team=t,status=st,starter=r['starter'],role_status=r['role_status'],role_evidence=r['evidence'],role_urls=r['urls'],season_dropbacks=int(n),shrink_weight_on_data=round(float(w),3),prior_dominated=prior_dom,posterior_sd_epa_per_db=round(post_sd,4),starter_q=round(float(qv),4),embedded_proxy_q=round(float(emb),4),embedded_qbs_per_history_game_name_dropbacks=embq,delta_epa_per_db=round(float(d),4),unilateral_team_swing_pts=round(beta*d,2),unilateral_team_swing_pts_raw=float(beta*d),unilateral_swing_coefficient_only_ci95=sorted([round(lo*d,2),round(hi*d,2)]))
cf=json.load(open(RAW+'current_forecasts.json'))['games']
games=[]
for g in cf:
    h,a=side(g['home_abbr']),side(g['away_abbr'])
    games.append(dict(game_id=g['game_id'],home=g['home_abbr'],away=g['away_abbr'],core_raw_margin_home=g['raw_margin_home'],home_side=h,away_side=a,raw_home_adjustment_pts=None,game_adjustment_note='Not computed: a full-game adjustment would need a verified role status for BOTH sides; unknown other side is not zero. Unilateral per-team scenarios only.'))
art=dict(version='NFL-QB-swap-currentseason-v1-REVIEW-DRAFT',cutoff=str(C.date()),spec=dict(quality='same-season prior passing EPA/dropback (dropbacks=attempts+sacks, all passers with epa, incl 0.47% non-QB-position dropbacks) shrunk to same-season league mean before cutoff',k_dropbacks=k,s2=s2,tau2=tau2,k_source='variance components from 2020..2025 within-season data (seasons < 2026)',beta_pts_per_epa_db=round(beta,2),beta_coefficient_ci95=[round(lo,2),round(hi,2)],ci_caveat='Coefficient-only bootstrap interval. Partial uncertainty: excludes uncertainty in starter quality (posterior_sd), embedded-proxy error, role/starter uncertainty and selection/confounding. Not a full predictive interval.',beta_basis='all rows 2021..11/12/2026 with date<cutoff, chronological core residuals, bootstrap 2000 draws seed per-index',prior_dominated_rule='shrink weight on data <0.5 (prior outweighs data), structural not tuned'),limits=['QB passing only','association not causal','embedded QB is EPA proxy not core conventional-rate input','non-QB, CFB null','recheck roles at deployment'],games=games)
json.dump(art,open(OUT+'integration_artifact_cs.json','w'),indent=1)
print('beta %.2f [%.2f,%.2f] k %.1f'%(beta,lo,hi,k))
for t in ['SEA','LV','MIN']: 
    s=side(t); print({x:s[x] for x in ('team','status','season_dropbacks','shrink_weight_on_data','posterior_sd_epa_per_db','delta_epa_per_db','unilateral_team_swing_pts','unilateral_swing_coefficient_only_ci95')})
