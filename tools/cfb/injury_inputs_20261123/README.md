# Injury-input role layer, incorporated November 23, 2026

This is working injury-input code and retained descriptive evidence, not a display-only table. It does not change a forecast, production baseline, protected evaluation, future workload allocation or numeric injury adjustment.

`official_lineup_adapter.py` joins the two official team-season gamebook collections with strict team/name/jersey identity gates and source-local URL bridges. It retains four unresolved Houston rows representing two people and withholds UNT's incomplete ten-player defensive lineup from complete-unit admission.

`build_role_history.py` consumes those verified overrides and the same FBS event histories and passing counts used by the baseline. It classifies Tyre's seven UNT-Tulane attempts as emergency-QB passing only for team249/event401862835/player5159360, retaining his roster WR position. Nothing reclassifies other events or players. `role_aware_history.json` is the consumed descriptive historical input artifact. Future allocation stays null. No caller in the active numerical forecast has been changed.

Reproduce offline from this directory:

```
python official_lineup_adapter.py
python build_verified_lineup_roles.py
python build_role_history.py
python -m unittest test_role_history.py
```

Ten actual unit tests cover event/team/player isolation, seven emergency attempts, baseline totals, unresolved rows, incomplete lineup handling and no forecast effects. The inherited adapter additionally has nine inline assertions, which are not nine independent unit tests.

`UPSTREAM_PACKAGE_SHA256.json` records the corrected v2 received package, before local portable-path edits. `incorporation_manifest.json` records incorporated file hashes. Original source manifests retain November23 approximately13:00CT collection times. Later code incorporation is not a new status collection. Raw sources, URLs and observations retain their original scope. Starting tables are listed starts, not full-game snap composition, injury cause or future availability.
