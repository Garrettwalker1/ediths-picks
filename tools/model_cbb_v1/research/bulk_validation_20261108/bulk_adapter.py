#!/usr/bin/env python3
"""Adapt SportsDataverse ESPN-derived bulk parquet (repo data/bulk/) into the
team_games CSV format used by train_model.py. Feature formulas identical to
build_features.py (possessions = FGA - OReb + TO + 0.475*FTA; efficiency vs avg poss).
BULK_HISTORY.md limits honored: outcomes/boxscores only; no ranks/records/enriched fields.
Known limitation: only away_non_div1_team exists upstream; non-D1 HOME opponents are not
flagged by the source and are not filtered (recorded in output as d1_flag_source)."""
import sys, pandas as pd

def load_season(bulkdir, year):
    tb = pd.read_parquet(f"{bulkdir}/team_box_{year}.parquet")
    sc = pd.read_parquet(f"{bulkdir}/mbb_schedule_{year}.parquet")
    want = ["game_id", "neutral_site", "season_type", "status_type_completed",
            "tournament_id", "away_non_div1_team", "venue_address_city", "venue_address_state"]
    sc = sc[[c for c in want if c in sc.columns]]  # away_non_div1_team absent in some seasons
    df = tb.merge(sc, on="game_id", how="left", suffixes=("", "_sc"))
    return df

def to_rows(df):
    df = df[df["status_type_completed"] == True]
    rows = []
    for gid, g in df.groupby("game_id"):
        if len(g) != 2: continue
        g = g.copy()
        g["poss"] = g["field_goals_attempted"] - g["offensive_rebounds"] + g["total_turnovers"] + 0.475 * g["free_throws_attempted"]
        if (g["poss"] <= 0).any(): continue
        a, b = g.iloc[0], g.iloc[1]
        avg_poss = (a["poss"] + b["poss"]) / 2
        for r, o in ((a, b), (b, a)):
            oreb_opp = o["defensive_rebounds"]
            or_denom = r["offensive_rebounds"] + oreb_opp
            rows.append({
                "event_id": str(r["game_id"]), "date": str(r["game_date"]),
                "side": r["team_home_away"], "team": r["team_display_name"],
                "teamId": str(r["team_id"]), "neutral": bool(r["neutral_site"]),
                "score": float(r["team_score"]), "opp_score": float(r["opponent_team_score"]),
                "poss": round(r["poss"], 1), "opp_poss": round(o["poss"], 1),
                "pace": round(avg_poss, 1),
                "off_eff": round(100 * r["team_score"] / avg_poss, 2),
                "def_eff": round(100 * r["opponent_team_score"] / avg_poss, 2),
                "efg": round((r["field_goals_made"] + 0.5 * r["three_point_field_goals_made"]) / r["field_goals_attempted"], 4) if r["field_goals_attempted"] else None,
                "tov_pct": round(r["total_turnovers"] / r["poss"], 4),
                "or_pct": round(r["offensive_rebounds"] / or_denom, 4) if or_denom else None,
                "ftr": round(r["free_throws_attempted"] / r["field_goals_attempted"], 4) if r["field_goals_attempted"] else None,
                "fgm": r["field_goals_made"], "fga": r["field_goals_attempted"],
                "tpm": r["three_point_field_goals_made"], "tpa": r["three_point_field_goals_attempted"],
                "ftm": r["free_throws_made"], "fta": r["free_throws_attempted"],
                "oreb": r["offensive_rebounds"], "dreb": r["defensive_rebounds"],
                "tov": r["total_turnovers"], "ast": r["assists"], "stl": r["steals"], "blk": r["blocks"],
                "season_type": int(r["season_type"]), "tournament_id": r.get("tournament_id"),
                "away_non_d1": bool(r.get("away_non_div1_team")) if pd.notna(r.get("away_non_div1_team")) else None,
            })
    return rows

if __name__ == "__main__":
    bulkdir, year, out_csv = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = to_rows(load_season(bulkdir, year))
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"season {year}: {len(rows)} team-game rows -> {out_csv}")
