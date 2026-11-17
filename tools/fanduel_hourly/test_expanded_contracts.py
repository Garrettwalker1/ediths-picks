"""Offline Week11 supplemental identity and explicit partial-category contracts."""
import datetime,hashlib,json,pathlib,shutil,tempfile,unittest
from build_player_comparison import build_event,load,R
class ExpandedContracts(unittest.TestCase):
 def run_build(self,idx=20,path=None):
  root=R/'tools/fanduel_hourly/player_captures/week11-expansion-20261117'
  p=path or root/str(idx);old=load(root/str(idx)/'event.json')
  g=next(g for g in load(R/'tools/nfl/current_season_20261117/current_forecasts.json')['games'] if g['event_id']==old['event_id'])
  return build_event(p,g,old['source_url'],load(R/'tools/nfl/week11_2026/td_projection_snapshot.json'),load(R/'tools/nfl/week11_2026/td_week11_primary.json'),load(R/'player_projections.json'),datetime.datetime.fromisoformat('2026-11-17T18:00:00+00:00'))
 def modified(self,idx=20):
  t=tempfile.TemporaryDirectory();p=pathlib.Path(t.name)
  shutil.copytree(R/f'tools/fanduel_hourly/player_captures/week11-expansion-20261117/{idx}',p,dirs_exist_ok=True)
  return t,p
 def reseal(self,p,file,kind):
  m=load(p/'manifest.json')
  for s in m:
   if s.get('kind')==kind:s['sha256']=hashlib.sha256((p/file).read_bytes()).hexdigest()
  (p/'manifest.json').write_text(json.dumps(m))
 def test_exact_four_category_replay(self):
  e=self.run_build();self.assertEqual(len(e['category_coverage']['present']),4)
  self.assertEqual(e['category_coverage']['not_observed'],['receiving_yards','receptions'])
  self.assertEqual(e['coverage']['unmatched_selections'],2)
 def test_WAS_WSH_and_reviewed_aliases(self):
  e=self.run_build(24);self.assertEqual(e['coverage']['joined_selections'],70)
  self.assertEqual(e['coverage']['unmatched_selections'],0)
  self.assertTrue(any(r['team_id']=='WSH' and r['player_name']=='Chigoziem Okonkwo' for r in e['rows']))
 def test_no_partial_exception_by_default(self):
  t,p=self.modified()
  with t:
   (p/'availability_audit.json').unlink()
   with self.assertRaisesRegex(ValueError,'all six'):self.run_build(path=p)
 def test_cannot_omit_observed_category(self):
  t,p=self.modified()
  with t:
   x=load(p/'rendered.json');x=json.loads(x['content']);x['markets']=[m for m in x['markets'] if not m['header'].endswith(' - Rushing Yds')];(p/'rendered.json').write_text(json.dumps(x))
   with self.assertRaisesRegex(ValueError,'omitted'):self.run_build(path=p)
 def test_identity_hash(self):
  t,p=self.modified()
  with t:
   (p/'identity_evidence.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'identity evidence provenance'):self.run_build(path=p)
 def test_stable_id_cannot_be_fabricated(self):
  t,p=self.modified()
  with t:
   x=load(p/'identity_evidence.json');x['identities'][0]['player_id']='not-real';x['identities'][0]['crosswalk_gsis_id']='not-real';(p/'identity_evidence.json').write_text(json.dumps(x));self.reseal(p,'identity_evidence.json','identity_evidence')
   with self.assertRaisesRegex(ValueError,'crosswalk'):self.run_build(path=p)
 def test_audit_hash(self):
  t,p=self.modified()
  with t:
   (p/'availability_audit.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'audit hash'):self.run_build(path=p)
 def test_audit_stale(self):
  t,p=self.modified()
  with t:
   x=load(p/'availability_audit.json');x['at']='2026-11-17T16:00:00Z';(p/'availability_audit.json').write_text(json.dumps(x));self.reseal(p,'availability_audit.json','availability_audit')
   with self.assertRaisesRegex(ValueError,'window'):self.run_build(path=p)
if __name__=='__main__':unittest.main()
