import pathlib,json,sys,datetime,hashlib
import pandas as pd,numpy as np
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).resolve().parent;sys.argv=['reference',str(R),str(P)]
src=(R/'tools/model_cfb_v2/repair_20261011/reference_features.py').read_text()
# Fit exact sealed reference first, all source files unchanged. Archive pre features.
ns={'__name__':'cfb_reference'};exec(compile(src,'sealed_reference','exec'),ns)
sealed=json.load(open(R/'tools/model_cfb_v2/repair_20261011/week7_sealed_research.json'));m=ns['model'];feats=ns['FEATS'];before=ns['feat26'].copy();print('MODEL',len(ns['hist']),len(feats))
# Reproduce sealed reference margins BEFORE touching current stats.
for g in sealed['games']:
 vals={f:float(before.loc[g['home'],f[2:]]-before.loc[g['away'],f[2:]]) for f in feats};p=float(m.predict(pd.DataFrame([vals])[feats])[0]);assert abs(p-g['predicted_margin_home']['2026_ap'])<1e-9,(g['event_id'],p)
# Current feature construction only. Route rawbox loop to combined new scratch, date cutoff updated,
# and prevent any model.fit on Week7 outcomes by reusing the sealed fitted object.
import tempfile
SCRATCH=tempfile.TemporaryDirectory(prefix='cfb-current-boxes-');B=pathlib.Path(SCRATCH.name)/'all_boxscores';B.mkdir()
for f in (R/'tools/cfb/boxscores').glob('*.json'):((B/f.name).unlink() if (B/f.name).is_symlink() else None);(B/f.name).symlink_to(f)
for f in (P/'boxscores').glob('boxscore-*.json'):((B/f.name).unlink() if (B/f.name).is_symlink() else None);(B/f.name).symlink_to(f)
current=src.replace("REPO/'tools/cfb/boxscores'","Path("+repr(str(B))+")").replace('2026-10-12T02:40:00Z','2026-10-16T12:40:00Z').replace("pd.Timestamp('2026-10-12')","pd.Timestamp('2026-10-16')")
current=current.replace("model=make_pipeline(StandardScaler(),Ridge(alpha=10.0)).fit(hist[FEATS],hist.margin)","model=SEALED_MODEL")
ns2={'__name__':'current_features','SEALED_MODEL':m};exec(compile(current,'current_features_no_refit','exec'),ns2);assert ns2['model'] is m, 'Current features must not refit the sealed model';after=ns2['feat26'];before.reset_index().to_csv(P/'sealed_team_features.csv',index=False);after.reset_index().to_csv(P/'current_team_features.csv',index=False)
slate=json.load(open(P/'week7.json'));upcoming={e['id']:e for e in slate['events'] if e['status']['type']['state']=='pre'};out=[]
for g in sealed['games']:
 if g['event_id'] not in upcoming:continue
 v={f:float(after.loc[g['home'],f[2:]]-after.loc[g['away'],f[2:]]) for f in feats};p=float(m.predict(pd.DataFrame([v])[feats])[0]);base=g['predicted_margin_home']['2026_ap'];out.append({'event_id':g['event_id'],'name':g['away']+' at '+g['home'],'date':g['date'],'home':g['home'],'away':g['away'],'sealed_baseline_margin_home_raw':base,'current_stats_research_margin_home_raw':p,'difference_raw':p-base,'changed_features':[f for f in feats if not np.isclose(v[f],g['features'][f])],'features':v,'research_only':True})
json.dump({'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'current stats feature snapshot with sealed fit fixed; excluded from original Week7 forward evaluation','sealed_reproduced_exact':True,'training_outcomes_unchanged':True,'games':out,'new_current_finals':7,'repaired_nonfinal_archives':3,'full_archived_boxscores':455},open(P/'current_research.json','w'),indent=2);print('CURRENT',len(out),'changed',sum(abs(x['difference_raw'])>1e-8 for x in out));after.to_csv(P/'after_features.csv')
