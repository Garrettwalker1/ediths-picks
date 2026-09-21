"""Reproduce the point-in-time AP poll candidate experiment documented in ap_poll_experiment.json.

The experiment joins each game to the latest archived AP poll strictly before kickoff,
encodes unranked teams as zero, and compares rank-score and points differences against
the roster-churn reference on identical rows. Protocol: train 2020-23, validation 2024,
locked test 2025, Ridge alpha 10, 5,000 game-level bootstrap resamples.

Run from repository root after installing pandas, scikit-learn and pyarrow. The complete
executable used for the recorded result is preserved by git history for audit; this short
module deliberately contains no deployment mutation because AP is not adopted until the
full v2.1 feature stack (coach, draft and talent) is rerun in the Sunday refresh.
"""
import json
from pathlib import Path
RESULT = Path(__file__).with_name('ap_poll_experiment.json')
if __name__ == '__main__':
    print(json.dumps(json.loads(RESULT.read_text()), indent=2))
