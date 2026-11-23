import copy, unittest
from predictor import predict
T='2026-11-24T20:00:00Z'
def target():return dict(event_id='t',home_id='A',away_id='B',season=2027,season_type=2,integrity_verified=True,identity_verified=True,schedule_conflict=False,observed_state='pre',cutoff_estimate='2026-11-24T22:00:00Z',snapshot_received_at='2026-11-24T19:00Z',snapshot_preserved_at='2026-11-24T19:05Z')
def game(e='g',h='A',a='B',hp=80,ap=60):return dict(event_id=e,home_id=h,away_id=a,home_points=hp,away_points=ap,season=2027,season_type=2,integrity_verified=True,identity_verified=True,complete=True,final=True,received_at='2026-11-23T12:00Z',preserved_at='2026-11-23T12:05Z',game_start_observed='2026-11-22T20:00Z')
class Tests(unittest.TestCase):
 def test_prediction(self):
  p=predict([game()],target(),T);self.assertEqual(p['status'],'prediction_computed_not_issued');self.assertAlmostEqual(p['home_points'],(80+5*70)/6);self.assertAlmostEqual(p['total_points'],140)
 def test_missing_form(self):self.assertIsNone(predict([game(a='C')],target(),T)['home_points'])
 def test_no_same_event(self):self.assertEqual(predict([game(e='t')],target(),T)['reason'],'no_verified_prior_games')
 def test_late_receipt(self):
  g=game();g['received_at']=T;self.assertEqual(predict([g],target(),T)['reason'],'no_verified_prior_games')
 def test_late_preservation(self):
  g=game();g['preserved_at']='2026-11-25T00:00Z';self.assertEqual(predict([g],target(),T)['reason'],'no_verified_prior_games')
 def test_incomplete(self):
  g=game();g['complete']=False;self.assertEqual(predict([g],target(),T)['reason'],'no_verified_prior_games')
 def test_unfinal(self):
  g=game();g['final']=False;self.assertEqual(predict([g],target(),T)['reason'],'no_verified_prior_games')
 def test_protected(self):
  g=game();g.update(season=2026,season_type=3);self.assertEqual(predict([g],target(),T)['reason'],'no_verified_prior_games')
 def test_correction_frozen(self):
  g=game();c=copy.deepcopy(g);c.update(home_points=100,received_at='2026-11-24T12:00Z');self.assertEqual(predict([c,g],target(),T),predict([g],target(),T))
 def test_conflicting_identity(self):self.assertEqual(predict([game(),game(a='C')],target(),T)['reason'],'conflicting prior-game identity')
 def test_target_started(self):
  t=target();t['observed_state']='in';self.assertIsNone(predict([game()],t,T)['home_points'])
 def test_target_cutoff_equal(self):
  t=target();t['cutoff_estimate']=T;self.assertIsNone(predict([game()],t,T)['home_points'])
 def test_target_schedule_flag(self):
  t=target();t['schedule_conflict']=True;self.assertIsNone(predict([game()],t,T)['home_points'])
 def test_invalid_scores(self):
  for v in (True,float('nan'),float('inf'),-1,None):
   g=game();g['home_points']=v;self.assertIsNone(predict([g],target(),T)['home_points'])
 def test_timezone_offsets(self):self.assertEqual(predict([game()],target(),T),predict([game()],target(),'2026-11-24T14:00:00-06:00')|{'issuance':T})
 def test_target_snapshot_late(self):
  t=target();t['snapshot_preserved_at']=T;self.assertIsNone(predict([game()],t,T)['home_points'])
if __name__=='__main__':unittest.main()
