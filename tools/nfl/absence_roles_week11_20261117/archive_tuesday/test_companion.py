import hashlib,json,pathlib,unittest
P=pathlib.Path(__file__).resolve().parent
R=P.parents[2]
D=json.loads((P/'companion.json').read_text())
class CompanionTests(unittest.TestCase):
 def test_scope(self):
  self.assertEqual((D['event_id'],D['game_id'],len(D['register'])),('401873066','2026_11_IND_HOU',28))
  self.assertEqual(sum('practice_estimate' in r for r in D['register']),25)
 def test_ids(self):
  ids=[(r['team'],r['gsis_id']) for r in D['register']]
  self.assertEqual(len(ids),len(set(ids)))
  self.assertTrue(all(r['espn_id'] and r['gsis_id'] for r in D['register']))
 def test_no_unsupported_effect(self):
  self.assertEqual(D['numeric_scenarios'],[])
  self.assertFalse(D['forecast_mutated'])
  self.assertTrue(all(r['numeric_injury_adjustment'] is None and r['future_workload_share'] is None for r in D['register']))
  self.assertTrue(all(r['replacement_point_effect'] is None and r['replacement_workload_prediction'] is None for r in D['replacement_role_evidence']))
 def test_core_preserved(self):
  p=R/D['provenance']['core_path']
  self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),D['provenance']['core_sha256'])
  self.assertIsNone(D['baseline']['injury_numeric_adjustment'])
 def test_prior_only(self):
  self.assertEqual(D['provenance']['completed_2026_reg_games'],150)
  self.assertTrue(all(r['last_stat_row'] is None or r['last_stat_row']['week']<=10 for r in D['register']))
 def test_sources_hashed(self):
  for s in D['provenance']['sources']:
   import gzip
   p=P/s['path'];data=gzip.open(p,'rb').read() if str(p).endswith('.gz') else p.read_bytes()
   self.assertEqual(hashlib.sha256(data).hexdigest(),s['sha256'])
 def test_practice_not_game_status(self):
  self.assertTrue(all(r['game_status'] is None for r in D['register']))
 def test_new_ir_transactions(self):
  rows=[r for r in D['register'] if r['reported_name'] in ['Azeez Al-Shaair','Jaylon Carlies']]
  self.assertEqual(len(rows),2)
  self.assertTrue(all('Reserve/Injured' in r['availability'] and not r['numeric_eligibility'] for r in rows))
  self.assertTrue(all(r['practice_estimate']=='DNP' and r['game_status'] is None for r in rows))
 def test_tuesday(self):
  self.assertEqual(sum('tuesday_practice' in r for r in D['register']),24)
  for name,value in [('Kamari Lassiter','DNP'),('Luke Rhodes','LP'),('Charlie Heck','DNP')]:
   r=next(r for r in D['register'] if r['reported_name']==name)
   self.assertEqual(r['tuesday_practice']['participation'],value)
   self.assertIsNone(r['tuesday_practice']['game_status'])
 def test_role_limits(self):
  self.assertEqual(len(D['replacement_role_evidence']),2)
  self.assertIsNone(D['conditional_return_context']['future_workload_share'])
 def test_volume_not_eligibility(self):
  eligible=[r for r in D['register'] if r['established_skill_volume_gate']]
  self.assertEqual(len(eligible),2)
  self.assertTrue(all(r['game_status'] is None for r in eligible))
if __name__=='__main__': unittest.main()
