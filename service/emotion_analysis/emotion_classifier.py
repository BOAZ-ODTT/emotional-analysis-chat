class EmotionClassifier:

    def __init__(self):
        from service.emotion_analysis.inference import predict_emotion
        self._classifier = predict_emotion

    def classify(self, message: str) -> str:
        return self._classifier(message)
