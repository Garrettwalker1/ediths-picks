import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('up',Path(__file__).with_name('update.py'));u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class Tests(unittest.TestCase):
 def test_names(self):
  for a,b in [('FIU','Florida International Panthers'),('Miami Florida','Miami Hurricanes'),('San Jose State','San José State Spartans')]:self.assertTrue(u.match(a,b))
  self.assertFalse(u.match('Miami Ohio','Miami Hurricanes'))
 def test_dates(self):
  q={'captured_at':'2026-11-13T16:04:00Z','kickoff_text':'SAT 11:00AM CT'}
  self.assertTrue(u.validday(q,'2026-11-14T17:00Z'));self.assertFalse(u.validday(q,'2026-11-21T17:00Z'));self.assertFalse(u.validday(q,'2026-11-15T17:00Z'))
 def test_pairs(self):
  self.assertFalse(u.match('Ohio','Ohio State Buckeyes') and u.match('Ball State','Northwestern Wildcats'))
if __name__=='__main__':unittest.main()
