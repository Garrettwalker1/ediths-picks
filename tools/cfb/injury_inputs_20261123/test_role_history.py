import unittest,json,pathlib,subprocess,sys
from official_lineup_adapter import role_for_attempt
from build_role_history import build
P=pathlib.Path(__file__).parent
class RoleLayerTests(unittest.TestCase):
 def setUp(self):self.data=build();self.overrides={('249','401862835','5159360'):'QB_EMERGENCY'}
 def test_exact_event_override(self):self.assertEqual(role_for_attempt('WR','249','401862835','5159360',self.overrides),'QB_EMERGENCY')
 def test_other_event_isolation(self):self.assertEqual(role_for_attempt('WR','249','other','5159360',self.overrides),'WR')
 def test_other_team_isolation(self):self.assertEqual(role_for_attempt('WR','248','401862835','5159360',self.overrides),'WR')
 def test_other_player_isolation(self):self.assertEqual(role_for_attempt('WR','249','401862835','other',self.overrides),'WR')
 def test_baseline_attempts(self):self.assertEqual([h['baseline_pass_attempts']for h in self.data['histories']],[347,316])
 def test_emergency_seven_attempts(self):
  rows=[r for h in self.data['histories']for r in h['rows']if r['event_role']=='QB_EMERGENCY'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['pass_att'],7);self.assertEqual(rows[0]['channel'],'quarterback_passing');self.assertEqual(rows[0]['roster_position'],'WR')
 def test_no_prospective_allocation(self):self.assertTrue(all(h['prospective_allocation']is None for h in self.data['histories']))
 def test_incomplete_defense_withheld(self):
  x=json.load(open(P/'two_team_official_lineup_adapter.json'));f=x['teams'][0]['quality_flags'][0];self.assertEqual(f['def_count'],10);self.assertFalse(f['admit_complete_unit_state'])
 def test_unresolved_rows_retained(self):
  x=json.load(open(P/'two_team_official_lineup_adapter.json'));u=[r for r in x['teams'][1]['rows']if r['espn_id']is None];self.assertEqual(len(u),4);self.assertEqual(len(set(r['name']for r in u)),2)
 def test_no_forecast_effect(self):self.assertFalse(self.data['numerical_forecast_effect']);self.assertFalse(self.data['baseline_values_changed']);self.assertFalse(self.data['protected_evaluation_changed'])
if __name__=='__main__':unittest.main()
