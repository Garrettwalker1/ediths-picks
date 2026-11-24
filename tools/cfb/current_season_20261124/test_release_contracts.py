#!/usr/bin/env python3
"""Offline release-contract tests, not an accuracy test."""
import pathlib,json,gzip,hashlib,datetime,unittest,re,warnings
warnings.simplefilter('ignore',ResourceWarning)
from zoneinfo import ZoneInfo
R=pathlib.Path('/tmp/edith');release=json.load(open(R/'cfb_current_release.json'));P=(R/release['forecast_path']).parent;W=(R/release['rankings_path']).parent
class Contracts(unittest.TestCase):
 def test_01_original_bytes(self):
  for x in json.load(open(W/'preserved_original_files.json')):self.assertEqual(hashlib.sha256((R/x['path']).read_bytes()).hexdigest(),x['sha256'],x['path'])
 def test_02_source_completeness_and_digest(self):
  audit=json.load(open(W/'fetch_audit.json'));rank=json.load(open(W/'power_ratings.json'));self.assertEqual(set(audit['ids']),set(rank['source_game_ids']));self.assertEqual(audit['failures'],[])
  for row in json.load(open(W/'source_manifest.json')):
   f=R/row.get('storage_path',row['file']);b=f.read_bytes();self.assertEqual(hashlib.sha256(gzip.decompress(b)if f.suffix=='.gz'else b).hexdigest(),row['sha256'])
 def test_03_no_retroactive_predictions(self):
  d=json.load(open(P/'current_forecasts.json'));issued=datetime.datetime.fromisoformat(d['metadata']['generated_at']);self.assertTrue(all(datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00'))>issued for g in d['games']));self.assertEqual(len(d['games']),69);self.assertEqual(sum(datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Chicago')).date().isoformat()=='2026-11-21'for g in d['games']),0);self.assertTrue(all(g['injury_numeric_adjustment']is None for g in d['games']));self.assertTrue(all(g['display_margin_home']*2==round(g['display_margin_home']*2)for g in d['games']));self.assertEqual(hashlib.sha256((P/'current_forecasts.json').read_bytes()).hexdigest(),(P/'forecast_seal.sha256').read_text().split()[0])
 def test_04_feature_boundaries(self):
  d=json.load(open(P/'current_forecasts.json'));m=d['metadata'];self.assertFalse(m['preseason_talent_inputs']);self.assertFalse(m['prior_season_stats_inputs']);self.assertFalse(m['odds_inputs']);self.assertFalse(m['injury_numeric_inputs']);self.assertEqual(m['training_rows'],2068)
 def test_05_current_rosters(self):
  d=json.load(open(P/'current_roster_manifest.json'));self.assertEqual(len(d),138)
  for r in d:self.assertGreater(r['player_count'],0);self.assertEqual(r['season']['year'],2026);self.assertEqual(hashlib.sha256(gzip.decompress((P/r['storage_path']).read_bytes())).hexdigest(),r['sha256'])
 def test_06_primary_report_binding_and_rows(self):
  d=json.load(open(P/'injury_designations.json'));norm=lambda s:re.sub('[^a-z0-9]','',s.lower());rs=json.load(open(P/'current_roster_manifest.json'));alias={}
  slate=json.load(gzip.open(P/'sources/slate.json.gz','rt'))
  for e in slate['events']:
   for c in e['competitions'][0]['competitors']:
    t=c['team']
    for k in ['displayName','shortDisplayName','location']:alias[norm(t[k])]=t['displayName']
  alias.update({norm('Miami (FL)'):'Miami Hurricanes',norm('Florida St.'):'Florida State Seminoles'})
  for g in d['games']:
   for team in g['teams']:
    self.assertIsNone(team['numeric_adjustment']);self.assertTrue(all(x['status']not in ['Available','Exempt']for x in team['rows']))
    if team['evidence_level'].startswith('primary'):
     raw=json.load(gzip.open(P/team['raw_source_path'],'rt'));r=raw[team['report_id']];self.assertEqual(r['footer']['date'],datetime.datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Chicago')).date().isoformat());self.assertEqual({alias[norm(t['teamName'])]for t in r['games']},{g['home'],g['away']});t=next(x for x in r['games']if alias[norm(x['teamName'])]==team['team']);self.assertEqual({(x['name'],x['status'])for x in t['rows']if x['status']not in ['Available','Exempt']},{(x['player'],x['status'])for x in team['rows']})
 def test_07_pick_policy_only(self):
  d=json.load(open(R/'tools/cfb/team_pick_policy.json'));self.assertEqual(len(d['eligible_team_ids']),67);self.assertNotIn('source_user_message',d);teams=d['eligible_team_ids'];self.assertTrue(all(x['conference']in d['conferences']for x in teams.values()));self.assertFalse(any(x['team']=='Notre Dame Fighting Irish'for x in teams.values()));self.assertTrue(any('Sam Houston Bearkats' in [g['home'],g['away']]for g in json.load(open(P/'current_forecasts.json'))['games']))
 def test_08_live_view_config(self):
  s=(R/'cfb-inline.js').read_text();self.assertIn('cfb_current_release.json',s);self.assertIn('Secondary republication, not primary-verified',s);self.assertIn('No numerical injury/replacement adjustment',s);s=(R/'index.html').read_text();self.assertNotIn('Current AP comparison unavailable',s);self.assertIn('822 completed',s);self.assertIn(release['rankings_path'],s)
if __name__=='__main__':unittest.main()
