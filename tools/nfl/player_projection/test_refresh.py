"""Offline regression and fail-closed guards; no publication or model fitting."""
import datetime as dt,json,unittest
import pandas as pd
from engine import build,m,R
from refresh import prepare,resolve,team
class RepairTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.games=pd.read_csv(R/'tools/nfl/week9_2026/games.csv')
  cls.raw=pd.concat([pd.read_csv(R/f'tools/player_projection_cache/stats_{y}.csv',usecols=m.COLS,low_memory=False) for y in [2023,2024,2025]]+[pd.read_csv(R/'tools/nfl/week9_2026/player_stats_2026.csv',usecols=m.COLS,low_memory=False)],ignore_index=True)
 def test_november_discovery(self):
  season,week,slate,prior=resolve(self.games,dt.datetime.fromisoformat('2026-11-03T07:00:00-06:00'));self.assertEqual((season,week,len(slate)),(2026,9,15));prepare(self.raw,self.games,season,week,prior)
 def test_missing_stats_fails(self):
  season,week,_,prior=resolve(self.games,dt.datetime.fromisoformat('2026-11-03T07:00:00-06:00'))
  with self.assertRaises(ValueError):prepare(self.raw[~((self.raw.season==2026)&(self.raw.team=='TEN')&(self.raw.week==8))],self.games,season,week,prior)
 def test_partial_prior_fails(self):
  d=self.games.copy();d.loc[(d.season==2026)&(d.week==8),'away_score']=None
  with self.assertRaises(ValueError):resolve(d,dt.datetime.fromisoformat('2026-11-03T07:00:00-06:00'))
 def test_january_previous_season(self):
  d=self.games.copy();last=d[(d.season==2026)&(d.week==18)].iloc[0];day=dt.date.fromisoformat(last.gameday)
  # Set all earlier scheduled games final to isolate cross-year date discovery.
  d.loc[(d.season==2026)&(d.week<18),['away_score','home_score']]=0
  season,week,_,_=resolve(d,dt.datetime.combine(day,dt.time(1),dt.timezone.utc));self.assertEqual((season,week),(2026,18))
 def test_no_current_week_leak(self):
  season,week,_,prior=resolve(self.games,dt.datetime.fromisoformat('2026-11-03T07:00:00-06:00'));raw=prepare(self.raw,self.games,season,week,prior);self.assertEqual(raw[raw.season==2026].week.max(),8)
 def test_fixed_current_numeric_replay(self):
  old=json.loads((R/'player_projections.json').read_text());fantasy=json.loads((R/'fantasy.json').read_text());rost=json.loads((R/'tools/nfl/player_projection_refresh_20261103/current_rosters.json').read_text())
  slate=self.games[(self.games.season==2026)&(self.games.week==9)];opp={}
  for x in slate.itertuples():opp[team(x.home_team)]=team(x.away_team);opp[team(x.away_team)]=team(x.home_team)
  raw=self.raw[(self.raw.season_type=='REG')&((self.raw.season<2026)|(self.raw.week<=8))].copy();players,_,match=build(raw,rost,fantasy,opp,2026,9)
  by={p['player_id']:p for p in old['players']};self.assertEqual(len(players),463);self.assertEqual(len(match),435)
  old_match={p['player_id']:p for p in old['matchup_context']['rows']}
  for row in match:
   for k in ['team','position','opponent','defense_sample_games','raw_allowed','sos_adjusted_vs_opponent_normal','head_to_head']:
    self.assertEqual(row[k],old_match[row['player_id']][k],(row['player'],k))
  for p in players:
   for k in ['receiving_yards','rushing_yards','receptions','anytime_td_probability','boom_probability','bust_probability','drivers','team','position']:
    self.assertEqual(p[k],by[p['player_id']][k],(p['player'],k))
 def test_duplicate_roster_identity_fails(self):
  roster=json.loads((R/'tools/nfl/player_projection_refresh_20261103/current_rosters.json').read_text());roster['DUP']=roster['ARI']
  fantasy=json.loads((R/'fantasy.json').read_text())
  with self.assertRaises(ValueError):build(self.raw.copy(),roster,fantasy,{},2026,9)
 def test_target_week_is_not_fixed(self):
  d=self.games.copy();d.loc[(d.season==2026)&(d.week<10),['away_score','home_score']]=0
  season,week,_,_=resolve(d,dt.datetime.fromisoformat('2026-11-10T07:00:00-06:00'));self.assertEqual((season,week),(2026,10))
 def test_week_started_fails(self):
  with self.assertRaises(ValueError):resolve(self.games,dt.datetime.fromisoformat('2026-11-08T07:00:00-06:00'))
 def test_fixed_previous_252(self):
  from fixed_inference import load_models
  models=load_models();old=json.loads((R/'tools/nfl/player_projection_refresh_20261103/previous_oct20.json').read_text());raw=self.raw[(self.raw.season_type=='REG')&((self.raw.season<2026)|(self.raw.week<=6))]
  for p in old['players']:
   g=raw[raw.player_id==p['player_id']].sort_values(['season','week']);z=g.iloc[-1].copy()
   for c in m.BASE_FEATURES:
    for n in [3,6]:z[f'{c}_r{n}']=g[c].tail(n).mean()
   for name,key,features in [('recv','receiving_yards',m.RF),('rush','rushing_yards',m.QF),('recs','receptions',m.REPF)]:self.assertEqual(round(m.pred(models[name],features,z),1),p[key]['median'])
   for name,key,features in [('td','anytime_td_probability',m.TDF),('boom','boom_probability',m.RF),('bust','bust_probability',m.BF)]:self.assertEqual(round(m.prob(models[name],features,z),3) if name!='bust' or z.targets_r3>=4 else None,p[key])
if __name__=='__main__':unittest.main()
