"""Pydantic request schemas — single source of truth for input validation.

Why centralize here rather than validating ad-hoc in each route: before this
change, every route pulled fields out of `request.get_json()` with `.get()`
or raw `[...]` indexing, so a missing field either silently became `None`
(propagating bad data into the DB) or raised an unhandled `KeyError` that
surfaced to the client as an opaque 500. Defining one pydantic model per
endpoint gives us: (1) a documented contract for each request body, (2)
consistent 400s with field-level detail instead of 500s, and (3) type
coercion (e.g. numeric strings -> float) handled in one place.

Each route is expected to do:

    try:
        payload = SomeRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid request body', 400, details=exc.errors())

Assumptions:
- Bodies are always JSON objects (routes use `silent=True` so a missing/
  malformed JSON body validates as `{}` and fails schema validation with a
  clear "field required" message instead of throwing on `.get_json()`).
- Numeric bounds (score >= 0, mood 1-10, etc.) reflect the domain rules
  already implied by the model docstrings/comments in models.py.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreateStudentRequest(BaseModel):
    name: str = Field(min_length=1)
    grade: str = Field(min_length=1)
    class_name: Optional[str] = None
    parent_id: Optional[int] = None


class AssignParentRequest(BaseModel):
    """Body for PATCH /students/<id>/parent. `parent_id: null` explicitly
    unlinks the student from any guardian account."""

    parent_id: Optional[int] = None


class AddAssessmentRequest(BaseModel):
    student_id: int
    subject: str = Field(min_length=1)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0, default=100)
    term: str = Field(min_length=1)


class AddAttendanceRequest(BaseModel):
    student_id: int
    date: date
    present: bool = True

    @field_validator("date", mode="before")
    @classmethod
    def _parse_date_string(cls, value):
        # Accept both plain dates ("2025-01-10") and full ISO datetimes
        # ("2025-01-10T00:00:00"), matching the previous manual parsing
        # behavior in students.py before this schema replaced it. Any
        # unparsable string is returned as-is (not raised here) so
        # pydantic's own `date` type validation produces the standard
        # ValidationError/400 envelope instead of an unhandled ValueError
        # propagating up as a 500.
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
            try:
                from datetime import datetime

                return datetime.fromisoformat(value).date()
            except ValueError:
                return value
        return value


class AddSurveyRequest(BaseModel):
    student_id: int
    mood: int = Field(ge=1, le=10, default=5)
    stress: int = Field(ge=1, le=10, default=5)
    sleep_hours: float = Field(ge=0, le=24, default=7.0)


class AwardRequest(BaseModel):
    student_id: int
    xp: int = Field(ge=0, default=10)
    badge: Optional[str] = None


class SendAlertRequest(BaseModel):
    channel: Literal["sms", "whatsapp"] = "sms"
    to: str = Field(min_length=1)
    message: str = Field(min_length=1)


class StudentFeaturesRequest(BaseModel):
    """Shared feature-vector shape consumed by ml.py::do_predict and
    digital_twin.py::project. Both routes previously did
    `float(data.get('avg_score', 60))`-style casts with no validation, so a
    non-numeric value (e.g. a string typo from a manually-built request)
    raised an unhandled ValueError that surfaced to the client as a raw 500
    — this was specifically confirmed reproducible in digital_twin.py.
    Bounds mirror the domain: avg_score/attendance_rate/homework_completion
    are on their respective natural scales, and behavior_incidents is a
    non-negative count.
    """

    avg_score: float = Field(ge=0, le=100, default=60)
    attendance_rate: float = Field(ge=0, le=1, default=0.9)
    homework_completion: float = Field(ge=0, le=1, default=0.8)
    behavior_incidents: float = Field(ge=0, default=0)


class VoiceAnalyzeRequest(BaseModel):
    transcript: str = Field(default="", max_length=10_000)
