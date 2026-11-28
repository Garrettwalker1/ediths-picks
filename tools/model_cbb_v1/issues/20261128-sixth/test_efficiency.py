import unittest
from efficiency import estimate,predict_efficiency
from test_predictor import game,target,T
class EfficiencyTests(unittest.TestCase):
 def g(self):
  g=game();g['period']=2;g['team_box_statistics']={t:{'fieldGoalsMade-fieldGoalsAttempted':'25-60','freeThrowsMade-freeThrowsAttempted':'15-20','offensiveRebounds':'10','turnovers':'12','totalTurnovers':'12'} for t in ('A','B')};return g
 def test_possessions(self):self.assertEqual(estimate(self.g()),71.5)
 def test_finite_prediction(self):
  p=predict_efficiency([self.g()],target(),T);self.assertEqual(p['status'],'prediction_computed_not_issued');self.assertTrue(0<p['total_points']<300)
 def test_ot_normalized(self):
  a=self.g();a['period']=3;p=predict_efficiency([a],target(),T);self.assertAlmostEqual(p['adjusted_efficiency']['A']['pace_per40'],71.5*40/45)
 def test_missing_efficiency_withholds(self):
  p=predict_efficiency([game()],target(),T);self.assertEqual(p['status'],'withheld')
 def test_same_event(self):
  g=self.g();g['event_id']='t';self.assertEqual(predict_efficiency([g],target(),T)['status'],'withheld')
if __name__=='__main__':unittest.main()
