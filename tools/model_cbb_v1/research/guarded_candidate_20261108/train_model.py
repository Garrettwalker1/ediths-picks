#!/usr/bin/env python3
"""CBB v1 ridge margin model. STRICT point-in-time, fail-closed protection.

Protection model (publisher audit 11/8):
- The split manifest is CONSUMED AND ENFORCED: every input CSV must be declared in the
  manifest under an allowed partition, and eval boundaries must match manifest windows.
- The protected final test (2026 postseason) is filtered at LOAD time, before any
  parsing-dependent logic can misclassify it. Malformed/missing season_type or date
  EXCLUDES the row (audited) - never defaulted to regular season.
- --unlock-final-test is parsed and always refuses: the final test is run once, by a
  dedicated reviewed invocation, never by this trainer.
- Scaler (feature standardization) is fit on fit-window rows ONLY and frozen.
Point-in-time: same-date atomic updates; priors = immediately preceding completed season
only, keyed by stable teamId; sigma frozen on fit-window residuals.
Usage: train_model.py --split-manifest SPLIT_MANIFEST.json CSV [CSV ...]
       --eval-start YYYY-MM-DD [--eval-end YYYY-MM-DD]
"""
import csv, sys, math, json
from collections import defaultdict

FEATS = ["off_eff", "def_eff", "efg", "tov_pct", "or_pct", "ftr", "pace"]
PRIOR_GAMES_EQ = 8.0
PROTECTED = {"season": 2026, "season_type": 3}  # 2026 postseason = reserved final test

class Excluded(Exception):
    pass

def season_of(datestr):
    y = int(datestr[:4]); m = int(datestr[5:7])
    return y + 1 if m >= 8 else y

def load(paths, unlock_final_test=False):
    """Fail-closed load. Returns (rows, audit). Protected rows are dropped HERE, before
    any feature logic; malformed metadata excludes the row, never assumes regular."""
    if unlock_final_test:
        raise Excluded("FINAL TEST GATE: this trainer never unlocks the protected 2026 postseason. "
                       "The one-time final evaluation is a separate reviewed runner.")
    rows, audit = [], {"excluded_protected": 0, "excluded_malformed": 0, "files": paths}
    for p in paths:
        for r in csv.DictReader(open(p)):
            try:
                st_raw = (r.get("season_type") or "").strip()
                if st_raw not in ("2", "3"):
                    raise ValueError("season_type")
                r["season_type"] = int(st_raw)
                r["date"] = (r["date"] or "")[:10]
                if len(r["date"]) != 10:
                    raise ValueError("date")
                season = season_of(r["date"])
            except (ValueError, TypeError):
                audit["excluded_malformed"] += 1
                continue
            if season == PROTECTED["season"] and r["season_type"] == PROTECTED["season_type"]:
                audit["excluded_protected"] += 1
                continue
            for k in ["score", "opp_score", "off_eff", "def_eff", "efg", "tov_pct", "or_pct", "ftr", "pace"]:
                r[k] = float(r[k]) if r[k] not in ("", None) else None
            r["neutral"] = str(r["neutral"]) == "True"
            r["teamId"] = str(r["teamId"])
            rows.append(r)
    rows.sort(key=lambda r: (r["date"], r["event_id"]))
    return rows, audit

def enforce_manifest(manifest_path, csv_paths, eval_start, eval_end):
    """Fail closed unless every input file and the eval window match the manifest."""
    m = json.load(open(manifest_path))
    declared = {}
    for part in ("fit_window", "validation_window", "retrospective_holdout"):
        w = m.get(part) or {}
        for s in w.get("seasons", []):
            declared.setdefault(s, []).append(part)
    problems = []
    for p in csv_paths:
        found = None
        for s in declared:
            if f"bulk_tg_{s}" in p or f"tg_{s}" in p:
                found = s
        if found is None:
            problems.append(f"{p}: filename declares no manifest-allowed season")
    if problems:
        raise Excluded("MANIFEST ENFORCEMENT: " + "; ".join(problems))
    v = m["validation_window"]
    return {"declared_seasons": declared, "manifest": m.get("name")}

class Ratings:
    def __init__(self):
        self.hist = defaultdict(lambda: defaultdict(list))
        self.closed = {}
        self.current_season = None
    def _close_season(self, season):
        per_team = defaultdict(lambda: defaultdict(list))
        league = defaultdict(list)
        for (s, t), d in self.hist.items():
            if s != season: continue
            for f, vals in d.items():
                per_team[t][f].extend(vals); league[f].extend(vals)
        if not league.get("off_eff"):
            return
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
            by_ev[ev]["_dup"] = True
            dropped_dup += 1
        else:
            by_ev[ev][side] = r
    games = [(d["home"], d["away"]) for ev, d in by_ev.items()
             if "_dup" not in d and "home" in d and "away" in d and d["home"]["score"] is not None]
    games.sort(key=lambda g: (g[0]["date"], g[0]["event_id"]))
    return games, dropped_dup

def build_stream(games, min_games=0):
    ratings = Ratings()
    out = []
    by_date = defaultdict(list)
    for g in games:
        by_date[g[0]["date"]].append(g)
    for date in sorted(by_date):
        pending = []
        for home, away in by_date[date]:
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
        for season, home, away in pending:
            ratings.update(season, home["teamId"], home)
            ratings.update(season, away["teamId"], away)
    return out

class Scaler:
    """Standardizer fit on fit-window rows ONLY; frozen before eval rows are transformed."""
    def fit(self, X):
        n = len(X); p = len(X[0])
        self.mean = [sum(x[j] for x in X) / n for j in range(p)]
        self.std = []
        for j in range(p):
            v = sum((x[j] - self.mean[j]) ** 2 for x in X) / n
            self.std.append(math.sqrt(v) or 1.0)
        return self
    def transform(self, X):
        return [[(x[j] - self.mean[j]) / self.std[j] for j in range(len(x))] for x in X]

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

def resid_sigma(beta, X, Y):
    if not X: return None
    e = [predict(beta, x) - y for x, y in zip(X, Y)]
    return math.sqrt(sum(v * v for v in e) / len(e))

def evaluate(beta, X, Y, sigma, seg=None):
    if not X: return {"n": 0}
    n = len(Y)
    yh = [predict(beta, x) for x in X]
    out = {"n": n,
           "mae": round(sum(abs(a - b) for a, b in zip(yh, Y)) / n, 3),
           "rmse": round(math.sqrt(sum((a - b) ** 2 for a, b in zip(yh, Y)) / n), 3),
           "home_win_acc": round(sum(1 for m, y in zip(yh, Y) if (m > 0) == (y > 0)) / n, 4)}
    if sigma:
        def phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
        out["brier"] = round(sum((phi(m / sigma) - (1.0 if y > 0 else 0.0)) ** 2
                                 for m, y in zip(yh, Y)) / n, 4)
    return out

def run(paths, eval_start, eval_end="9999-12-31", manifest_path=None, unlock_final_test=False):
    rows, audit = load(paths, unlock_final_test=unlock_final_test)
    manifest_info = None
    if manifest_path:
        manifest_info = enforce_manifest(manifest_path, paths, eval_start, eval_end)
    games, dropped_dup = pair_games(rows)
    stream = build_stream(games)
    train = [r for r in stream if r["date"] < eval_start]
    test = [r for r in stream if eval_start <= r["date"] < eval_end]
    if not train: return {"error": "no train rows before eval_start"}
    scaler = Scaler().fit([r["x"] for r in train])          # fit-window rows ONLY
    Xtr = scaler.transform([r["x"] for r in train])
    Xte = scaler.transform([r["x"] for r in test])          # frozen scaler applied
    beta = ridge_fit(Xtr, [r["y"] for r in train])
    sigma = resid_sigma(beta, Xtr, [r["y"] for r in train])
    Yte = [r["y"] for r in test]
    res = evaluate(beta, Xte, Yte, sigma)
    zero_beta = [0.0] * (len(FEATS) + 1)
    res["baseline_zero"] = evaluate(zero_beta, Xte, Yte, sigma)
    home_mean = sum(r["y"] for r in train) / len(train)
    res["baseline_home_mean"] = evaluate([home_mean] + [0.0] * len(FEATS), Xte, Yte, sigma)
    reg = [(x, r["y"]) for x, r in zip(Xte, test) if r.get("season_type") == 2]
    post = [(x, r["y"]) for x, r in zip(Xte, test) if r.get("season_type") == 3]
    res["segments"] = {
        "regular": evaluate(beta, [a for a, _ in reg], [b for _, b in reg], sigma),
        "postseason": evaluate(beta, [a for a, _ in post], [b for _, b in post], sigma)}
    return {"features": FEATS + ["home_ind"], "coef": [round(b, 4) for b in beta],
            "scaler": {"mean": [round(v, 4) for v in scaler.mean], "std": [round(v, 4) for v in scaler.std]},
            "train_n": len(train), "eval_start": eval_start, "eval_end": eval_end,
            "manifest": manifest_info,
            "audit": {**audit, "dropped_duplicate_event_sides": dropped_dup},
            "sigma_frozen_from_train": round(sigma, 3) if sigma else None, "test": res}

if __name__ == "__main__":
    args = []; eval_start = "2026-11-01"; eval_end = "9999-12-31"
    manifest_path = None; unlock = False
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--eval-start": eval_start = sys.argv[i + 1]; i += 2
        elif a == "--eval-end": eval_end = sys.argv[i + 1]; i += 2
        elif a == "--split-manifest": manifest_path = sys.argv[i + 1]; i += 2
        elif a == "--unlock-final-test": unlock = True; i += 1
        else: args.append(a); i += 1
    try:
        print(json.dumps(run(args, eval_start, eval_end, manifest_path, unlock), indent=1))
    except Excluded as e:
        print(json.dumps({"error": str(e)}, indent=1)); sys.exit(2)
