import unittest,pandas as pd
from source_adapter import depth_at,player_link_id,unique_map,build
class SourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=build('2026-11-23T21:08:00Z')
 def test_teams(self):self.assertEqual(len(set(r['team']for r in self.data['depth'])),32)
 def test_missing_gsis_retained(self):self.assertEqual(sum(r['gsis_id']is None for r in self.data['depth']),7)
 def test_carter_pfr_withheld(self):self.assertTrue(all(r['gsis_id']is None for r in self.data['snap_exposure']if r['pfr_player_id']=='CartNa00'))
 def test_espn_link_not_entry(self):
  r=next(x for x in self.data['espn_statuses']if x['espn_player_id']=='4567048');self.assertEqual(r['gsis_id'],'00-0038134');self.assertNotEqual(r['injury_entry_id'],r['espn_player_id'])
 def test_espn_identity_counts(self):self.assertEqual(len(self.data['espn_statuses']),800);self.assertEqual(sum(x['gsis_id']is None for x in self.data['espn_statuses']),2)
 def test_missing_weekly_times(self):self.assertFalse(self.data['weekly_injuries']['row_timestamp_available'])
 def test_no_numeric_effect(self):self.assertFalse(self.data['numerical_forecast_effect']);self.assertIsNone(self.data['prospective_allocation'])
 def test_ambiguous_link_refused(self):self.assertIsNone(player_link_id({'links':[{'href':'https://www.espn.com/nfl/player/_/id/1/a'},{'href':'https://www.espn.com/nfl/player/_/id/2/b'}]}))
 def test_crosswalk_collision_withheld(self):self.assertEqual(unique_map(pd.DataFrame({'pfr':['a','a'],'gsis':['1','2']}),'pfr','gsis'),{})
 def test_strict_snapshot_before(self):
  f=pd.DataFrame([dict(dt='2026-11-23T07:00Z',team='A',pos_grp_id='O',pos_slot=1,pos_rank=1)]);self.assertTrue(depth_at(f,'2026-11-23T07:00Z').empty)
 def test_slot_collision_refused(self):
  f=pd.DataFrame([dict(dt='2026-11-23T07:00Z',team='A',pos_grp_id='O',pos_slot=1,pos_rank=1)]*2)
  with self.assertRaises(ValueError):depth_at(f,'2026-11-23T08:00Z')
 def test_naive_time_refused(self):
  with self.assertRaises(ValueError):depth_at(pd.DataFrame(),'2026-11-23T08:00')
if __name__=='__main__':unittest.main()
