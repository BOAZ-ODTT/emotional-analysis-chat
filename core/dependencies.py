from chat.connection_manager import ConnectionManager
from emotion_analysis.mock_emotion_classifier import MockEmotionClassifier

# DI 구조를 고민하다가 지금은 단순하게 여기에 의존성을 Singleton으로 선언해둡니다.

connection_manager = ConnectionManager()

# emotion_classifier = EmotionClassifier()
# m1 import 이슈로 작업할 때는 MockEmotionClassifier 사용
# main에 merge 되지 않도록 주의해주세요!
emotion_classifier = MockEmotionClassifier()
