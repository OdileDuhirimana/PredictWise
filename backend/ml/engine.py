import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
import json

try:
    import shap  # optional, used if available
    _HAS_SHAP = True
except Exception:
    _HAS_SHAP = False

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'artifacts')
MODEL_PATH = os.path.join(MODEL_DIR, 'score_regressor.joblib')
BASELINE_PATH = os.path.join(MODEL_DIR, 'feature_baseline.json')


def ensure_dir():
    os.makedirs(MODEL_DIR, exist_ok=True)


def train_regressor(X: pd.DataFrame, y: pd.Series) -> float:
    ensure_dir()
    model = RandomForestRegressor(random_state=42)
    params = {'n_estimators': [100, 200], 'max_depth': [None, 10, 20]}
    n_samples = len(X)
    if n_samples < 2:
        # Not enough data for CV; train a default model or skip
        model.set_params(n_estimators=100, max_depth=None)
        try:
            model.fit(X, y)
            joblib.dump(model, MODEL_PATH)
        except Exception:
            pass
        # Save a trivial baseline
        _save_baseline(X)
        return 0.0
    cv_folds = 2 if n_samples == 2 else 3
    grid = GridSearchCV(model, params, cv=cv_folds, n_jobs=-1)
    grid.fit(X, y)
    joblib.dump(grid.best_estimator_, MODEL_PATH)
    # Save feature baseline from training data
    _save_baseline(X)
    return float(grid.best_score_)


def is_trained() -> bool:
    return os.path.exists(MODEL_PATH)


def predict(features: dict) -> dict:
    ensure_dir()
    if not os.path.exists(MODEL_PATH):
        # Fallback heuristic if not trained
        base = float(features.get('avg_score', 60))
        attendance = float(features.get('attendance_rate', 0.9))
        predicted = base * (0.5 + 0.5 * attendance)
        pass_prob = min(0.99, max(0.01, predicted / 100))
        growth = (predicted - base) / max(1.0, base)
        return {'predicted_score': predicted, 'pass_prob': pass_prob, 'expected_growth': growth}
    model = joblib.load(MODEL_PATH)
    cols = ['avg_score', 'attendance_rate', 'homework_completion', 'behavior_incidents']
    x = np.array([[float(features.get(c, 0 if c=='behavior_incidents' else 0.0)) for c in cols]])
    pred = float(model.predict(x)[0])
    pass_prob = min(0.99, max(0.01, pred / 100))
    growth = (pred - float(features.get('avg_score', 60))) / max(1.0, float(features.get('avg_score', 60)))
    return {'predicted_score': pred, 'pass_prob': pass_prob, 'expected_growth': growth}


def _save_baseline(X: pd.DataFrame):
    try:
        ensure_dir()
        # Save per-feature quantile bins to use for PSI
        baseline = {}
        for col in X.columns:
            try:
                # 10 bins quantiles
                qs = np.linspace(0, 1, 11)
                cuts = list(pd.Series(X[col]).quantile(qs).astype(float).values)
                # ensure strictly increasing
                cuts = [cuts[0]] + [max(cuts[i], cuts[i-1] + 1e-9) for i in range(1, len(cuts))]
                baseline[col] = cuts
            except Exception:
                baseline[col] = []
        with open(BASELINE_PATH, 'w') as f:
            json.dump(baseline, f)
    except Exception:
        pass


def get_baseline():
    if not os.path.exists(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH, 'r') as f:
        return json.load(f)


def compute_psi(current: pd.DataFrame) -> dict:
    """Compute PSI for each feature using stored baseline quantile cuts."""
    baseline = get_baseline()
    res = {}
    for col, cuts in baseline.items():
        if not cuts or col not in current.columns:
            res[col] = None
            continue
        try:
            bins = pd.IntervalIndex.from_breaks(cuts, closed='both')
            cur = pd.cut(current[col].astype(float), bins=bins, include_lowest=True)
            cur_counts = cur.value_counts().sort_index()
            cur_pct = (cur_counts / max(cur_counts.sum(), 1)).replace(0, 1e-6)
            # Uniform baseline across bins from training quantiles
            base_pct = pd.Series(np.repeat(1/len(cur_pct), len(cur_pct)), index=cur_pct.index)
            psi = float(((cur_pct - base_pct) * np.log(cur_pct / base_pct)).sum())
            res[col] = psi
        except Exception:
            res[col] = None
    return res


def explain_shap(feature_row: dict) -> list:
    """Return SHAP values if shap is available; fallback to feature importance × value.
    Returns list of dicts: [{feature, shap_value}] sorted by absolute value desc.
    """
    cols = ['avg_score', 'attendance_rate', 'homework_completion', 'behavior_incidents']
    x = np.array([[float(feature_row.get(c, 0 if c=='behavior_incidents' else 0.0)) for c in cols]])
    if not os.path.exists(MODEL_PATH):
        # simple zeros if untrained
        return [{'feature': c, 'shap_value': 0.0} for c in cols]
    model = joblib.load(MODEL_PATH)
    if _HAS_SHAP:
        try:
            explainer = shap.TreeExplainer(model)
            sv = explainer.shap_values(x)
            # For regression, sv is shape (n_samples, n_features)
            shap_vals = sv[0] if isinstance(sv, list) else sv[0]
            out = [{'feature': c, 'shap_value': float(v)} for c, v in zip(cols, shap_vals)]
            out.sort(key=lambda d: abs(d['shap_value']), reverse=True)
            return out
        except Exception:
            pass
    # Fallback: use feature importance scaled by feature values
    try:
        imps = getattr(model, 'feature_importances_', None)
        if imps is None:
            imps = np.ones(len(cols)) / len(cols)
        approx = imps * x[0]
        out = [{'feature': c, 'shap_value': float(v)} for c, v in zip(cols, approx)]
        out.sort(key=lambda d: abs(d['shap_value']), reverse=True)
        return out
    except Exception:
        return [{'feature': c, 'shap_value': 0.0} for c in cols]
