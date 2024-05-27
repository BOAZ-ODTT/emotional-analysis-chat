from service.emotion_analysis.emotion_classifier import EmotionClassifier


class MockEmotionClassifier(EmotionClassifier):

    def __init__(self):
        pass

    def classify(self, message: str) -> str:
        return "아무 감정이"
