import unittest,json,tempfile
from pathlib import Path
from bind_current_cfb_routes import bind
class Tests(unittest.TestCase):
 def run_case(self,rows):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=r/'tools/cfb/new/current_forecasts.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'games':[{'event_id':'1','away':'Kent State Golden Flashes','home':'Eastern Michigan Eagles','date':'2026-11-25T00:00Z'}]}));(r/'cfb_current_release.json').write_text(json.dumps({'forecast_path':'tools/cfb/new/current_forecasts.json'}));return bind(r,{'at':'2026-11-22T14:56Z','url':'https://sportsbook.fanduel.com/navigation/ncaaf','items':rows})
 def row(self,**extra):return dict({'away':'Kent State','home':'Eastern Michigan','kickoff':'2026-11-25T00:00:00.000Z','url':'https://sportsbook.fanduel.com/football/ncaa-football-games/test-1'},**extra)
 def test_exact(self):
  b=self.run_case([self.row()]);self.assertEqual(len(b['accepted']),1);self.assertEqual(b['accepted'][0]['kickoff'],'2026-11-25T00:00Z')
 def test_conflict(self):
  q=self.row();q['kickoff']='2026-11-25T01:00Z';b=self.run_case([q]);self.assertEqual(len(b['accepted']),0);self.assertEqual(len(b['rejected']),1)
 def test_unknown(self):
  q=self.row();q['away']='Ohio';self.assertEqual(len(self.run_case([q])['accepted']),0)
