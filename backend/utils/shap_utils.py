def shap_explain(features: dict, prediction: dict):
    # Placeholder lightweight explanation
    avg = float(features.get('avg_score', 60))
    attendance = float(features.get('attendance_rate', 0.9))
    return [
        {'feature': 'avg_score', 'impact': round((avg - 60)/40, 3)},
        {'feature': 'attendance_rate', 'impact': round((attendance - 0.85)/0.15, 3)},
    ]
