"""Pure unit tests for services/risk_service.py — no Flask app, no
database, no HTTP client. This is exactly the kind of test the audit
noted was missing: "no service layer for true unit isolation of business
rules."
"""
from backend.services.risk_service import (
    RISK_HIGH_RISK,
    RISK_NEEDS_ATTENTION,
    RISK_ON_TRACK,
    classify_risk,
)


class TestClassifyRisk:
    def test_high_pass_prob_and_score_is_on_track(self):
        assert classify_risk(pass_prob=0.9, predicted_score=85) == RISK_ON_TRACK

    def test_low_pass_prob_alone_is_high_risk(self):
        assert classify_risk(pass_prob=0.3, predicted_score=90) == RISK_HIGH_RISK

    def test_low_score_alone_is_high_risk(self):
        assert classify_risk(pass_prob=0.95, predicted_score=40) == RISK_HIGH_RISK

    def test_mid_range_is_needs_attention(self):
        assert classify_risk(pass_prob=0.6, predicted_score=70) == RISK_NEEDS_ATTENTION

    def test_boundary_at_high_risk_threshold_is_not_yet_high_risk(self):
        # pass_prob == 0.5 and score == 50 are the thresholds themselves;
        # the rule is strictly "<", so equality should not trigger High Risk.
        assert classify_risk(pass_prob=0.5, predicted_score=50) != RISK_HIGH_RISK

    def test_boundary_at_needs_attention_threshold_is_on_track(self):
        assert classify_risk(pass_prob=0.7, predicted_score=65) == RISK_ON_TRACK
