"""Archive replay and fail-closed event-contract tests, no network access."""
import copy, datetime, json, pathlib, tempfile, unittest
from build_player_comparison import build_event, load, stamp, R

class EventContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.archive=R/'tools/fanduel_hourly/player_captures/20261113T214129161Z'
  cls.game=next(g for g in load(R/'tools/nfl/current_season_20261113/current_forecasts.json')['games'] if g['event_id']=='401873053')
  cls.url='https://sportsbook.fanduel.com/football/nfl/new-england-patriots-@-detroit-lions-35605986'
  cls.td=load(R/'tools/nfl/week10_2026/td_projection_snapshot.json')
  cls.primary=load(R/'tools/nfl/week10_2026/td_week10_primary.json')
  cls.generic=load(R/'player_projections.json')
  cls.now=stamp('2026-11-13T22:00:00Z')
 def run_build(self,archive=None,game=None,url=None,now=None):
  return build_event(archive or self.archive,game or self.game,url or self.url,self.td,self.primary,self.generic,now or self.now)
 def test_exact_replay(self):
  event=self.run_build();old=load(self.archive/'comparison_reference.json')
  self.assertEqual(event['rows'],old['rows'])
  self.assertEqual(event['identity_gaps'],old['identity_gaps'])
  self.assertEqual(event['checked_at'],'2026-11-13T21:41:29.161Z')
 def test_wrong_url(self):
  with self.assertRaisesRegex(ValueError,'URL'):self.run_build(url=self.url+'-wrong')
 def test_future_capture(self):
  with self.assertRaisesRegex(ValueError,'future capture'):self.run_build(now=stamp('2026-11-13T21:00:00Z'))
 def test_postkickoff(self):
  game=dict(self.game,date='2026-11-13T20:00Z')
  with self.assertRaisesRegex(ValueError,'post-kickoff'):self.run_build(game=game)
 def test_timezone_required(self):
  with self.assertRaises(ValueError):stamp('2026-11-13T21:41:29')
 def modified(self,change):
  temp=tempfile.TemporaryDirectory();path=pathlib.Path(temp.name)
  for source in self.archive.iterdir():
   (path/source.name).write_bytes(source.read_bytes())
  x=load(path/'rendered.json');x=json.loads(x['content']);change(x)
  (path/'rendered.json').write_text(json.dumps(x))
  return temp,path
 def test_no_state_evidence(self):
  temp,path=self.modified(lambda x:x.update(state_evidence=[]))
  with temp,self.assertRaisesRegex(ValueError,'Illinois'):self.run_build(archive=path)
 def test_unexpanded(self):
  temp,path=self.modified(lambda x:x['markets'][0].update(expanded='false'))
  with temp,self.assertRaisesRegex(ValueError,'expanded'):self.run_build(archive=path)
 def test_roster_hash_mismatch(self):
  temp,path=self.modified(lambda x:None)
  (path/'DET.json').write_text('{}')
  with temp,self.assertRaisesRegex(ValueError,'hash'):self.run_build(archive=path)

if __name__=='__main__':unittest.main()
