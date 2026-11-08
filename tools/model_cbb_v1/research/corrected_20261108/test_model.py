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
    eval_rows = [{"x": [0.0]*(len(tm.FEATS)+1), "y": 100.0} for _ in range(10)]  # huge residuals
    # beta predicts margin 1.0; y=100 (99-pt residual). Frozen sigma=5 -> win prob phi(0.2)=0.5793
    # -> brier (1-0.5793)^2 = 0.177. An eval-fitted sigma (~99) would give ~0.246 instead.
    out = tm.evaluate(beta, eval_rows, sigma=5.0)
    expected = round((1 - 0.5 * (1 + math.erf(0.2 / math.sqrt(2)))) ** 2, 4)
    assert "brier" in out and abs(out["brier"] - expected) < 1e-9, \
        f"frozen sigma=5 should give brier {expected}, got {out.get('brier')} (an eval-fitted sigma would give ~0.246)"
    out2 = tm.evaluate(beta, eval_rows, sigma=None)
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

if __name__ == "__main__":
    test_no_own_or_future_season_prior()
    test_prior_only_immediately_preceding()
    test_sigma_frozen_not_fit_on_eval()
    test_home_away_from_header_ids()
    print("ALL TESTS DONE")
