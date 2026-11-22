import unittest,importlib.util,json,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('up',Path(__file__).with_name('update.py'));u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class Tests(unittest.TestCase):
 def test_names(self):
  for a,b in [('Miami Ohio','Miami (OH) RedHawks'),('FIU','Florida International Panthers'),('Miami Florida','Miami Hurricanes'),('San Jose State','San José State Spartans')]:self.assertTrue(u.match(a,b))
  self.assertFalse(u.match('Miami Ohio','Miami Hurricanes'))
 def test_dates(self):
  q={'captured_at':'2026-11-13T16:04:00Z','kickoff_text':'SAT 11:00AM CT'}
  self.assertTrue(u.validday(q,'2026-11-14T17:00Z'));self.assertFalse(u.validday(q,'2026-11-21T17:00Z'));self.assertFalse(u.validday(q,'2026-11-15T17:00Z'))
 def test_current_schedule(self):
  sched={'events':{'1':{'kickoff':'2026-11-15T18:00Z'}}}
  self.assertEqual(u.current_kickoff('1','2026-11-14T21:15Z',sched),'2026-11-15T18:00Z')
  self.assertEqual(u.current_kickoff('2','2026-11-14T21:15Z',sched),'2026-11-14T21:15Z')
  q={'captured_at':'2026-11-14T13:07:00Z','kickoff_text':'SAT 3:15PM CT'}
  self.assertFalse(u.validday(q,u.current_kickoff('1','2026-11-14T21:15Z',sched)))
 def test_current_cfb_pointer(self):
  with tempfile.TemporaryDirectory() as temp:
   r=Path(temp);p=r/'tools/cfb/new/current_forecasts.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'games':[{'event_id':'new'}]}));(r/'cfb_current_release.json').write_text(json.dumps({'forecast_path':'tools/cfb/new/current_forecasts.json'}))
   self.assertEqual(u.current_cfb_forecasts(r),[{'event_id':'new'}])
 def test_cfb_pointer_escape(self):
  with tempfile.TemporaryDirectory() as temp:
   r=Path(temp);(r/'cfb_current_release.json').write_text(json.dumps({'forecast_path':'../current_forecasts.json'}))
   with self.assertRaises(ValueError):u.current_cfb_forecasts(r)
 def test_pairs(self):
  self.assertFalse(u.match('Ohio','Ohio State Buckeyes') and u.match('Ball State','Northwestern Wildcats'))
if __name__=='__main__':unittest.main()
