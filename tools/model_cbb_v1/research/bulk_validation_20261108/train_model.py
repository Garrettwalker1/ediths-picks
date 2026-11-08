#!/usr/bin/env python3
"""CBB v1 ridge margin model. STRICT point-in-time, single chronological stream.

Fixes vs experimental_20261108 (repo REVIEW.md):
1. Priors leak: priors are now computed only when the walk completes a season, from that
   season's accumulated rows only; a game in season S never sees season-S final values.
2. Prior enforced as the IMMEDIATELY PRECEDING completed season (S-1). If S-1 is not in
   memory the prior is None and the game is feature-incomplete (skipped), never borrowed
   from an older season.
3. All team keys are stable teamId strings, never display names.
4. evaluate() takes a sigma frozen on TRAIN residuals; nothing is fit on eval rows.
Split discipline: a calendar boundary separates fit-window rows from eval-window rows;
features for every row are built only from strictly earlier games regardless of the split.
Usage: train_model.py CSV [CSV ...] --eval-start YYYY-MM-DD
"""
import csv, sys, math, json
from collections import defaultdict

FEATS = ["off_eff", "def_eff", "efg", "tov_pct", "or_pct", "ftr", "pace"]
PRIOR_GAMES_EQ = 8.0

def load(paths):
    rows = []
    for p in paths:
        for r in csv.DictReader(open(p)):
            for k in ["score", "opp_score", "off_eff", "def_eff", "efg", "tov_pct", "or_pct", "ftr", "pace"]:
                r[k] = float(r[k]) if r[k] not in ("", None) else None
            r["neutral"] = str(r["neutral"]) == "True"
            r["teamId"] = str(r["teamId"])
            r["season_type"] = int(r["season_type"]) if str(r.get("season_type", "")).isdigit() else 2
            r["date"] = (r["date"] or "")[:10]  # normalize to calendar date
            rows.append(r)
    rows.sort(key=lambda r: (r["date"] or "", r["event_id"]))
    return rows

def season_of(datestr):
    y = int(datestr[:4]); m = int(datestr[5:7])
    return y + 1 if m >= 8 else y

class Ratings:
    """Point-in-time team ratings keyed by stable teamId. Priors: S-1 finals only."""
    def __init__(self):
        self.hist = defaultdict(lambda: defaultdict(list))   # (season, teamId) -> feat -> values
        self.closed = {}          # season -> {"teams": teamId -> feat avg, "league": feat avg}
        self.current_season = None
    def _close_season(self, season):
        per_team = defaultdict(lambda: defaultdict(list))
        league = defaultdict(list)
        for (s, t), d in self.hist.items():
            if s != season: continue
            for f, vals in d.items():
                per_team[t][f].extend(vals); league[f].extend(vals)
        if not league.get("off_eff"):
            return  # season with no games in memory stays UNRECORDED; prior() then returns None
        lmean = {f: (sum(v) / len(v) if v else 0.0) for f in FEATS for v in [league[f]]}
        self.closed[season] = {
            "league": lmean,
            "teams": {t: {f: (sum(d[f]) / len(d[f]) if d[f] else lmean[f]) for f in FEATS}
                      for t, d in per_team.items()}}
    def _maybe_advance(self, season):
        if self.current_season is None:
            self.current_season = season
        while self.current_season < season:
            self._close_season(self.current_season)
            self.current_season += 1
    def prior(self, season, team_id):
        """Immediately preceding completed season only; None when unavailable."""
        prev = self.closed.get(season - 1)
        if prev is None: return None
        return prev["teams"].get(team_id) or dict(prev["league"])
    def snapshot(self, season, team_id):
        h = self.hist[(season, team_id)]
        pr = self.prior(season, team_id)
        out = {}
        for f in FEATS:
            vals = h.get(f, [])
            if vals and pr is not None:
                out[f] = (sum(vals) + PRIOR_GAMES_EQ * pr[f]) / (len(vals) + PRIOR_GAMES_EQ)
            elif vals:
                out[f] = sum(vals) / len(vals)
            elif pr is not None:
                out[f] = pr[f]
            else:
                out[f] = None
        out["n"] = len(h.get("off_eff", []))
        return out
    def update(self, season, team_id, row):
        self._maybe_advance(season)
        for f in FEATS:
            if row[f] is not None:
                self.hist[(season, team_id)][f].append(row[f])

def pair_games(rows):
    by_ev = defaultdict(dict)
    dropped_dup = 0
    for r in rows:
        ev, side = r["event_id"], r["side"]
        if side in by_ev[ev]:
            by_ev[ev]["_dup"] = True  # duplicate event-side: mark whole event unusable
            dropped_dup += 1
        else:
            by_ev[ev][side] = r
    games = [(d["home"], d["away"]) for ev, d in by_ev.items()
             if "_dup" not in d and "home" in d and "away" in d and d["home"]["score"] is not None]
    games.sort(key=lambda g: (g[0]["date"] or "", g[0]["event_id"]))
    return games, dropped_dup

def build_stream(games, min_games=0):
    """Chronological pass with SAME-DATE ATOMICITY: all games on a date are featurized
    before any of them updates ratings. A game can never consume a same-day result, so
    kickoff order vs completion order is irrelevant (REVIEW: normalized-date rule)."""
    ratings = Ratings()
    out = []
    by_date = defaultdict(list)
    for g in games:
        by_date[g[0]["date"]].append(g)
    for date in sorted(by_date):
        day = by_date[date]
        pending = []
        for home, away in day:
            season = season_of(home["date"])
            ratings._maybe_advance(season)
            hs = ratings.snapshot(season, home["teamId"]); as_ = ratings.snapshot(season, away["teamId"])
            if min(hs["n"], as_["n"]) >= min_games and all(
                    hs[f] is not None and as_[f] is not None for f in FEATS):
                x = [hs[f] - as_[f] for f in FEATS]
                x.append(0.0 if home["neutral"] else 1.0)
                out.append({"date": home["date"], "x": x, "y": home["score"] - away["score"],
                            "homeId": home["teamId"], "awayId": away["teamId"], "season": season,
                            "season_type": home.get("season_type", 2)})
            pending.append((season, home, away))
        for season, home, away in pending:  # updates only after the whole date is featurized
            ratings.update(season, home["teamId"], home)
            ratings.update(season, away["teamId"], away)
    return out

def ridge_fit(X, Y, lam=10.0):
    n = len(X); p = len(X[0]) + 1
    Xb = [[1.0] + x for x in X]
    A = [[sum(Xb[i][a] * Xb[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    for a in range(1, p): A[a][a] += lam
    v = [sum(Xb[i][a] * Y[i] for i in range(n)) for a in range(p)]
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(A[r][c]))
        A[c], A[piv] = A[piv], A[c]; v[c], v[piv] = v[piv], v[c]
        pv = A[c][c]
        if abs(pv) < 1e-12: continue
        for r in range(p):
            if r == c: continue
            f = A[r][c] / pv
            for k in range(c, p): A[r][k] -= f * A[c][k]
            v[r] -= f * v[c]
    return [v[a] / A[a][a] if abs(A[a][a]) > 1e-12 else 0.0 for a in range(p)]

def predict(beta, x): return beta[0] + sum(b * a for b, a in zip(beta[1:], x))

def resid_sigma(beta, rows):
    """Frozen spread from a designated residual set (fit window only, never eval rows)."""
    if not rows: return None
    e = [predict(beta, r["x"]) - r["y"] for r in rows]
    return math.sqrt(sum(v * v for v in e) / len(e))

def evaluate(beta, rows, sigma):
    """sigma must be pre-frozen on fit-window residuals. Nothing is fit on rows here."""
    if not rows: return {"n": 0}
    Y = [r["y"] for r in rows]; yh = [predict(beta, r["x"]) for r in rows]
    n = len(Y)
    out = {"n": n,
           "mae": round(sum(abs(a - b) for a, b in zip(yh, Y)) / n, 3),
           "rmse": round(math.sqrt(sum((a - b) ** 2 for a, b in zip(yh, Y)) / n), 3),
           "home_win_acc": round(sum(1 for m, y in zip(yh, Y) if (m > 0) == (y > 0)) / n, 4)}
    if sigma:
        def phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
        out["brier"] = round(sum((phi(m / sigma) - (1.0 if y > 0 else 0.0)) ** 2
                                 for m, y in zip(yh, Y)) / n, 4)
    return out

def run(paths, eval_start, eval_end="9999-12-31", unlock_final_test=False):
    rows = load(paths)
    protected = [r for r in rows if season_of(r["date"]) == 2026 and r["season_type"] == 3]
    if protected and not unlock_final_test:
        rows = [r for r in rows if not (season_of(r["date"]) == 2026 and r["season_type"] == 3)]
    elif protected and unlock_final_test:
        return {"error": "FINAL TEST GATE: refusing to run. The 2026 postseason is the reserved final test; removing it from this invocation is mandatory."}
    games, dropped_dup = pair_games(rows)
    stream = build_stream(games)
    train = [r for r in stream if r["date"] < eval_start]
    test = [r for r in stream if eval_start <= r["date"] < eval_end]
    if not train: return {"error": "no train rows before eval_start"}
    beta = ridge_fit([r["x"] for r in train], [r["y"] for r in train])
    sigma = resid_sigma(beta, train)
    res = evaluate(beta, test, sigma)
    zero_beta = [0.0] * (len(FEATS) + 1)
    res["baseline_zero"] = evaluate(zero_beta, test, sigma)
    home_mean = sum(r["y"] for r in train) / len(train)
    hm_beta = [home_mean] + [0.0] * len(FEATS)
    res["baseline_home_mean"] = evaluate(hm_beta, test, sigma)
    res["segments"] = {
        "regular": evaluate(beta, [r for r in test if r["date"] and season_of(r["date"]) and r.get("season_type", 2) == 2], sigma),
        "postseason": evaluate(beta, [r for r in test if r.get("season_type", 2) == 3], sigma)}
    return {"features": FEATS + ["home_ind"], "coef": [round(b, 4) for b in beta],
            "train_n": len(train), "eval_start": eval_start, "eval_end": eval_end,
            "dropped_duplicate_event_sides": dropped_dup,
            "protected_rows_excluded": len(protected),
            "sigma_frozen_from_train": round(sigma, 3) if sigma else None, "test": res}

if __name__ == "__main__":
    args = []
    eval_start = "2026-11-01"
    eval_end = "9999-12-31"
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--eval-start":
            eval_start = sys.argv[i + 1]; i += 2
        elif a == "--eval-end":
            eval_end = sys.argv[i + 1]; i += 2
        else:
            args.append(a); i += 1
    print(json.dumps(run(args, eval_start, eval_end), indent=1))
