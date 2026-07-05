"""Gamification business rules — pure functions, no Flask/DB dependency.

Why extracted: routes/gamification.py::award() previously mixed request
parsing, this XP/streak/badge math, and the db.session commit lifecycle in
one function body. The only tests exercising the math were full HTTP
integration tests through Flask + a real database — this extraction lets
the actual business rule (how XP/streak/badges combine) be unit-tested in
isolation, and named `MAX_STREAK` replaces the inline magic number `365`.
"""
from __future__ import annotations

from typing import Optional, Protocol


MAX_STREAK = 365


class GamificationLike(Protocol):
    """Structural type for whatever `apply_award` is given — in production
    this is a `models.Gamification` ORM instance, but the function itself
    has no import-time dependency on SQLAlchemy or Flask, which is what
    makes it unit-testable with a plain stand-in object."""

    xp: int
    streak: int
    badges: str


def apply_award(gamification: GamificationLike, xp: int, badge: Optional[str]) -> None:
    """Applies one award to `gamification` in place.

    Mutates the given object's `xp`, `streak`, and `badges` fields
    following the same rules previously inlined in
    routes/gamification.py::award():
      - `xp` accumulates.
      - `streak` increments by 1 per award, capped at `MAX_STREAK`.
      - `badge`, if given and not already present, is appended to the
        comma-separated `badges` string.

    Args:
        gamification: any object with mutable `.xp` (int), `.streak`
            (int), and `.badges` (comma-separated str) attributes.
        xp: non-negative XP to add (validation of non-negativity is the
            caller's responsibility via schemas.AwardRequest — this
            function trusts its input, matching the "validate at the
            boundary, keep the domain function simple" split).
        badge: badge name to award, or None to award XP/streak only.
    """
    gamification.xp += xp
    gamification.streak = min(gamification.streak + 1, MAX_STREAK)
    if badge:
        existing_badges = [b for b in gamification.badges.split(",") if b]
        if badge not in existing_badges:
            existing_badges.append(badge)
        gamification.badges = ",".join(existing_badges)
