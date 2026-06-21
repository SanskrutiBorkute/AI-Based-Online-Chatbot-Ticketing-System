from textblob import TextBlob

def analyze_sentiment(text):

    text_lower = text.lower()

    emergency_words = [
        "smoke", "fire", "panic", "bomb", "accident",
        "injured", "emergency",

        "धुआं", "आग", "घायल", "आपातकाल", "दुर्घटना",

        "धूर", "आग", "जखमी", "आपत्कालीन", "अपघात"
    ]

    if any(word in text_lower for word in emergency_words):
        return {
            "sentiment": "negative",
            "score": 1.0
        }

    blob = TextBlob(text)

    polarity = blob.sentiment.polarity

    if polarity > 0.2:
        sentiment = "positive"
    elif polarity < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "score": round(abs(polarity), 2)
    }

