def recommend_study_plan(features: dict, prediction: dict, risk: str):
    recs = []
    avg = float(features.get('avg_score', 60))
    attendance = float(features.get('attendance_rate', 0.9))
    if risk == 'High Risk':
        recs.append({'type': 'tutoring', 'detail': 'Schedule 2x/week tutoring sessions'})
        recs.append({'type': 'revision', 'detail': 'Focus on core topics: Algebra, Reading comprehension'})
    if attendance < 0.85:
        recs.append({'type': 'attendance', 'detail': 'Parent call + morning check-in'})
    if avg < 65:
        recs.append({'type': 'practice', 'detail': 'Daily 30-min practice on weak subjects'})
    recs.append({'type': 'videos', 'detail': 'Khan Academy playlist based on weak topics'})
    return recs
