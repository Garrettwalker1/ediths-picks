# CFB moneyline gate notes

- 2026-09-09: two independent routes to a CFB moneyline model were tested against the frozen benchmark game sets (749 FBS-vs-FBS games in the 2024 holdout, 761 in the 2025 holdout, 10,000 game-level bootstrap resamples, seed locked). Both **beat Elo decisively** and both **lose decisively to the closing-spread-derived win-probability proxy** in each year separately. Verdict per the frozen promotion rule: **descriptive_failed_close - NOT shipped.** Fourth CFB approach to lose to the market price (spread, totals, h2h moneyline, margin-derived moneyline).

## Route 1: cfb_h2h_v1 (direct win-probability model)
- Frozen spec 2026-09-02: `tools/test/1-cfb_h2h_spec_v1.md` (+ sha256 lock). Dynamic Elo + exponentially weighted team form + home/neutral/rest + week term; L2 logistic; calibration chosen on development out-of-fold only. Sequential holdouts 2024 and 2025.
- Frozen verdict (2026-09-02): `descriptive_failed_close` - beats the locked Elo baseline in both years, loses decisively to the closing-spread-derived probability benchmark in both years. Primary benchmark (closing no-vig moneyline) was not available at sufficient free coverage, so the closing-spread proxy was used and labeled the weaker proxy per the spec.

## Route 2: v2.1 margin -> win probability (built/tested 2026-09-09)
- Method: the validated v2.1 margin model (the one driving the Week 2 board), ridge retrained on 2020-2023; margin-to-win-prob logistic mapping fit on cross-fitted (leave-one-season-out) training-era predictions only; scored on the untouched 2024 and 2025 holdouts joined to the frozen h2h benchmark game set. No holdout calibration. Sanity check reproduced the v2.1 locked-test MAE exactly (12.940), so the pipeline is faithful.

### 2024 holdout (n=749)
| model | log loss | Brier | winner acc |
|---|---|---|---|
| v2.1->ML | 0.5846 | 0.2007 | 69.0% |
| Elo | 0.6265 | 0.2183 | 64.0% |
| closing-spread proxy | 0.5340 | 0.1810 | 71.6% |

- vs Elo: **beats it, settled** - 99.9% of bootstrap resamples better on both metrics (log-loss delta CI95 [-0.067, -0.016], Brier delta CI95 [-0.028, -0.007]).
- vs closing-spread proxy: **loses decisively** - 0.0% of resamples better (log-loss delta CI95 [+0.028, +0.074], Brier delta CI95 [+0.011, +0.029]).
- Calibration: slope 0.95, intercept 0.04 - well calibrated, just less sharp than the market.

### 2025 holdout (n=761)
| model | log loss | Brier | winner acc |
|---|---|---|---|
| v2.1->ML | 0.5681 | 0.1939 | 71.0% |
| Elo | 0.6097 | 0.2100 | 67.9% |
| closing-spread proxy | 0.5245 | 0.1777 | 72.9% |

- vs Elo: **beats it, settled** - 100.0% / 99.9% of resamples better (log-loss delta CI95 [-0.065, -0.018], Brier delta CI95 [-0.026, -0.006]).
- vs closing-spread proxy: **loses decisively** - 0.0% of resamples better (log-loss delta CI95 [+0.024, +0.063], Brier delta CI95 [+0.008, +0.024]).
- Calibration: slope 1.08, intercept 0.08.

## Consequences
- Moneyline stays off the boards, same as totals (2026-09-06 verdict). The model families keep failing to beat the market price; the dashboard remains measurement/comparison, never a pick.
- A "model fair ML" column would be a monotone re-expression of the model margin already shown - it adds no information beyond the spread gap and is not shipped, per the same rule.
- Eval pipeline lives in the build agent's sandbox (/tmp/ml_eval.py, /tmp/ml_eval_joined.csv, transient). Metrics above are the frozen record.
