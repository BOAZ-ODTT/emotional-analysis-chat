class EmotionClassifier:

    def __init__(self):
        from inference import predict_emotion

        self._classifier = predict_emotion

    def classify(self, message: str) -> str:
        return self._classifier(message)
