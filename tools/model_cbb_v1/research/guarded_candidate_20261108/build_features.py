#!/usr/bin/env python3
"""Parse harvested ESPN boxscore files into per-team per-game efficiency rows.
Possessions estimated: FGA - OReb + TO + 0.475*FTA (standard box-score approximation).
Point-in-time discipline: callers must build rolling features using only games before tip."""
import json, os, sys, csv, glob

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def made_att(v):
    if not isinstance(v, str) or "-" not in v: return None, None
    a, b = v.split("-", 1)
    return num(a), num(b)

def team_row(game, team_block, side, event_meta):
    stats = {s.get("name"): s.get("displayValue") for s in team_block.get("statistics", [])}
    fgm, fga = made_att(stats.get("fieldGoalsMade-fieldGoalsAttempted"))
    tpm, tpa = made_att(stats.get("threePointFieldGoalsMade-threePointAttempted") or stats.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
    ftm, fta = made_att(stats.get("freeThrowsMade-freeThrowsAttempted"))
    oreb = num(stats.get("offensiveRebounds")); dreb = num(stats.get("defensiveRebounds"))
    tov = num(stats.get("totalTurnovers") or stats.get("turnovers"))
    ast = num(stats.get("assists")); stl = num(stats.get("steals")); blk = num(stats.get("blocks"))
    if None in (fgm, fga, oreb, tov, fta): return None
    poss = fga - oreb + tov + 0.475 * fta
    score = num((team_block.get("score") if isinstance(team_block.get("score"), (int, float, str)) else None))
    return {
        "event_id": event_meta["id"], "date": event_meta.get("date"), "side": side,
        "team": team_block.get("team", {}).get("displayName"),
        "teamId": team_block.get("team", {}).get("id"),
        "neutral": event_meta.get("neutral"), "poss": round(poss, 1),
        "fgm": fgm, "fga": fga, "tpm": tpm, "tpa": tpa, "ftm": ftm, "fta": fta,
        "oreb": oreb, "dreb": dreb, "tov": tov, "ast": ast, "stl": stl, "blk": blk,
    }

def parse_game(path):
    d = json.load(open(path))
    header = d.get("header", {})
    comps = header.get("competitions", [])
    if not comps: return []
    comp = comps[0]
    meta = {"id": header.get("id") or os.path.basename(path)[5:-5],
            "date": comp.get("date"), "neutral": bool(comp.get("neutralSite"))}
    # scores by team id from header competitors
    scores = {}
    for c in comp.get("competitors", []):
        scores[str(c.get("team", {}).get("id"))] = num(c.get("score"))
    bx = d.get("boxscore", {})
    # side from header competitor homeAway matched on stable team ID, never array order
    side_by_id = {}
    for c in comp.get("competitors", []):
        tid = str(c.get("team", {}).get("id"))
        ha = c.get("homeAway")
        if tid and ha in ("home", "away"):
            side_by_id[tid] = ha
    rows = []
    for t in bx.get("teams", []):
        tid = str(t.get("team", {}).get("id"))
        side = side_by_id.get(tid)
        if side is None:
            return []  # ambiguous sides: drop the game rather than guess
        r = team_row(d, t, side, meta)
        if r:
            r["teamId"] = tid
            r["score"] = scores.get(tid) or scores.get(t.get("team", {}).get("id"))
            rows.append(r)
    if len(rows) == 2 and rows[0].get("score") is not None and rows[1].get("score") is not None:
        rows[0]["opp_score"] = rows[1]["score"]; rows[1]["opp_score"] = rows[0]["score"]
        rows[0]["opp_poss"] = rows[1]["poss"]; rows[1]["opp_poss"] = rows[0]["poss"]
        avg_poss = (rows[0]["poss"] + rows[1]["poss"]) / 2
        for r in rows:
            r["pace"] = round(avg_poss, 1)
            r["off_eff"] = round(100 * r["score"] / avg_poss, 2) if avg_poss else None
            r["def_eff"] = round(100 * r["opp_score"] / avg_poss, 2) if avg_poss else None
            r["efg"] = round((r["fgm"] + 0.5 * (r["tpm"] or 0)) / r["fga"], 4) if r["fga"] else None
            r["tov_pct"] = round(r["tov"] / r["poss"], 4) if r["poss"] else None
            denom_or = r["oreb"] + (rows[1]["dreb"] if r is rows[0] else rows[0]["dreb"])
            r["or_pct"] = round(r["oreb"] / denom_or, 4) if denom_or else None
            r["ftr"] = round(r["fta"] / r["fga"], 4) if r["fga"] else None
    return rows

if __name__ == "__main__":
    games_dir, out_csv = sys.argv[1], sys.argv[2]
    fields = ["event_id","date","side","team","teamId","neutral","score","opp_score","poss","opp_poss","pace","off_eff","def_eff","efg","tov_pct","or_pct","ftr","fgm","fga","tpm","tpa","ftm","fta","oreb","dreb","tov","ast","stl","blk"]
    n = 0
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for p in sorted(glob.glob(os.path.join(games_dir, "*.json"))):
            for r in parse_game(p):
                w.writerow({k: r.get(k) for k in fields}); n += 1
    print("rows:", n)
