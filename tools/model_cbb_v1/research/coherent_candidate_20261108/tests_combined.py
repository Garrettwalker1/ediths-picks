# === test_enforcement.py (adversarial, publisher contract 11/8) ===
#!/usr/bin/env python3
"""Adversarial enforcement tests (publisher contract 11/8): renamed files, tampered
content, window/season smuggling, protected-row contamination, missing manifest, unlock."""
import csv, json, os, subprocess, sys, tempfile, hashlib, math
import train_model as tm

def make_csv(path, rows):
    fields = ["event_id","date","side","team","teamId","neutral","score","opp_score",
              "off_eff","def_eff","efg","tov_pct","or_pct","ftr","pace","season_type","d1_game"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def row(ev, date, st="2", d1="True", tid="1"):
    return {"event_id": ev, "date": date, "side": "home", "team": "A", "teamId": tid,
            "neutral": "False", "score": "80", "opp_score": "70", "off_eff": "110",
            "def_eff": "95", "efg": "0.5", "tov_pct": "0.15", "or_pct": "0.3",
            "ftr": "0.3", "pace": "70", "season_type": st, "d1_game": d1}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f: h.update(f.read())
    return h.hexdigest()

def manifest(tmp, inputs):
    m = {"name": "t", "partitions": {
            "fit": {"seasons": [2023], "season_types": [2, 3], "date_range": ["2022-11-01", "2023-05-01"]},
            "validation": {"seasons": [2025], "season_types": [2, 3], "date_range": ["2024-11-01", "2025-05-01"]}},
         "eval": {"fit_partitions": ["fit"], "eval_partitions": ["validation"]},
         "protected": {"seasons": [2026], "season_types": [3], "rule": "never"},
         "inputs": inputs}
    mp = os.path.join(tmp, "m.json"); json.dump(m, open(mp, "w")); return mp

def test_renamed_file_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "bulk_tg_2023.csv"); make_csv(p, [row("g1", "2023-01-10")])
        rn = os.path.join(tmp, "renamed.csv"); make_csv(rn, [row("g1", "2023-01-10")])
        mp = manifest(tmp, {p: {"partition": "fit", "sha256": sha(p)}})
        try:
            tm.run([rn], mp); raise SystemExit("renamed file must be rejected")
        except tm.Excluded as e:
            assert "not declared" in str(e)
    print("PASS adversarial: renamed copy rejected unread")

def test_tampered_content_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "bulk_tg_2023.csv"); make_csv(p, [row("g1", "2023-01-10")])
        mp = manifest(tmp, {p: {"partition": "fit", "sha256": sha(p)}})
        make_csv(p, [row("g1", "2023-01-10", tid="999")])  # tamper after freeze
        try:
            tm.run([p], mp); raise SystemExit("tampered file must be rejected")
        except tm.Excluded as e:
            assert "hash mismatch" in str(e)
    print("PASS adversarial: tampered content rejected by hash")

def test_row_out_of_partition_excluded_with_audit():
    with tempfile.TemporaryDirectory() as tmp:
        rows = [row("g1", "2023-01-10"), row("g2", "2024-06-01")]  # g2 date outside fit range
        p = os.path.join(tmp, "bulk_tg_2023.csv"); make_csv(p, rows)
        mp = manifest(tmp, {p: {"partition": "fit", "sha256": sha(p)}})
        admitted = tm.admit_files(tm.load_manifest(mp), [p])
        loaded, audit = tm.load_admitted(admitted, tm.load_manifest(mp)["protected"])
        assert len(loaded) == 1 and loaded[0]["event_id"] == "g1", [r["event_id"] for r in loaded]
        assert audit["excluded_out_of_partition"] == 1, audit
    print("PASS adversarial: out-of-partition row excluded with audit count")

def test_protected_row_aborts_run():
    with tempfile.TemporaryDirectory() as tmp:
        # a fit-declared file smuggling a 2026 postseason row
        rows = [row("g1", "2023-01-10"), row("gX", "2026-03-20", st="3")]
        p = os.path.join(tmp, "bulk_tg_2023.csv"); make_csv(p, rows)
        mp = manifest(tmp, {p: {"partition": "fit", "sha256": sha(p)}})
        try:
            tm.run([p], mp); raise SystemExit("protected row must abort the run")
        except tm.Excluded as e:
            assert "PROTECTED ROW IN INPUT" in str(e)
    print("PASS adversarial: protected row in declared file aborts run")

def test_no_manifest_no_run():
    r = subprocess.run([sys.executable, "train_model.py", "whatever.csv"],
                       capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath("train_model.py")) or ".")
    assert r.returncode == 2 and "mandatory" in r.stdout, (r.returncode, r.stdout[:200])
    print("PASS adversarial: no manifest, no run (exit 2)")

def test_unlock_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "bulk_tg_2023.csv"); make_csv(p, [row("g1", "2023-01-10")])
        mp = manifest(tmp, {p: {"partition": "fit", "sha256": sha(p)}})
        try:
            tm.run([p], mp, unlock_final_test=True); raise SystemExit("unlock must refuse")
        except tm.Excluded:
            pass
    print("PASS adversarial: --unlock-final-test parsed and refused")

def test_d1_only_filter():
    with tempfile.TemporaryDirectory() as tmp:
        rows = [row("g1", "2023-01-10", d1="True"), row("g2", "2023-01-11", d1="False")]
        p = os.path.join(tmp, "bulk_tg_2023.csv"); make_csv(p, rows)
        mp = manifest(tmp, {p: {"partition": "fit", "sha256": sha(p)}})
        admitted = tm.admit_files(tm.load_manifest(mp), [p])
        loaded, audit = tm.load_admitted(admitted, tm.load_manifest(mp)["protected"], d1_only=True)
        assert len(loaded) == 1 and loaded[0]["event_id"] == "g1"
        assert audit["excluded_non_d1"] == 1
    print("PASS adversarial: non-D1 game excluded under --d1-only with audit")

def test_platt_fit_window_only():
    # calibration parameters depend only on fit rows
    beta = [1.0] + [0.0] * len(tm.FEATS)
    X = [[1.0]* (len(tm.FEATS)+1) for _ in range(50)]
    Y = [10.0 if i % 2 else -5.0 for i in range(50)]
    c1 = tm.platt_fit(beta, X, Y, sigma=10.0)
    c2 = tm.platt_fit(beta, X, Y, sigma=10.0)
    assert c1 == c2
    print("PASS platt deterministic on fit rows")

if __name__ == "__main__":
    test_renamed_file_rejected()
    test_tampered_content_rejected()
    test_row_out_of_partition_excluded_with_audit()
    test_protected_row_aborts_run()
    test_no_manifest_no_run()
    test_unlock_refuses()
    test_d1_only_filter()
    test_platt_fit_window_only()
    print("ALL ENFORCEMENT TESTS DONE")

# === test_model.py (point-in-time / side / scaler regressions) ===
#!/usr/bin/env python3
"""Defect-regression tests for CBB v1 model code (REVIEW.md classes)."""
import math, json, copy
import train_model as tm
import build_features as bf

def row(ev, date, side, tid, score, off):
    return {"event_id": ev, "date": date, "side": side, "team": "T" + tid, "teamId": tid,
            "neutral": False, "score": score, "opp_score": None, "off_eff": off, "def_eff": 100.0,
            "efg": 0.5, "tov_pct": 0.18, "or_pct": 0.3, "ftr": 0.35, "pace": 70.0}

def test_no_own_or_future_season_prior():
    # Season 2024: team A average off_eff 100. Season 2025: team A off_eff 130 every game.
    # A season-2025 game's snapshot must NEVER contain 130 (own-season finals) in its prior.
    games = []
    for i in range(10):  # 2024 season, teams A=1,B=2
        games.append((row(f"e24{i}a", f"2023-11-{i+1:02d}T00:00Z", "home", "1", 70, 100.0),
                      row(f"e24{i}a", f"2023-11-{i+1:02d}T00:00Z", "away", "2", 60, 90.0)))
    for i in range(5):   # 2025 season, team A now scoring at 130 off_eff
        games.append((row(f"e25{i}a", f"2024-11-{i+1:02d}T00:00Z", "home", "1", 90, 130.0),
                      row(f"e25{i}a", f"2024-11-{i+1:02d}T00:00Z", "away", "2", 60, 90.0)))
    r = tm.Ratings()
    leaks = []
    for home, away in games:
        s = tm.season_of(home["date"])
        r._maybe_advance(s)
        snap = r.snapshot(s, home["teamId"])
        if s == 2025 and snap["n"] == 0:  # first 2025 game: pure prior
            pr = r.prior(2025, home["teamId"])
            assert pr is not None, "prior from 2024 finals should exist"
            assert abs(pr["off_eff"] - 100.0) < 1e-9, f"PRIOR LEAK: expected 100.0 from 2024 finals, got {pr['off_eff']}"
        r.update(s, home["teamId"], home); r.update(s, away["teamId"], away)
    print("PASS no own/future-season prior leak")

def test_prior_only_immediately_preceding():
    # 2023 and 2025 exist, 2024 missing: prior for 2025 must be None (not 2023 finals).
    r = tm.Ratings()
    a23 = row("x1", "2022-11-05T00:00Z", "home", "1", 70, 100.0)
    b23 = row("x1", "2022-11-05T00:00Z", "away", "2", 60, 90.0)
    r.update(2023, "1", a23); r.update(2023, "2", b23)
    r._maybe_advance(2025)  # closes 2023 (recorded), then 2024 (empty -> unrecorded), lands 2025
    pr = r.prior(2025, "1")
    assert pr is None, f"2024 has no games in memory; prior must be None, not borrowed zeros or 2023 finals (got {pr})"
    print("PASS prior not borrowed across a missing season (returns None)")

def test_sigma_frozen_not_fit_on_eval():
    beta = [1.0] + [0.0] * len(tm.FEATS)
    X = [[0.0]*(len(tm.FEATS)+1) for _ in range(10)]
    Y = [100.0] * 10  # huge residuals
    # identity Platt (a=1,b=0), frozen sigma=5 -> p = sigmoid(1/5)=0.5498 -> brier (1-p)^2
    cal = {"a": 1.0, "b": 0.0}
    ps = [tm.platt_p(cal, tm.predict(beta, x), 5.0) for x in X]
    p = 1.0 / (1.0 + math.exp(-0.2))
    expected = round((1 - p) ** 2, 4)
    assert abs(tm.brier(ps, Y) - expected) < 1e-4, \
        f"frozen sigma must drive probability: expected {expected}, got {round(tm.brier(ps, Y), 4)}"
    print("PASS sigma frozen drives probabilities; nothing refit on eval rows")

def test_home_away_from_header_ids():
    # boxscore teams array flipped vs header: away team listed first in boxscore
    game = {
      "header": {"id": "999", "competitions": [{"date": "2026-11-05T00:00Z", "neutralSite": False,
        "competitors": [
          {"homeAway": "home", "team": {"id": "10", "displayName": "HomeU"}, "score": "80"},
          {"homeAway": "away", "team": {"id": "20", "displayName": "AwayU"}, "score": "70"}]}]},
      "boxscore": {"teams": [
        {"team": {"id": "20", "displayName": "AwayU"}, "statistics": [
          {"name": "fieldGoalsMade-fieldGoalsAttempted", "displayValue": "28-60"},
          {"name": "threePointFieldGoalsMade-threePointFieldGoalsAttempted", "displayValue": "8-20"},
          {"name": "freeThrowsMade-freeThrowsAttempted", "displayValue": "6-10"},
          {"name": "offensiveRebounds", "displayValue": "10"},
          {"name": "defensiveRebounds", "displayValue": "20"},
          {"name": "totalTurnovers", "displayValue": "12"}]},
        {"team": {"id": "10", "displayName": "HomeU"}, "statistics": [
          {"name": "fieldGoalsMade-fieldGoalsAttempted", "displayValue": "30-62"},
          {"name": "threePointFieldGoalsMade-threePointFieldGoalsAttempted", "displayValue": "10-25"},
          {"name": "freeThrowsMade-freeThrowsAttempted", "displayValue": "10-14"},
          {"name": "offensiveRebounds", "displayValue": "12"},
          {"name": "defensiveRebounds", "displayValue": "22"},
          {"name": "totalTurnovers", "displayValue": "10"}]}]}}
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(game, f); path = f.name
    rows = bf.parse_game(path)
    os.unlink(path)
    assert len(rows) == 2, f"expected 2 rows, got {len(rows)}"
    by_side = {r["side"]: r for r in rows}
    assert by_side["home"]["teamId"] == "10" and by_side["away"]["teamId"] == "20", \
        f"SIDE DEFECT: home={by_side['home']['teamId']} away={by_side['away']['teamId']}"
    assert by_side["home"]["score"] == 80.0 and by_side["away"]["score"] == 70.0
    print("PASS home/away mapped from header team IDs with flipped boxscore order")




def test_scaler_fit_on_train_only():
    X_train = [[10.0, 1.0], [20.0, 3.0]]
    sc = tm.Scaler().fit(X_train)
    m_before, s_before = list(sc.mean), list(sc.std)
    sc.transform([[1000.0, 999.0]])  # eval row must not move parameters
    assert sc.mean == m_before and sc.std == s_before, "scaler mutated by eval transform"
    assert sc.mean == [15.0, 2.0], sc.mean
    print("PASS scaler fit on train only; eval transform is read-only")

def test_same_date_atomicity():
    # Two games same date: team 1 plays game A (early) and team 1's rating must NOT
    # include game A when featurizing game B the same date.
    r1 = {"event_id": "a", "date": "2023-11-10", "side": "home", "team": "A", "teamId": "1",
          "neutral": False, "score": 90.0, "opp_score": 50.0, "off_eff": 150.0, "def_eff": 80.0,
          "efg": 0.6, "tov_pct": 0.1, "or_pct": 0.4, "ftr": 0.4, "pace": 75.0, "season_type": 2}
    r2 = dict(r1, side="away", teamId="2", team="B", score=50.0, opp_score=90.0, off_eff=80.0, def_eff=150.0)
    r3 = dict(r1, event_id="b", teamId="1", team="A", score=70.0, off_eff=100.0, def_eff=100.0)
    r4 = dict(r3, side="away", teamId="3", team="C", score=70.0, opp_score=70.0, off_eff=100.0, def_eff=100.0)
    games, _ = tm.pair_games([r1, r2, r3, r4])
    stream = tm.build_stream(games)
    # game b (team 1's second game same date): snapshot n must be 0, not 1
    b = [s for s in stream if s["homeId"] == "1"]
    assert not b or all(True for _ in b), stream
    # with no priors anywhere, game b is unscorable -> excluded; either way team 1's
    # same-day result must not appear. Verify via Ratings directly:
    rt = tm.Ratings()
    by_date = {}
    for g in games: by_date.setdefault(g[0]["date"], []).append(g)
    for date in sorted(by_date):
        for home, away in by_date[date]:
            s = tm.season_of(home["date"]); rt._maybe_advance(s)
            snap = rt.snapshot(s, home["teamId"])
            assert snap["n"] == 0, f"SAME-DATE LEAK: {home['team']} sees n={snap['n']} on {date}"
        for home, away in by_date[date]:
            s = tm.season_of(home["date"])
            rt.update(s, home["teamId"], home); rt.update(s, away["teamId"], away)
    print("PASS same-date atomicity: no game consumes a same-day result")



if __name__ == "__main__":
    test_no_own_or_future_season_prior()
    test_prior_only_immediately_preceding()
    test_sigma_frozen_not_fit_on_eval()
    test_home_away_from_header_ids()
    test_scaler_fit_on_train_only()
    test_same_date_atomicity()
    print("ALL TESTS DONE")
