#!/usr/bin/env python3
"""Adapt SportsDataverse ESPN-derived bulk parquet into team_games CSV. FAIL-CLOSED.
Every omitted game is audited with a reason (adapter_audit.json alongside output).
BULK_HISTORY.md limits: outcomes/boxscores only; no ranks/records/enriched fields.
Season-specific D1 membership: a team is D1 for a season iff it carries a non-null,
non-zero conference_id in that season's schedule (source-derived, per-season). Known
edge: true D1 independents (rare, e.g. transitional schools) are misclassified non-D1;
suspected independents (null-conf teams with 15+ games) are listed in the audit.
Usage: bulk_adapter.py BULKDIR YEAR OUT_CSV"""
import sys, json, math, pandas as pd

CORE = ["field_goals_attempted", "offensive_rebounds", "total_turnovers",
        "free_throws_attempted", "field_goals_made", "three_point_field_goals_made",
        "free_throws_made", "defensive_rebounds", "team_score", "opponent_team_score"]

def load_season(bulkdir, year):
    tb = pd.read_parquet(f"{bulkdir}/team_box_{year}.parquet")
    sc = pd.read_parquet(f"{bulkdir}/mbb_schedule_{year}.parquet")
    want = ["game_id", "neutral_site", "season_type", "status_type_completed",
            "tournament_id", "away_non_div1_team", "venue_address_city", "venue_address_state",
            "home_id", "away_id", "home_conference_id", "away_conference_id"]
    sc = sc[[c for c in want if c in sc.columns]]
    return tb, sc

def membership(sc):
    """Season-specific D1 set from schedule conference IDs (both sides)."""
    ids = {}
    for home_col, away_col in (("home_id", "home_conference_id"), ("away_id", "away_conference_id")):
        if home_col not in sc.columns: continue
        for tid, cid in zip(sc[home_col], sc[away_col]):
            if pd.isna(tid): continue
            ids.setdefault(str(int(tid)) if float(tid).is_integer() else str(tid), set())
            if pd.notna(cid) and cid != 0:
                ids[str(int(tid)) if float(tid).is_integer() else str(tid)].add(int(cid))
    d1 = {t for t, cs in ids.items() if cs}
    games_played = {}
    for col in ("home_id", "away_id"):
        if col in sc.columns:
            for tid in sc[col]:
                if pd.notna(tid):
                    k = str(int(tid)) if float(tid).is_integer() else str(tid)
                    games_played[k] = games_played.get(k, 0) + 1
    suspected_independents = sorted(t for t in set(ids) - d1 if games_played.get(t, 0) >= 15)
    return d1, suspected_independents

def to_rows(tb, sc):
    d1, suspected = membership(sc)
    scm = sc.set_index("game_id")
    audit = {"omitted": [], "counts": {}, "suspected_d1_independents_excluded": suspected,
             "d1_team_count": len(d1)}
    def omit(gid, reason):
        audit["omitted"].append({"game_id": str(gid), "reason": reason})
        audit["counts"][reason] = audit["counts"].get(reason, 0) + 1
    rows = []
    for gid, g in tb.groupby("game_id"):
        if len(g) != 2:
            omit(gid, "row_count_not_2"); continue
        a, b = g.iloc[0], g.iloc[1]
        ids = {str(a["team_id"]), str(b["team_id"])}
        if len(ids) != 2:
            omit(gid, "team_ids_not_unique"); continue
        sides = {a["team_home_away"], b["team_home_away"]}
        if sides != {"home", "away"}:
            omit(gid, "sides_not_opposing"); continue
        m = scm.loc[gid] if gid in scm.index else None
        if m is None:
            omit(gid, "no_schedule_row"); continue
        if m["status_type_completed"] is not True and m["status_type_completed"] != True:
            omit(gid, "not_completed"); continue
        ok = True
        for r in (a, b):
            for c in CORE:
                v = r[c]
                if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                    omit(gid, f"nonfinite_core:{c}"); ok = False; break
            if not ok: break
        if not ok: continue
        if float(a["team_score"]) != float(b["opponent_team_score"]) or float(b["team_score"]) != float(a["opponent_team_score"]):
            omit(gid, "score_cross_mismatch"); continue
        g = g.copy()
        g["poss"] = g["field_goals_attempted"] - g["offensive_rebounds"] + g["total_turnovers"] + 0.475 * g["free_throws_attempted"]
        if (g["poss"] <= 0).any():
            omit(gid, "nonpositive_possessions"); continue
        a, b = g.iloc[0], g.iloc[1]
        avg_poss = (a["poss"] + b["poss"]) / 2
        home_d1 = str(a["team_id"]) in d1 if a["team_home_away"] == "home" else str(b["team_id"]) in d1
        away_d1 = str(b["team_id"]) in d1 if a["team_home_away"] == "home" else str(a["team_id"]) in d1
        for r, o in ((a, b), (b, a)):
            or_denom = r["offensive_rebounds"] + o["defensive_rebounds"]
            rows.append({
                "event_id": str(r["game_id"]), "date": str(r["game_date"])[:10],
                "side": r["team_home_away"], "team": r["team_display_name"],
                "teamId": str(r["team_id"]), "neutral": bool(m["neutral_site"]),
                "score": float(r["team_score"]), "opp_score": float(r["opponent_team_score"]),
                "poss": round(r["poss"], 1), "opp_poss": round(o["poss"], 1),
                "pace": round(avg_poss, 1),
                "off_eff": round(100 * r["team_score"] / avg_poss, 2),
                "def_eff": round(100 * r["opponent_team_score"] / avg_poss, 2),
                "efg": round((r["field_goals_made"] + 0.5 * r["three_point_field_goals_made"]) / r["field_goals_attempted"], 4),
                "tov_pct": round(r["total_turnovers"] / r["poss"], 4),
                "or_pct": round(r["offensive_rebounds"] / or_denom, 4) if or_denom else None,
                "ftr": round(r["free_throws_attempted"] / r["field_goals_attempted"], 4),
                "fgm": r["field_goals_made"], "fga": r["field_goals_attempted"],
                "tpm": r["three_point_field_goals_made"], "tpa": r["three_point_field_goals_attempted"],
                "ftm": r["free_throws_made"], "fta": r["free_throws_attempted"],
                "oreb": r["offensive_rebounds"], "dreb": r["defensive_rebounds"],
                "tov": r["total_turnovers"], "ast": r["assists"], "stl": r["steals"], "blk": r["blocks"],
                "season_type": int(m["season_type"]),
                "tournament_id": None if pd.isna(m.get("tournament_id")) else m.get("tournament_id"),
                "home_d1": home_d1, "away_d1": away_d1, "d1_game": home_d1 and away_d1,
            })
    return rows, audit

if __name__ == "__main__":
    bulkdir, year, out_csv = sys.argv[1], sys.argv[2], sys.argv[3]
    tb, sc = load_season(bulkdir, year)
    rows, audit = to_rows(tb, sc)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    with open(out_csv.replace(".csv", "_audit.json"), "w") as f:
        json.dump({"season": year, "rows": len(rows), **audit,
                   "omitted": audit["omitted"][:200], "omitted_total": len(audit["omitted"])}, f, indent=1)
    print(f"season {year}: {len(rows)} rows, omitted {len(audit['omitted'])} "
          f"({audit['counts']}), d1 teams {audit['d1_team_count']}, "
          f"suspected independents excluded: {len(audit['suspected_d1_independents_excluded'])}")
