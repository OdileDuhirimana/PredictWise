"""Risk-tier classification — pure business logic, no Flask/DB dependency.

Why extracted: this logic previously lived inline inside
routes/ml.py::do_predict as four unnamed magic-number comparisons
(0.5, 50, 0.7, 65). Two problems with that: (1) the thresholds couldn't be
unit-tested without going through a full Flask request/JWT/DB integration
test, and (2) "why 0.5 and not 0.55" had no place to be documented. Naming
the constants and moving the branching into a plain function fixes both —
this is exactly the kind of rule the audit's ARC-01/CODE-06 findings were
about ("business logic lives directly inside route handlers... with no
service/domain layer", "magic values... untouched").
"""
from __future__ import annotations

RISK_ON_TRACK = "On-Track"
RISK_NEEDS_ATTENTION = "Needs Attention"
RISK_HIGH_RISK = "High Risk"

# A student is flagged High Risk if EITHER their predicted pass
# probability or their predicted absolute score falls below these
# thresholds — either signal alone is treated as sufficient, matching the
# original inline `or` logic in routes/ml.py before this extraction.
HIGH_RISK_PASS_PROB_THRESHOLD = 0.5
HIGH_RISK_SCORE_THRESHOLD = 50.0

NEEDS_ATTENTION_PASS_PROB_THRESHOLD = 0.7
NEEDS_ATTENTION_SCORE_THRESHOLD = 65.0


def classify_risk(pass_prob: float, predicted_score: float) -> str:
    """Classifies a single prediction into one of three risk tiers.

    Args:
        pass_prob: model-predicted probability of passing, in [0, 1].
        predicted_score: model-predicted absolute score, typically 0-100.

    Returns:
        One of RISK_HIGH_RISK, RISK_NEEDS_ATTENTION, RISK_ON_TRACK.
    """
    if pass_prob < HIGH_RISK_PASS_PROB_THRESHOLD or predicted_score < HIGH_RISK_SCORE_THRESHOLD:
        return RISK_HIGH_RISK
    if pass_prob < NEEDS_ATTENTION_PASS_PROB_THRESHOLD or predicted_score < NEEDS_ATTENTION_SCORE_THRESHOLD:
        return RISK_NEEDS_ATTENTION
    return RISK_ON_TRACK
