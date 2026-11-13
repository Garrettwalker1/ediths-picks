import copy, unittest
from build_player_comparison import load, stamp, R
from merge_player_comparisons import merge

class MergeContract(unittest.TestCase):
 def setUp(self):
  self.old=load(R/'tools/fanduel_hourly/player_captures/20261113T214129161Z/comparison_reference.json')
  self.slate=load(R/'tools/nfl/current_season_20261113/current_forecasts.json')['games']
 def test_no_retimestamp(self):
  result=merge(self.old,[],self.slate,stamp('2026-11-13T23:00Z'))
  self.assertEqual(result['checked_at'],self.old['checked_at'])
  self.assertEqual(result['rows'],self.old['rows'])
  self.assertEqual(result['coverage']['events_captured'],1)
  self.assertFalse(result['events'][0]['frozen'])
 def test_kickoff_freeze(self):
  result=merge(self.old,[],self.slate,stamp('2026-11-15T14:30Z'))
  self.assertTrue(result['events'][0]['frozen'])
  self.assertEqual(result['rows'],self.old['rows'])
 def test_no_early_refresh(self):
  result=merge(self.old,[],self.slate,stamp('2026-11-13T23:00Z'))
  with self.assertRaisesRegex(ValueError,'60 minutes'):
   merge(self.old,result['events'],self.slate,stamp('2026-11-13T23:00Z'))
 def test_no_backfill(self):
  result=merge(self.old,[],self.slate,stamp('2026-11-13T23:00Z'))
  with self.assertRaisesRegex(ValueError,'kicked-off'):
   merge({},result['events'],self.slate,stamp('2026-11-15T14:30Z'))
 def test_no_wrong_kickoff(self):
  result=merge(self.old,[],self.slate,stamp('2026-11-13T23:00Z'))
  result['events'][0]['kickoff']='2026-11-16T14:30Z'
  with self.assertRaisesRegex(ValueError,'kickoff changed'):
   merge({},result['events'],self.slate,stamp('2026-11-13T23:00Z'))
 def test_no_duplicate_incoming(self):
  result=merge(self.old,[],self.slate,stamp('2026-11-13T23:00Z'))
  with self.assertRaises(ValueError):
   merge({},result['events']*2,self.slate,stamp('2026-11-13T23:00Z'))

if __name__=='__main__':unittest.main()
