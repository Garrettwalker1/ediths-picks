#!/usr/bin/env python3
"""CBB v1 ridge margin model. Fail-closed, manifest-enforced, point-in-time.

Contract (publisher adversarial review 11/8):
- --split-manifest is MANDATORY. Windows come ONLY from the manifest; no CLI date args.
- Before ANY file is opened: every input path must be declared in manifest inputs with a
  matching sha256 and a partition whose seasons/types/dates are allowed; anything else
  (including renamed copies, undeclared seasons, protected-set files) is rejected unread.
- During parse, every ROW is checked against its file's declared partition (season,
  season_type, date range); violations exclude the row with audit counts. A row matching
  the PROTECTED set (2026 postseason) aborts the whole run - inputs must never contain it.
- --unlock-final-test is parsed and ALWAYS refuses (exit 2).
- Coefficients, scaler, sigma, and Platt calibration fit on fit-window rows ONLY.
- Same-date atomic updates; priors = immediately preceding completed season, stable IDs.
Usage: train_model.py --split-manifest M.json [--d1-only] CSV [CSV ...]
"""
import csv, sys, math, json, hashlib, os
from collections import defaultdict

FEATS = ["off_eff", "def_eff", "efg", "tov_pct", "or_pct", "ftr", "pace"]
PRIOR_GAMES_EQ = 8.0

class Excluded(Exception):
    pass

def season_of(datestr):
    y = int(datestr[:4]); m = int(datestr[5:7])
    return y + 1 if m >= 8 else y

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_manifest(path):
    m = json.load(open(path))
    for k in ("partitions", "protected", "inputs", "eval"):
        if k not in m: raise Excluded(f"manifest missing {k}")
    return m

def admit_files(manifest, paths):
    """Pre-parse admission: exact path + hash + partition. Nothing undeclared is opened."""
    admitted = []
    for p in paths:
        entry = manifest["inputs"].get(p)
        if entry is None:
            raise Excluded(f"MANIFEST: {p} not declared in inputs (renamed/undeclared files rejected unread)")
        if entry.get("sha256") != sha256_file(p):
            raise Excluded(f"MANIFEST: {p} hash mismatch (file changed since freeze)")
        part = manifest["partitions"].get(entry.get("partition"))
        if part is None:
            raise Excluded(f"MANIFEST: {p} declares unknown partition {entry.get('partition')}")
        admitted.append((p, entry["partition"], part))
    return admitted

def load_admitted(admitted, protected, d1_only=False):
    """Row-level partition enforcement. Protected rows ABORT the run."""
    rows, audit = [], {"excluded_out_of_partition": 0, "excluded_malformed": 0,
                       "excluded_non_d1": 0, "files": [a[0] for a in admitted]}
    for path, part_name, part in admitted:
        for r in csv.DictReader(open(path)):
            try:
                st = (r.get("season_type") or "").strip()
                if st not in ("2", "3"): raise ValueError("season_type")
                r["season_type"] = int(st)
                r["date"] = (r["date"] or "")[:10]
                if len(r["date"]) != 10: raise ValueError("date")
                season = season_of(r["date"])
            except (ValueError, TypeError):
                audit["excluded_malformed"] += 1
                continue
            if season in protected["seasons"] and r["season_type"] in protected["season_types"]:
                raise Excluded(f"PROTECTED ROW IN INPUT: {path} contains a {season} postseason row "
                               f"(event {r.get('event_id')}). Protected inputs must never reach the trainer.")
            if (season not in part["seasons"] or r["season_type"] not in part["season_types"]
                    or not (part["date_range"][0] <= r["date"] <= part["date_range"][1])):
                audit["excluded_out_of_partition"] += 1
                continue
            if d1_only and str(r.get("d1_game")) != "True":
                audit["excluded_non_d1"] += 1
                continue
            for k in ["score", "opp_score", "off_eff", "def_eff", "efg", "tov_pct", "or_pct", "ftr", "pace"]:
                r[k] = float(r[k]) if r[k] not in ("", None) else None
            r["neutral"] = str(r["neutral"]) == "True"
            r["teamId"] = str(r["teamId"])
            rows.append(r)
    rows.sort(key=lambda r: (r["date"], r["event_id"]))
    return rows, audit

class Ratings:
    def __init__(self):
        self.hist = defaultdict(lambda: defaultdict(list))
        self.closed = {}
        self.current_season = None
    def _close_season(self, season):
        per_team = defaultdict(lambda: defaultdict(list)); league = defaultdict(list)
        for (s, t), d in self.hist.items():
            if s != season: continue
            for f, vals in d.items():
                per_team[t][f].extend(vals); league[f].extend(vals)
        if not league.get("off_eff"): return
        lmean = {f: (sum(v) / len(v) if v else 0.0) for f in FEATS for v in [league[f]]}
        self.closed[season] = {"league": lmean,
            "teams": {t: {f: (sum(d[f]) / len(d[f]) if d[f] else lmean[f]) for f in FEATS}
                      for t, d in per_team.items()}}
    def _maybe_advance(self, season):
        if self.current_season is None: self.current_season = season
        while self.current_season < season:
            self._close_season(self.current_season); self.current_season += 1
    def prior(self, season, team_id):
        prev = self.closed.get(season - 1)
        if prev is None: return None
        return prev["teams"].get(team_id) or dict(prev["league"])
    def snapshot(self, season, team_id):
        h = self.hist[(season, team_id)]; pr = self.prior(season, team_id); out = {}
        for f in FEATS:
            vals = h.get(f, [])
            if vals and pr is not None: out[f] = (sum(vals) + PRIOR_GAMES_EQ * pr[f]) / (len(vals) + PRIOR_GAMES_EQ)
            elif vals: out[f] = sum(vals) / len(vals)
            elif pr is not None: out[f] = pr[f]
            else: out[f] = None
        out["n"] = len(h.get("off_eff", []))
        return out
    def update(self, season, team_id, row):
        self._maybe_advance(season)
        for f in FEATS:
            if row[f] is not None: self.hist[(season, team_id)][f].append(row[f])

def pair_games(rows):
    by_ev = defaultdict(dict); dropped_dup = 0
    for r in rows:
        ev, side = r["event_id"], r["side"]
        if side in by_ev[ev]: by_ev[ev]["_dup"] = True; dropped_dup += 1
        else: by_ev[ev][side] = r
    games = [(d["home"], d["away"]) for ev, d in by_ev.items()
             if "_dup" not in d and "home" in d and "away" in d and d["home"]["score"] is not None]
    games.sort(key=lambda g: (g[0]["date"], g[0]["event_id"]))
    return games, dropped_dup

def build_stream(games, min_games=0):
    ratings = Ratings(); out = []
    by_date = defaultdict(list)
    for g in games: by_date[g[0]["date"]].append(g)
    for date in sorted(by_date):
        pending = []
        for home, away in by_date[date]:
            season = season_of(home["date"]); ratings._maybe_advance(season)
            hs = ratings.snapshot(season, home["teamId"]); as_ = ratings.snapshot(season, away["teamId"])
            if min(hs["n"], as_["n"]) >= min_games and all(
                    hs[f] is not None and as_[f] is not None for f in FEATS):
                x = [hs[f] - as_[f] for f in FEATS]; x.append(0.0 if home["neutral"] else 1.0)
                out.append({"date": home["date"], "x": x, "y": home["score"] - away["score"],
                            "homeId": home["teamId"], "awayId": away["teamId"], "season": season,
                            "season_type": home.get("season_type", 2)})
            pending.append((season, home, away))
        for season, home, away in pending:
            ratings.update(season, home["teamId"], home); ratings.update(season, away["teamId"], away)
    return out

class Scaler:
    def fit(self, X):
        n = len(X); p = len(X[0])
        self.mean = [sum(x[j] for x in X) / n for j in range(p)]
        self.std = [math.sqrt(sum((x[j] - self.mean[j]) ** 2 for x in X) / n) or 1.0 for j in range(p)]
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

def platt_fit(beta, X, Y, sigma, iters=200, lr=0.05):
    """Platt scaling on fit-window rows ONLY: p = sigmoid(a*z + b), z = margin/sigma."""
    z = [predict(beta, x) / sigma for x in X]
    t = [1.0 if y > 0 else 0.0 for y in Y]
    a, b = 1.0, 0.0
    for _ in range(iters):
        ga = gb = 0.0
        for zi, ti in zip(z, t):
            p = 1.0 / (1.0 + math.exp(-(a * zi + b)))
            ga += (p - ti) * zi; gb += (p - ti)
        a -= lr * ga / len(z); b -= lr * gb / len(z)
    return {"a": a, "b": b}

def platt_p(cal, margin, sigma):
    return 1.0 / (1.0 + math.exp(-(cal["a"] * (margin / sigma) + cal["b"])))

def brier(ps, Y):
    return sum((p - (1.0 if y > 0 else 0.0)) ** 2 for p, y in zip(ps, Y)) / len(Y)

def reliability(ps, Y, bins=10):
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        idx = [j for j, p in enumerate(ps) if lo <= p < hi or (i == bins - 1 and p == 1.0)]
        if not idx: continue
        out.append({"bin": [round(lo, 2), round(hi, 2)], "n": len(idx),
                    "mean_pred": round(sum(ps[j] for j in idx) / len(idx), 4),
                    "empirical": round(sum(1.0 if Y[j] > 0 else 0.0 for j in idx) / len(idx), 4)})
    return out

def margin_metrics(beta, X, Y):
    if not X: return {"n": 0}
    yh = [predict(beta, x) for x in X]; n = len(Y)
    return {"n": n, "mae": round(sum(abs(a - b) for a, b in zip(yh, Y)) / n, 3),
            "rmse": round(math.sqrt(sum((a - b) ** 2 for a, b in zip(yh, Y)) / n), 3),
            "win_acc": round(sum(1 for m, y in zip(yh, Y) if (m > 0) == (y > 0)) / n, 4)}

def run(paths, manifest_path, d1_only=False, unlock_final_test=False):
    if unlock_final_test:
        raise Excluded("FINAL TEST GATE: this trainer never unlocks the protected set. "
                       "The one-time final evaluation is a separate reviewed runner.")
    m = load_manifest(manifest_path)
    admitted = admit_files(m, paths)
    rows, audit = load_admitted(admitted, m["protected"], d1_only=d1_only)
    games, dropped_dup = pair_games(rows)
    stream = build_stream(games)
    fit_seasons = set()
    for pn in m["eval"]["fit_partitions"]: fit_seasons |= set(m["partitions"][pn]["seasons"])
    eval_seasons = set()
    for pn in m["eval"]["eval_partitions"]: eval_seasons |= set(m["partitions"][pn]["seasons"])
    train = [r for r in stream if r["season"] in fit_seasons]
    test = [r for r in stream if r["season"] in eval_seasons]
    if not train: return {"error": "no fit-window rows"}
    scaler = Scaler().fit([r["x"] for r in train])
    Xtr = scaler.transform([r["x"] for r in train]); Ytr = [r["y"] for r in train]
    Xte = scaler.transform([r["x"] for r in test]); Yte = [r["y"] for r in test]
    beta = ridge_fit(Xtr, Ytr)
    sigma = resid_sigma(beta, Xtr, Ytr)
    cal = platt_fit(beta, Xtr, Ytr, sigma)
    pte = [platt_p(cal, predict(beta, x), sigma) for x in Xte]
    ptr = [platt_p(cal, predict(beta, x), sigma) for x in Xtr]
    home_wr = sum(1.0 if y > 0 else 0.0 for y in Ytr) / len(Ytr)
    res = margin_metrics(beta, Xte, Yte)
    res["probability"] = {
        "brier_platt": round(brier(pte, Yte), 4),
        "brier_constant_home_rate": round(brier([home_wr] * len(Yte), Yte), 4),
        "reliability_validation": reliability(pte, Yte),
        "platt_fit_window_brier": round(brier(ptr, Ytr), 4),
        "note": "Platt a/b and sigma fit on fit window only; reliability is descriptive, not calibration proof"}
    res["baselines"] = {
        "home_mean_margin": {**margin_metrics([sum(Ytr)/len(Ytr)] + [0.0]*len(FEATS), Xte, Yte)},
        "always_away_pick": {"note": "zero-margin predictor picks away every game; its 'accuracy' is the away win rate, NOT a 50% coin flip",
                             "win_acc": round(sum(1 for y in Yte if y < 0) / len(Yte), 4)}}
    reg = [(x, y) for x, y, r in zip(Xte, Yte, test) if r.get("season_type") == 2]
    post = [(x, y) for x, y, r in zip(Xte, Yte, test) if r.get("season_type") == 3]
    res["segments"] = {"regular": margin_metrics(beta, [a for a, _ in reg], [b for _, b in reg]),
                       "postseason": margin_metrics(beta, [a for a, _ in post], [b for _, b in post])}
    return {"features": FEATS + ["home_ind"], "coef": [round(b, 4) for b in beta],
            "scaler_mean": [round(v, 4) for v in scaler.mean], "scaler_std": [round(v, 4) for v in scaler.std],
            "platt": {k: round(v, 5) for k, v in cal.items()},
            "train_n": len(train), "eval_n": len(test),
            "manifest": m["name"], "d1_only": d1_only,
            "audit": {**audit, "dropped_duplicate_event_sides": dropped_dup},
            "sigma_frozen_from_fit": round(sigma, 3) if sigma else None, "validation": res}

if __name__ == "__main__":
    args = []; manifest_path = None; d1_only = False; unlock = False
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--split-manifest": manifest_path = sys.argv[i + 1]; i += 2
        elif a == "--d1-only": d1_only = True; i += 1
        elif a == "--unlock-final-test": unlock = True; i += 1
        else: args.append(a); i += 1
    if not manifest_path:
        print(json.dumps({"error": "--split-manifest is mandatory; no manifest, no run"})); sys.exit(2)
    try:
        print(json.dumps(run(args, manifest_path, d1_only, unlock), indent=1))
    except Excluded as e:
        print(json.dumps({"error": str(e)}, indent=1)); sys.exit(2)
