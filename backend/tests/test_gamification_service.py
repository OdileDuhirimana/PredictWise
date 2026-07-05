"""Pure unit tests for services/gamification_service.py — no Flask app, no
database, no ORM. Uses a plain stand-in object instead of the real
Gamification model to prove the function has no SQLAlchemy dependency.
"""
from types import SimpleNamespace

from backend.services.gamification_service import MAX_STREAK, apply_award


def _gamification(xp=0, streak=0, badges=""):
    return SimpleNamespace(xp=xp, streak=streak, badges=badges)


class TestApplyAward:
    def test_xp_accumulates(self):
        g = _gamification(xp=10)
        apply_award(g, xp=5, badge=None)
        assert g.xp == 15

    def test_streak_increments_by_one_per_award(self):
        g = _gamification(streak=3)
        apply_award(g, xp=1, badge=None)
        assert g.streak == 4

    def test_streak_is_capped_at_max_streak(self):
        g = _gamification(streak=MAX_STREAK)
        apply_award(g, xp=1, badge=None)
        assert g.streak == MAX_STREAK

    def test_new_badge_is_appended(self):
        g = _gamification(badges="Starter")
        apply_award(g, xp=1, badge="Achiever")
        assert g.badges == "Starter,Achiever"

    def test_duplicate_badge_is_not_appended_twice(self):
        g = _gamification(badges="Starter")
        apply_award(g, xp=1, badge="Starter")
        assert g.badges == "Starter"

    def test_no_badge_leaves_badges_unchanged(self):
        g = _gamification(badges="Starter")
        apply_award(g, xp=1, badge=None)
        assert g.badges == "Starter"

    def test_first_badge_on_empty_string(self):
        g = _gamification(badges="")
        apply_award(g, xp=1, badge="Starter")
        assert g.badges == "Starter"
