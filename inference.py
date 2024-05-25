import numpy as np

np.bool = np.bool_
import gluonnlp as nlp
import torch
from torch import nn
from kobert_tokenizer import KoBERTTokenizer
from transformers import BertModel
from torch.utils.data import Dataset

# Torch GPU 설정
device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
device = torch.device(device_type)

tokenizer = KoBERTTokenizer.from_pretrained('skt/kobert-base-v1')


# kobert 공식 git에 있는 get_kobert_model 선언
def get_kobert_model(model_path, vocab_file, ctx="cpu"):
    bertmodel = BertModel.from_pretrained(model_path)
    device = torch.device(ctx)
    bertmodel.to(device)
    bertmodel.eval()
    vocab_b_obj = nlp.vocab.BERTVocab.from_sentencepiece(vocab_file,
                                                         padding_token='[PAD]')
    return bertmodel, vocab_b_obj


bertmodel, vocab = get_kobert_model('skt/kobert-base-v1', tokenizer.vocab_file)
tok = nlp.data.BERTSPTokenizer(tokenizer, vocab, lower=False)


# BERTSentenceTransform 수정
class BERTSentenceTransform:

    def __init__(self, tokenizer, max_seq_length, vocab, pad=True, pair=True):
        self._tokenizer = tokenizer
        self._max_seq_length = max_seq_length
        self._pad = pad
        self._pair = pair
        self._vocab = vocab

    def __call__(self, line):

        # 유니코드로 변환
        text_a = line[0]
        if self._pair:
            assert len(line) == 2
            text_b = line[1]

        tokens_a = self._tokenizer.tokenize(text_a)
        tokens_b = None

        if self._pair:
            tokens_b = self._tokenizer(text_b)

        if tokens_b:
            # 'tokens_a' 및 'tokens_b'를 수정하여 총 길이가 지정된 길이보다 작아지도록 함
            # [CLS], [SEP], [SEP]에 해당하는 "- 3" 고려
            self._truncate_seq_pair(tokens_a, tokens_b,
                                    self._max_seq_length - 3)
        else:
            # [CLS] 및 [SEP]에 해당하는 "- 2" 고려
            if len(tokens_a) > self._max_seq_length - 2:
                tokens_a = tokens_a[0:(self._max_seq_length - 2)]

        vocab = self._vocab
        tokens = []
        tokens.append(vocab.cls_token)
        tokens.extend(tokens_a)
        tokens.append(vocab.sep_token)
        segment_ids = [0] * len(tokens)

        if tokens_b:
            tokens.extend(tokens_b)
            tokens.append(vocab.sep_token)
            segment_ids.extend([1] * (len(tokens) - len(segment_ids)))

        input_ids = self._tokenizer.convert_tokens_to_ids(tokens)

        # 문장의 길이
        valid_length = len(input_ids)

        if self._pad:
            # 시퀀스 길이까지 제로 패딩
            padding_length = self._max_seq_length - valid_length
            # 나머지는 패딩 토큰으로 채움
            input_ids.extend([vocab[vocab.padding_token]] * padding_length)
            segment_ids.extend([0] * padding_length)

        return np.array(input_ids, dtype='int32'), np.array(valid_length, dtype='int32'), \
            np.array(segment_ids, dtype='int32')


class BERTClassifier(nn.Module):
    def __init__(self,
                 bert,
                 hidden_size=768,
                 num_classes=7,  # 감정 클래스 수
                 dr_rate=None,
                 params=None):
        super(BERTClassifier, self).__init__()
        self.bert = bert
        self.dr_rate = dr_rate

        self.classifier = nn.Linear(hidden_size, num_classes)
        if dr_rate:
            self.dropout = nn.Dropout(p=dr_rate)

    def gen_attention_mask(self, token_ids, valid_length):
        attention_mask = torch.zeros_like(token_ids)
        for i, v in enumerate(valid_length):
            attention_mask[i][:v] = 1
        return attention_mask.float()

    def forward(self, token_ids, valid_length, segment_ids):
        attention_mask = self.gen_attention_mask(token_ids, valid_length)

        _, pooler = self.bert(input_ids=token_ids, token_type_ids=segment_ids.long(),
                              attention_mask=attention_mask.float().to(token_ids.device), return_dict=False)
        if self.dr_rate:
            out = self.dropout(pooler)
        return self.classifier(out)


class BERTDataset(Dataset):
    def __init__(self, dataset, sent_idx, label_idx, bert_tokenizer, vocab, max_len,
                 pad, pair):
        transform = BERTSentenceTransform(bert_tokenizer, max_seq_length=max_len, vocab=vocab, pad=pad, pair=pair)

        self.sentences = [transform([i[sent_idx]]) for i in dataset]
        self.labels = [np.int32(i[label_idx]) for i in dataset]

    def __getitem__(self, i):
        return (self.sentences[i] + (self.labels[i],))

    def __len__(self):
        return (len(self.labels))


emotion_map = {
    0: "불안",
    1: "당황",
    2: "분노",
    3: "슬픔",
    4: "중립",
    5: "행복",
    6: "혐오"
}

# 저장한 모델 불러오기
loaded_model = BERTClassifier(bertmodel, dr_rate=0.5).to(device)
checkpoint_path = './saved_model.pth'  # 모델 체크포인트 파일 경로
state_dict = torch.load(checkpoint_path)
loaded_model.load_state_dict(state_dict, strict=False)
loaded_model.eval()

# 하이퍼 파라미터 설정
max_len = 64
batch_size = 64
warmup_ratio = 0.1
num_epochs = 50
max_grad_norm = 1
log_interval = 200
learning_rate = 5e-5

# 입력을 계속해서 받기 위한 반복문
while True:
    # 예측할 문장 입력 받기
    input_sentence = input("분류할 문장을 입력하세요 (종료하려면 'exit'을 입력하세요): ")

    # 종료 조건 확인
    if input_sentence.lower() == 'exit':
        print("프로그램을 종료합니다.")
        break

    # 입력 문장을 BERT 모델의 입력 형식으로 변환
    transform = BERTSentenceTransform(tokenizer, max_seq_length=max_len, vocab=vocab, pad=True, pair=False)
    input_data = transform([input_sentence])

    # 토큰 ID, 유효 길이, 토큰 타입 ID를 추출
    input_token_ids, input_valid_length, input_segment_ids = input_data

    # 텐서로 변환
    input_token_ids = torch.tensor([input_token_ids], dtype=torch.long).to(device)
    input_valid_length = torch.tensor(input_valid_length, dtype=torch.long).to(device)  # 스칼라 값으로 전달
    input_segment_ids = torch.tensor([input_segment_ids], dtype=torch.long).to(device)

    # 예측 수행
    with torch.no_grad():
        input_valid_length = torch.tensor([input_valid_length], dtype=torch.long).to(device)  # 스칼라 값으로 전달
        output = loaded_model(input_token_ids, input_valid_length, input_segment_ids)
        predicted_situation_label = torch.argmax(output, dim=1).item()

    predicted_emotion = emotion_map.get(predicted_situation_label, "알 수 없는 감정")
    print("Predicted Emotion:", predicted_emotion)
