from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str):
    if not text:
        return {'neg': 0.0, 'neu': 1.0, 'pos': 0.0, 'compound': 0.0}
    scores = _analyzer.polarity_scores(text)
    # Map to qualitative label
    label = 'neutral'
    if scores['compound'] >= 0.2:
        label = 'positive'
    elif scores['compound'] <= -0.2:
        label = 'negative'
    return {**scores, 'label': label}
