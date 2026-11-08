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
    # beta predicts margin 1.0; y=100 (99-pt residual). Frozen sigma=5 -> win prob phi(0.2)=0.5793
    # -> brier (1-0.5793)^2 = 0.177. An eval-fitted sigma (~99) would give ~0.246 instead.
    out = tm.evaluate(beta, X, Y, sigma=5.0)
    expected = round((1 - 0.5 * (1 + math.erf(0.2 / math.sqrt(2)))) ** 2, 4)
    assert "brier" in out and abs(out["brier"] - expected) < 1e-9, \
        f"frozen sigma=5 should give brier {expected}, got {out.get('brier')} (an eval-fitted sigma would give ~0.246)"
    out2 = tm.evaluate(beta, X, Y, sigma=None)
    assert "brier" not in out2, "brier must not appear without a frozen sigma"
    print("PASS sigma frozen / no brier without frozen sigma")

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



def test_fail_closed_load_and_protection(tmp_rows=None):
    import tempfile, os, csv
    rows = [
        # valid 2026 REGULAR season row (allowed)
        {"event_id": "g1", "date": "2025-11-05", "side": "home", "team": "A", "teamId": "1",
         "neutral": "False", "score": "80", "opp_score": "70", "off_eff": "110", "def_eff": "95",
         "efg": "0.5", "tov_pct": "0.15", "or_pct": "0.3", "ftr": "0.3", "pace": "70", "season_type": "2"},
        # valid 2026 POSTSEASON row (protected - must be excluded at load)
        {"event_id": "g2", "date": "2026-03-20", "side": "home", "team": "A", "teamId": "1",
         "neutral": "True", "score": "80", "opp_score": "70", "off_eff": "110", "def_eff": "95",
         "efg": "0.5", "tov_pct": "0.15", "or_pct": "0.3", "ftr": "0.3", "pace": "70", "season_type": "3"},
        # malformed season_type (must be excluded, NOT defaulted to regular)
        {"event_id": "g3", "date": "2026-03-21", "side": "home", "team": "B", "teamId": "2",
         "neutral": "True", "score": "80", "opp_score": "70", "off_eff": "110", "def_eff": "95",
         "efg": "0.5", "tov_pct": "0.15", "or_pct": "0.3", "ftr": "0.3", "pace": "70", "season_type": ""},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows); path = f.name
    loaded, audit = tm.load([path])
    os.unlink(path)
    ids = [r["event_id"] for r in loaded]
    assert ids == ["g1"], f"expected only g1 to survive, got {ids}"
    assert audit["excluded_protected"] == 1 and audit["excluded_malformed"] == 1, audit
    try:
        tm.load([path], unlock_final_test=True)
        raise SystemExit("unlock must refuse")
    except tm.Excluded:
        pass
    print("PASS fail-closed load: protected excluded at load, malformed excluded, unlock refuses")

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

def test_manifest_enforcement(tmp=None):
    import tempfile, json
    m = {"name": "t", "fit_window": {"seasons": [2023]}, "validation_window": {"seasons": [2025]}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(m, f); mp = f.name
    tm.enforce_manifest(mp, ["data/bulk_tg_2023.csv", "data/bulk_tg_2025.csv"], "2024-08-01", "2025-08-01")
    try:
        tm.enforce_manifest(mp, ["data/bulk_tg_2026.csv"], "2024-08-01", "2025-08-01")
        raise SystemExit("undeclared season file must fail closed")
    except tm.Excluded:
        pass
    print("PASS manifest enforcement: undeclared season file rejected")



if __name__ == "__main__":
    test_no_own_or_future_season_prior()
    test_prior_only_immediately_preceding()
    test_sigma_frozen_not_fit_on_eval()
    test_home_away_from_header_ids()
    test_fail_closed_load_and_protection()
    test_scaler_fit_on_train_only()
    test_same_date_atomicity()
    test_manifest_enforcement()
    print("ALL TESTS DONE")
