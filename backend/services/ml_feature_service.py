"""Feature-engineering logic for the ML pipeline — pure pandas
transforms, no Flask/DB/ORM dependency.

Why extracted: routes/ml.py::train() and routes/ml.py::drift() each
independently rebuilt the exact same "assessments + attendance ->
per-student feature frame" transform (the audit's CODE-04 duplicate-logic
finding — the two copies were only one line apart in shape but genuinely
duplicated). Centralizing it here means:
  - the transform can be unit-tested with plain lists of dicts, no Flask
    app, no database, no ORM models;
  - train() and drift() are now provably building an identical feature
    frame, which matters because PSI drift detection is only meaningful
    if "current" features are computed the same way "training" features
    were.
"""
from __future__ import annotations

from typing import Sequence

import pandas as pd

# These three features aren't tracked anywhere in the current schema
# (there's no homework-completion or behavior-incident model), so a fixed
# default stands in for them across every student — named here rather
# than as inline literals, and documented as a known simplification (see
# project.md's "Challenges & Tradeoffs").
DEFAULT_ATTENDANCE_RATE = 0.9
DEFAULT_HOMEWORK_COMPLETION = 0.8
DEFAULT_BEHAVIOR_INCIDENTS = 0

FEATURE_COLUMNS = ["avg_score", "attendance_rate", "homework_completion", "behavior_incidents"]


def build_feature_dataframe(
    assessment_rows: Sequence[dict],
    attendance_rows: Sequence[dict],
) -> pd.DataFrame:
    """Builds one row per student with columns
    [student_id, avg_score, attendance_rate, homework_completion, behavior_incidents].

    Args:
        assessment_rows: [{'student_id': int, 'score': float}, ...] — one
            row per Assessment record.
        attendance_rows: [{'student_id': int, 'present': 0 | 1}, ...] —
            one row per Attendance record. May be empty.

    Returns:
        A DataFrame with one row per distinct student_id present in
        `assessment_rows`. Empty (with the correct columns) if
        `assessment_rows` is empty — callers are expected to check for
        "no assessment data" themselves before calling this, matching the
        existing 400 behavior in routes/ml.py.
    """
    assessments_df = pd.DataFrame(assessment_rows, columns=["student_id", "score"])
    if assessments_df.empty:
        return pd.DataFrame(columns=["student_id", *FEATURE_COLUMNS])

    per_student_avg = (
        assessments_df.groupby("student_id").score.mean().reset_index().rename(columns={"score": "avg_score"})
    )

    if attendance_rows:
        attendance_df = pd.DataFrame(attendance_rows, columns=["student_id", "present"])
        attendance_rate = (
            attendance_df.groupby("student_id")
            .present.mean()
            .reset_index()
            .rename(columns={"present": "attendance_rate"})
        )
    else:
        # Explicit float64 dtype (rather than pandas' default object dtype
        # for an empty DataFrame) avoids a pandas FutureWarning on the
        # fillna() below about downcasting object-dtype columns.
        attendance_rate = pd.DataFrame({"student_id": pd.Series(dtype="int64"), "attendance_rate": pd.Series(dtype="float64")})

    merged = per_student_avg.merge(attendance_rate, on="student_id", how="left").fillna(
        {"attendance_rate": DEFAULT_ATTENDANCE_RATE}
    )
    merged["homework_completion"] = DEFAULT_HOMEWORK_COMPLETION
    merged["behavior_incidents"] = DEFAULT_BEHAVIOR_INCIDENTS

    return merged[["student_id", *FEATURE_COLUMNS]]
