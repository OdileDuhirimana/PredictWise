"""Unit tests for backend/utils/recommend.py::recommend_study_plan.

Each branch of recommend_study_plan is independently triggerable (High
Risk, low attendance, low average score), and they can combine — so tests
assert the exact set of rec `type`s returned for representative inputs
rather than just "returns something", to catch regressions where a branch
silently stops firing or an extra one appears.
"""
from backend.utils.recommend import recommend_study_plan


def _rec_types(recs):
    return [r["type"] for r in recs]


class TestRecommendStudyPlan:
    def test_high_risk_branch_adds_tutoring_and_revision(self):
        features = {"avg_score": 40, "attendance_rate": 0.95}
        prediction = {"predicted_score": 40, "pass_prob": 0.2}

        recs = recommend_study_plan(features, prediction, risk="High Risk")

        types = _rec_types(recs)
        assert "tutoring" in types
        assert "revision" in types
        # avg_score < 65 also fires the practice branch alongside High Risk.
        assert "practice" in types
        # 'videos' is always appended regardless of risk.
        assert "videos" in types

    def test_low_attendance_branch(self):
        features = {"avg_score": 80, "attendance_rate": 0.70}
        prediction = {"predicted_score": 80, "pass_prob": 0.9}

        recs = recommend_study_plan(features, prediction, risk="On-Track")

        types = _rec_types(recs)
        assert "attendance" in types
        assert "tutoring" not in types  # not High Risk
        assert "practice" not in types  # avg_score >= 65

    def test_low_average_branch(self):
        features = {"avg_score": 55, "attendance_rate": 0.95}
        prediction = {"predicted_score": 55, "pass_prob": 0.6}

        recs = recommend_study_plan(features, prediction, risk="Needs Attention")

        types = _rec_types(recs)
        assert "practice" in types
        assert "tutoring" not in types  # not High Risk
        assert "attendance" not in types  # attendance_rate >= 0.85

    def test_baseline_default_branch_only_adds_videos(self):
        """When risk is On-Track, attendance is healthy, and avg_score is
        high, none of the conditional branches should fire — only the
        unconditional 'videos' recommendation remains."""
        features = {"avg_score": 90, "attendance_rate": 0.98}
        prediction = {"predicted_score": 90, "pass_prob": 0.95}

        recs = recommend_study_plan(features, prediction, risk="On-Track")

        assert _rec_types(recs) == ["videos"]

    def test_missing_features_default_safely(self):
        """recommend_study_plan reads avg_score/attendance_rate via
        features.get(...) with defaults, so an empty features dict must
        not raise. Defaults are avg_score=60 (< 65, so 'practice' fires)
        and attendance_rate=0.9 (healthy, so 'attendance' does not)."""
        recs = recommend_study_plan({}, {}, risk="On-Track")

        assert _rec_types(recs) == ["practice", "videos"]
