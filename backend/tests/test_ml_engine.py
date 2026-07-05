"""Unit tests for backend/ml/engine.py.

Why isolate MODEL_DIR/MODEL_PATH/BASELINE_PATH per test (via monkeypatch):
engine.py persists its trained model and PSI baseline to disk at fixed
paths under backend/ml/artifacts/. Without redirecting those paths, running
this suite would (a) overwrite the real committed
backend/ml/artifacts/score_regressor.joblib on every test run and (b) let
tests leak state into each other through a shared file. Each test gets its
own tmp_path-backed model/baseline file, so tests are hermetic and safe to
run in any order or in parallel.
"""
import numpy as np
import pandas as pd
import pytest

from backend.ml import engine


@pytest.fixture()
def isolated_artifacts(tmp_path, monkeypatch):
    """Redirect engine's model/baseline paths into a per-test tmp dir."""
    model_dir = tmp_path / "artifacts"
    monkeypatch.setattr(engine, "MODEL_DIR", str(model_dir))
    monkeypatch.setattr(engine, "MODEL_PATH", str(model_dir / "score_regressor.joblib"))
    monkeypatch.setattr(engine, "BASELINE_PATH", str(model_dir / "feature_baseline.json"))
    return model_dir


FEATURE_COLUMNS = ["avg_score", "attendance_rate", "homework_completion", "behavior_incidents"]


def _make_training_frame(n_rows: int) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(42)
    X = pd.DataFrame(
        {
            "avg_score": rng.uniform(40, 95, n_rows),
            "attendance_rate": rng.uniform(0.6, 1.0, n_rows),
            "homework_completion": rng.uniform(0.5, 1.0, n_rows),
            "behavior_incidents": rng.integers(0, 3, n_rows),
        }
    )
    y = X["avg_score"] * 0.9 + rng.normal(0, 2, n_rows)
    return X, y


class TestTrainRegressor:
    def test_trains_and_marks_model_as_trained(self, isolated_artifacts):
        assert engine.is_trained() is False
        X, y = _make_training_frame(20)

        score = engine.train_regressor(X, y)

        assert engine.is_trained() is True
        assert isinstance(score, float)

    def test_small_sample_does_not_raise(self, isolated_artifacts):
        """n_samples < 2 takes the 'not enough data for CV' branch, which
        must degrade gracefully (train a default model, save a trivial
        baseline) rather than raising GridSearchCV's cross-validation
        errors on a single row."""
        X, y = _make_training_frame(1)

        score = engine.train_regressor(X, y)

        assert score == 0.0
        # Model training on a single row can legitimately fail inside
        # sklearn (wrapped in a try/except in engine.py), so is_trained()
        # is not asserted here — the contract under test is "does not
        # raise", which the fixture's teardown-free execution proves.


class TestPredict:
    def test_heuristic_fallback_when_untrained(self, isolated_artifacts):
        result = engine.predict({"avg_score": 70, "attendance_rate": 0.9})

        assert engine.is_trained() is False
        assert result["predicted_score"] == pytest.approx(70 * (0.5 + 0.5 * 0.9))
        assert 0.01 <= result["pass_prob"] <= 0.99
        assert "expected_growth" in result

    def test_trained_model_path(self, isolated_artifacts):
        X, y = _make_training_frame(20)
        engine.train_regressor(X, y)

        result = engine.predict(
            {"avg_score": 70, "attendance_rate": 0.9, "homework_completion": 0.8, "behavior_incidents": 0}
        )

        assert engine.is_trained() is True
        assert isinstance(result["predicted_score"], float)
        assert 0.01 <= result["pass_prob"] <= 0.99

    def test_predict_missing_features_defaults_safely(self, isolated_artifacts):
        # No KeyError/TypeError even when the caller omits every feature.
        result = engine.predict({})
        assert "predicted_score" in result


class TestComputePsi:
    def test_returns_empty_without_baseline(self, isolated_artifacts):
        current = pd.DataFrame({"avg_score": [60, 70, 80]})
        assert engine.compute_psi(current) == {}

    def test_returns_psi_per_feature_with_baseline(self, isolated_artifacts):
        X, y = _make_training_frame(30)
        engine.train_regressor(X, y)

        current = X.copy()
        psi = engine.compute_psi(current)

        assert set(psi.keys()) == set(FEATURE_COLUMNS)
        for value in psi.values():
            assert value is None or isinstance(value, float)


class TestExplainShap:
    def test_untrained_returns_zeros(self, isolated_artifacts):
        result = engine.explain_shap({"avg_score": 70, "attendance_rate": 0.9})

        assert len(result) == len(FEATURE_COLUMNS)
        assert all(row["shap_value"] == 0.0 for row in result)
        assert {row["feature"] for row in result} == set(FEATURE_COLUMNS)

    def test_trained_feature_importance_fallback(self, isolated_artifacts, monkeypatch):
        """Force the feature-importance fallback branch explicitly by
        disabling the shap library branch, rather than relying on whether
        `shap` happens to be importable in the test environment."""
        monkeypatch.setattr(engine, "_HAS_SHAP", False)
        X, y = _make_training_frame(20)
        engine.train_regressor(X, y)

        result = engine.explain_shap(
            {"avg_score": 70, "attendance_rate": 0.9, "homework_completion": 0.8, "behavior_incidents": 0}
        )

        assert len(result) == len(FEATURE_COLUMNS)
        assert {row["feature"] for row in result} == set(FEATURE_COLUMNS)
        # Sorted by absolute shap value descending.
        magnitudes = [abs(row["shap_value"]) for row in result]
        assert magnitudes == sorted(magnitudes, reverse=True)

    def test_trained_real_shap_branch(self, isolated_artifacts):
        """Exercise the real shap.TreeExplainer path when shap is available
        and functional in this environment.

        shap 0.45.1 (pinned in requirements.txt) calls `np.obj2sctype`,
        which NumPy 2.0 removed — so on numpy>=2.1 (also pinned) importing
        shap succeeds but calling TreeExplainer raises AttributeError. This
        is a real upstream version-compatibility gap between two pinned
        dependencies, not a bug in engine.py: engine.py already wraps the
        shap call in `try/except Exception: pass` and falls through to the
        feature-importance fallback, which is exactly the behavior
        `test_trained_feature_importance_fallback` verifies explicitly.
        We skip this test rather than assert on it so the suite doesn't
        depend on a shap/numpy combination fix outside this pass's scope.
        """
        try:
            import shap
        except Exception as exc:
            # shap 0.45.1 pinned against numpy 2.1 raises AttributeError
            # (`np.obj2sctype` removed) during its own module import, not a
            # clean ImportError, so a plain `pytest.importorskip` can't
            # catch it — hence the broad except here.
            pytest.skip(f"shap is not importable/functional in this environment: {exc}")

        X, y = _make_training_frame(20)
        engine.train_regressor(X, y)
        model = engine.joblib.load(engine.MODEL_PATH)
        try:
            shap.TreeExplainer(model)
        except Exception as exc:
            pytest.skip(f"shap is installed but non-functional in this environment: {exc}")

        result = engine.explain_shap(
            {"avg_score": 70, "attendance_rate": 0.9, "homework_completion": 0.8, "behavior_incidents": 0}
        )

        assert len(result) == len(FEATURE_COLUMNS)
        assert all(isinstance(row["shap_value"], float) for row in result)
