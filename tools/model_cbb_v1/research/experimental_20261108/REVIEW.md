# Experimental code review - November 8, 2026

Preserved for research recovery, not production or valid evaluation. Scripts are original experimental versions. Manifest has only a coordination-reference wording cleanup and this warning. Do not use reported smoke results as predictive validation.

Known blocking defects:
- `train_model.py` rolls final priors from all training seasons before constructing any training features. Earlier training games can consume their own/future-season final averages. Snapshot-before-update alone does not prevent this leak.
- `evaluate()` estimates probability sigma from evaluated test residuals. That fits probabilities to test outcomes. Fit variance/calibration on the training/validation window and freeze it before a final test.
- `build_features.py` assigns home/away by boxscore array index. Match team IDs to header competitor `homeAway` instead.
- `Ratings.prior` is keyed by display name, not stable team ID, and is not enforced as immediately preceding season. Season transitions need explicit handling.
- No season-specific D1 membership filter or independent point-in-time audit exists.
- Pull script retries all errors with a short delay and lists at most one GitHub contents page. It is not the recommended bulk-history acquisition route.

No fixes are silently substituted here. Repair and audit before fitting, calibration or held-out evaluation. The smoke sample is partial, and the reported margin MAE loses the home-mean baseline.
