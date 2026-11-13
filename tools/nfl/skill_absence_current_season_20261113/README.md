# Limited experimental NFL skill-Out correction

This separate overlay preserves the November13 core, original seals and QB scenario. It is an observational correction, not a causal injury effect or proof of improved accuracy.

Deployment uses the reviewed four-decimal coefficient CSV: b=-7.0800, SE5.2005. The correction is b times home-minus-away included trailing share, added to the raw current core home margin. No intercept, season term, QB or undesignated term is applied. No scalar attenuation or QB-scenario stacking.

Established means at least2 earlier stat-row appearances and at least2% of team attempts+carries+receptions. Shares use same-season completed REG games strictly before the cutoff. All production rows, including zero-touch rows, count as appearances in2026. Stable GSIS IDs, exact names, positions and team are checked against the original core production file. Baselines/shares/deltas remain unrounded until half-point headline display.

Only three source-confirmed same-week Out players are included: NE Henderson, TEN Tate, NO Donaldson. Source URLs and captured check time travel with the artifact. MIN-GB is wholly withheld because Jacobs's owning page is unspecified while the Vikings opponent table saysOut; no one-sided Hockenson-only number. SF-DAL is withheld, not zero. Other effects are unknown/outside scope.

The coefficient-only95% band crosses zero for every correction. Corrected-home bands are not full predictive intervals and need not themselves cross zero. Status, role, replacement and confounding uncertainty are excluded. Continuing absences and replacement production are mixed into the core reference, not a healthy-roster baseline; this contract cannot guarantee removal of individual-game double counting.

`apply.py` rebuilds this dated bounded overlay from core data and source-verified event records. `review_sources` preserves the coefficient and current football input bundle; this is not a portable end-to-end historical fit. Do not run a dated rebuild as a fresh status check. New weeks/cutoffs require current source and event-contract checks first.
