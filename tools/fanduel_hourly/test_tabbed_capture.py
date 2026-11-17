import unittest,json,datetime,copy,pathlib
from merge_player_comparisons import merge,stamp,R
class Tabbed(unittest.TestCase):
 def setUp(self):
  self.event=json.loads((R/'tools/fanduel_hourly/player_captures/week11-first-20261117/event.json').read_text());self.slate=json.loads((R/'tools/nfl/current_season_20261117/current_forecasts.json').read_text())['games'];self.now=stamp('2026-11-17T16:00:00Z')
 def test_exact_rows_times_and_six_categories(self):
  e=self.event;o=merge({},[e],self.slate,self.now);self.assertEqual(o['rows'],e['rows']);self.assertEqual(o['coverage']['events_captured'],1);self.assertEqual(o['coverage']['other_events_not_captured'],12);self.assertEqual(len({r['market']for r in o['rows']}),6);self.assertGreater(len({r['captured_at']for r in o['rows']}),1)
 def test_wrong_tab_held(self):
  self.event['rows'][0]['source_url']='https://sportsbook.fanduel.com/other-event'
  with self.assertRaisesRegex(ValueError,'provenance'):merge({},[self.event],self.slate,self.now)
 def test_bad_window_held(self):
  self.event['capture_window_start']='2026-11-17T14:00:00Z'
  with self.assertRaisesRegex(ValueError,'window'):merge({},[self.event],self.slate,self.now)
if __name__=='__main__':unittest.main()
