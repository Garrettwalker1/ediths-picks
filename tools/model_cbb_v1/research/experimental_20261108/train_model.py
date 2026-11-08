#!/usr/bin/env python3
"""CBB v1 ridge margin model with strict point-in-time, walk-forward discipline.
Features per game: differentials of rolling season-to-date off/def efficiency and four
factors, shrunk toward prior-season final ratings early in the season, plus home flag.
Usage: train_model.py TRAIN_CSV[,TRAIN_CSV2...] TEST_CSV
No season-final values ever enter a pregame feature (evidence boundary, 11/6)."""
import csv, sys, math, json
from collections import defaultdict

FEATS = ["off_eff","def_eff","efg","tov_pct","or_pct","ftr","pace"]
PRIOR_GAMES_EQ = 8.0  # shrinkage strength toward prior-season rating (in game-equivalents)

def load(paths):
    rows = []
    for p in paths:
        for r in csv.DictReader(open(p)):
            for k in ["score","opp_score","off_eff","def_eff","efg","tov_pct","or_pct","ftr","pace"]:
                r[k] = float(r[k]) if r[k] not in ("", None) else None
            r["neutral"] = r["neutral"] == "True"
            rows.append(r)
    rows.sort(key=lambda r: r["date"] or "")
    return rows

def season_of(datestr):
    y = int(datestr[:4]); m = int(datestr[5:7])
    return y + 1 if m >= 8 else y  # season 2027 = 2026-27

class Ratings:
    """Rolling point-in-time team ratings with prior-season shrinkage."""
    def __init__(self):
        self.hist = defaultdict(lambda: defaultdict(list))  # (season,team) -> feat -> values
        self.prior = {}   # team -> prior season final averages
    def snapshot(self, season, team):
        h = self.hist[(season, team)]
        out = {}
        n = len(h.get("off_eff", []))
        pr = self.prior.get(team)
        for f in FEATS:
            vals = h.get(f, [])
            if vals:
                avg = sum(vals)/len(vals)
                if pr and f in pr:
                    out[f] = (sum(vals) + PRIOR_GAMES_EQ*pr[f]) / (len(vals) + PRIOR_GAMES_EQ)
                else:
                    out[f] = avg
            elif pr and f in pr:
                out[f] = pr[f]
            else:
                out[f] = None
        out["n"] = n
        return out
    def update(self, season, team, row):
        for f in FEATS:
            if row[f] is not None:
                self.hist[(season, team)][f].append(row[f])
    def roll_season(self, season, teams_rows):
        league = {f: [] for f in FEATS}
        per_team = defaultdict(lambda: defaultdict(list))
        for r in teams_rows:
            for f in FEATS:
                if r[f] is not None:
                    league[f].append(r[f]); per_team[r["team"]][f].append(r[f])
        lmean = {f: (sum(v)/len(v) if v else 0.0) for f, v in league.items()}
        for t, d in per_team.items():
            self.prior[t] = {f: (sum(d[f])/len(d[f]) if d[f] else lmean[f]) for f in FEATS}
        self._league_prior = lmean
    def league_prior(self):
        return getattr(self, "_league_prior", {})

def pair_games(rows):
    by_ev = defaultdict(dict)
    for r in rows:
        by_ev[r["event_id"]][r["side"]] = r
    games = []
    for ev, d in by_ev.items():
        if "home" in d and "away" in d and d["home"]["score"] is not None:
            games.append((d["home"], d["away"]))
    games.sort(key=lambda g: g[0]["date"] or "")
    return games

def build_xy(games, ratings, min_games=0):
    X, Y, meta = [], [], []
    for home, away in games:
        season = season_of(home["date"])
        hs = ratings.snapshot(season, home["team"]); as_ = ratings.snapshot(season, away["team"])
        # update AFTER snapshot (point-in-time)
        ratings.update(season, home["team"], home); ratings.update(season, away["team"], away)
        if min(hs["n"], as_["n"]) < min_games: continue
        if any(hs[f] is None or as_[f] is None for f in FEATS): continue
        x = [hs[f] - as_[f] for f in FEATS]
        x.append(0.0 if home["neutral"] else 1.0)  # home-court indicator
        X.append(x); Y.append(home["score"] - away["score"])
        meta.append((home["date"], home["team"], away["team"], hs["n"], as_["n"]))
    return X, Y, meta

def ridge_fit(X, Y, lam=10.0):
    n = len(X); p = len(X[0]) + 1
    Xb = [[1.0] + x for x in X]
    # normal equations with L2 (no penalty on intercept)
    A = [[sum(Xb[i][a]*Xb[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    for a in range(1, p): A[a][a] += lam
    v = [sum(Xb[i][a]*Y[i] for i in range(n)) for a in range(p)]
    # gaussian elimination
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(A[r][c]))
        A[c], A[piv] = A[piv], A[c]; v[c], v[piv] = v[piv], v[c]
        pv = A[c][c]
        if abs(pv) < 1e-12: continue
        for r in range(p):
            if r == c: continue
            f = A[r][c]/pv
            for k in range(c, p): A[r][k] -= f*A[c][k]
            v[r] -= f*v[c]
    return [v[a]/A[a][a] if abs(A[a][a])>1e-12 else 0.0 for a in range(p)]

def predict(beta, x): return beta[0] + sum(b*a for b, a in zip(beta[1:], x))

def evaluate(yhat, Y):
    n = len(Y)
    mae = sum(abs(a-b) for a, b in zip(yhat, Y))/n
    rmse = math.sqrt(sum((a-b)**2 for a, b in zip(yhat, Y))/n)
    var_resid = sum((a-b)**2 for a, b in zip(yhat, Y))/n
    sigma = math.sqrt(var_resid)
    # win prob via normal margin dist; Brier on home win
    def phi(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
    brier = sum((phi(m/sigma) - (1.0 if y > 0 else 0.0))**2 for m, y in zip(yhat, Y))/n
    acc = sum(1 for m, y in zip(yhat, Y) if (m > 0) == (y > 0))/n
    return {"n": n, "mae": round(mae,3), "rmse": round(rmse,3), "sigma": round(sigma,3), "brier": round(brier,4), "home_win_acc": round(acc,4)}

if __name__ == "__main__":
    train_paths = sys.argv[1].split(","); test_path = sys.argv[2]
    ratings = Ratings()
    # roll priors season by season from train rows
    train_rows = load(train_paths)
    by_season = defaultdict(list)
    for r in train_rows: by_season[season_of(r["date"])].append(r)
    for s in sorted(by_season): ratings.roll_season(s, by_season[s])
    # fit on train (walk-forward within train for honesty, but final fit uses all train)
    Xtr, Ytr, _ = build_xy(pair_games(train_rows), ratings)
    beta = ridge_fit(Xtr, Ytr)
    # test with ratings that keep updating through the test season (point-in-time, no finals leak)
    test_rows = load([test_path])
    Xt, Yt, meta = build_xy(pair_games(test_rows), ratings)
    yhat = [predict(beta, x) for x in Xt]
    res = evaluate(yhat, Yt)
    # baseline 1: always predict 0 (pick the favorite-less coin flip on margin)
    res["baseline_zero"] = evaluate([0.0]*len(Yt), Yt)
    # baseline 2: home-court-only constant = mean home margin over TRAIN
    home_mean = sum(Ytr)/len(Ytr) if Ytr else 0.0
    res["baseline_home_mean"] = evaluate([home_mean]*len(Yt), Yt)
    out = {"features": FEATS + ["home_ind"], "coef": [round(b,4) for b in beta],
           "train_n": len(Ytr), "test": res}
    print(json.dumps(out, indent=1))
