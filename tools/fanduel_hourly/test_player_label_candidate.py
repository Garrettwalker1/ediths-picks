import unittest
from player_label_candidate import parse_label,attach_identity

class Labels(unittest.TestCase):
 def test_six_markets(self):
  for source,target in [('Passing Yds','passing_yards'),('Passing TDs','passing_tds'),('Rushing Yds','rushing_yards'),('Receiving Yds','receiving_yards'),('Total Receptions','receptions')]:
   self.assertEqual(parse_label(f'A Player - {source}, A Player Over, 2.5, -114')['market'],target)
  self.assertEqual(parse_label('Any Time Touchdown Scorer, Jahmyr Gibbs, -250')['market'],'anytime_td')
 def test_last_first_alt_not_anytime(self):
  for s in ['Last Touchdown Scorer, Jahmyr Gibbs, +420','First Touchdown Scorer, Jahmyr Gibbs, +420','A Player - Alt Passing Yds, A Player Over, 2.5, -114']:
   self.assertIsNone(parse_label(s))
 def test_defense_excluded(self):self.assertIsNone(parse_label('Any Time Touchdown Scorer, New England Defense, +850'))
 def test_mismatched_name(self):
  with self.assertRaises(ValueError):parse_label('A Player - Passing Yds, B Player Over, 2.5, -114')
 def test_unknown_not_published(self):
  a,b=attach_identity([parse_label('Any Time Touchdown Scorer, Jahmyr Gibbs, -250')],'1','2099-01-01','IL','2026-11-13','https://example.invalid',{})
  self.assertEqual(a,[]);self.assertEqual(b[0]['reason'],'missing_identity')
 def test_duplicate_fails(self):
  r=parse_label('Any Time Touchdown Scorer, Jahmyr Gibbs, -250')
  with self.assertRaises(ValueError):attach_identity([r,r],'1','2099-01-01','IL','2026-11-13','https://example.invalid',{'Jahmyr Gibbs':[dict(player_id='1',team_id='2')]})

if __name__=='__main__':unittest.main()
