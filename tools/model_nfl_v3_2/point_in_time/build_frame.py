#!/usr/bin/env python3
"""Strictly lagged team-form frame. No target-game player, weather or roster fields.

Raw weekly player stats can describe a game only for a later kickoff. Previous-
season priors use completed previous-season games. The first historical season
cannot have a prior, so its early games are absent from the fit rather than
filled using full-year information. Book prices are benchmarks only.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np,pandas as pd
SOURCES=Path('/tmp/training/nflv32')
FORMS={'total_yds_for':'yf','total_yds_allowed':'ya','pass_yds':'pyf','pass_yds_allowed':'pya','rush_yds':'ryf','rush_yds_allowed':'rya','giveaways':'gv','takeaways':'tk','sacks_taken':'skt','sacks_made':'skm','cmp_pct':'qbc','pass_td':'ptd','points_for':'pf','points_allowed':'pa'}
FEATURES=['d_'+z for z in ('pf_f','pa_f','yf_f','ya_f','pyf_r4','pya_r4','ryf_r4','rya_r4','gv_r4','tk_r4','skt_r4','skm_r4','qbc_r4','ptd_r4','gp')]
def build(games,sp,as_of=None):
 games=games[(games.season>=2010)&(games.game_type=='REG')].copy()
 games['date']=pd.to_datetime(games.gameday)
 if as_of is not None:
  # Target-week rows remain on the schedule; only past games feed form.
  assert pd.Timestamp(as_of).tzinfo is None
  games.loc[games.date>pd.Timestamp(as_of),['home_score','away_score']]=np.nan
 known=games.dropna(subset=['home_score','away_score'])
 sp=sp[(sp.season_type=='REG')&(sp.season>=2010)].copy()
 if as_of is not None:
  played=known[['season','week','home_team','away_team']]
  playedteams=pd.concat([played[['season','week','home_team']].rename(columns={'home_team':'team'}),played[['season','week','away_team']].rename(columns={'away_team':'team'})]).drop_duplicates()
  sp=sp.merge(playedteams,on=['season','week','team'],how='inner')
 agg=sp.groupby(['season','week','team','opponent_team'],as_index=False).agg(pass_yds=('passing_yards','sum'),rush_yds=('rushing_yards','sum'),ints_thrown=('passing_interceptions','sum'),fum_lost=('fumbles_lost_total','sum'),sacks_taken=('sacks_suffered','sum'),pass_att=('attempts','sum'),pass_cmp=('completions','sum'),pass_td=('passing_tds','sum'),def_sacks=('def_sacks','sum'),def_int=('def_interceptions','sum'),fum_rec_opp=('fumble_recovery_opp','sum'))
 tg=agg.copy();tg['total_yds_for']=tg.pass_yds+tg.rush_yds;tg['giveaways']=tg.ints_thrown+tg.fum_lost;tg['takeaways']=tg.def_int+tg.fum_rec_opp;tg['sacks_made']=tg.def_sacks
 dv=agg.rename(columns={'team':'_team','opponent_team':'team'})[['season','week','team','_team','pass_yds','rush_yds']].rename(columns={'_team':'opponent_team','pass_yds':'pass_yds_allowed','rush_yds':'rush_yds_allowed'})
 tg=tg.merge(dv,on=['season','week','team','opponent_team'],how='left',validate='one_to_one');tg['total_yds_allowed']=tg.pass_yds_allowed+tg.rush_yds_allowed;tg['cmp_pct']=tg.pass_cmp/tg.pass_att.replace(0,np.nan)
 h=known[['game_id','season','week','home_team','home_score','away_score']].rename(columns={'home_team':'team','home_score':'points_for','away_score':'points_allowed'})
 a=known[['game_id','season','week','away_team','away_score','home_score']].rename(columns={'away_team':'team','away_score':'points_for','home_score':'points_allowed'})
 tg=tg.merge(pd.concat([h,a]),on=['season','week','team'],how='left',validate='one_to_one');tg=tg[tg.game_id.notna()].copy()
 # Add target-game team rows with feature inputs missing; shifted transforms never use them.
 future=games[games.home_score.isna()|games.away_score.isna()]
 add=pd.concat([future[['game_id','season','week','home_team']].rename(columns={'home_team':'team'}),future[['game_id','season','week','away_team']].rename(columns={'away_team':'team'})]);tg=pd.concat([tg,add],ignore_index=True)
 assert not tg.duplicated(['game_id','team']).any()
 tg=tg.sort_values(['team','season','week','game_id']).reset_index(drop=True)
 grp=tg.groupby(['team','season'],sort=False)
 for col,label in FORMS.items():
  tg[label+'_r4']=grp[col].transform(lambda z:z.shift().rolling(4,min_periods=1).mean())
 tg['gp']=grp['game_id'].transform(lambda z:z.shift().rolling(100,min_periods=1).count()).fillna(0)
 for col,label in [('total_yds_for','yf'),('total_yds_allowed','ya'),('points_for','pf'),('points_allowed','pa')]:
  prior=tg[tg[col].notna()].groupby(['team','season'])[col].mean().rename('prior_'+label).reset_index();prior['season']+=1;tg=tg.merge(prior,on=['team','season'],how='left',validate='many_to_one')
  w=tg.gp/(tg.gp+2);tg[label+'_f']=w*tg[label+'_r4'].fillna(tg['prior_'+label])+(1-w)*tg['prior_'+label]
 # Same-season rolling form deliberately absent until the team played once.
 cols=[v for v in FEATURES if v!='d_gp'];stem=[v[2:] for v in cols]+['gp']
 hh=tg.set_index(['game_id','team']);home=games[['game_id','home_team']].set_index('game_id');away=games[['game_id','away_team']].set_index('game_id')
 h=hh.reindex(pd.MultiIndex.from_arrays([home.index,home.home_team]))[stem].reset_index(level=1,drop=True)
 a=hh.reindex(pd.MultiIndex.from_arrays([away.index,away.away_team]))[stem].reset_index(level=1,drop=True)
 result=games.set_index('game_id').copy()
 for col in stem:result['d_'+col]=h[col]-a[col]
 result['margin']=result.home_score-result.away_score
 result=result.reset_index();assert len(result)==len(games) and not result.game_id.duplicated().any()
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--games',type=Path,default=SOURCES/'games.csv');p.add_argument('--stats',type=Path,nargs='+',default=sorted(SOURCES.glob('spw_*.csv')));p.add_argument('--as-of');p.add_argument('--out',type=Path,required=True);args=p.parse_args()
 games=pd.read_csv(args.games,low_memory=False);needed=['season','season_type','week','team','opponent_team','passing_yards','rushing_yards','passing_interceptions','fumbles_lost_total','sacks_suffered','attempts','completions','passing_tds','def_sacks','def_interceptions','fumble_recovery_opp'];sp=pd.concat([pd.read_csv(f,usecols=needed,low_memory=False) for f in args.stats],ignore_index=True);frame=build(games,sp,args.as_of);args.out.parent.mkdir(parents=True,exist_ok=True);frame.to_parquet(args.out,index=False)
 print(json.dumps({'rows':len(frame),'seasons':[int(frame.season.min()),int(frame.season.max())],'complete':int(frame.margin.notna().sum()),'scorable':int(frame[FEATURES].notna().all(axis=1).sum()),'sha256':hashlib.sha256(args.out.read_bytes()).hexdigest()}))
