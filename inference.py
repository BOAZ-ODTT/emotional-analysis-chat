import numpy as np
import torch
from torch.utils.data import Dataset

np.bool = np.bool_

import gluonnlp as nlp

from kobert_tokenizer import KoBERTTokenizer
from transformers import BertModel

# Torch GPU 설정
device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
device = torch.device(device_type)


class BERTDataset(Dataset):
    def __init__(self, dataset, sent_idx, label_idx, bert_tokenizer, max_len,
                 pad, pair):
        transform = nlp.data.BERTSentenceTransform(
            bert_tokenizer, max_seq_length=max_len, pad=pad, pair=pair)

        self.sentences = [transform([i[sent_idx]]) for i in dataset]
        self.labels = [np.int32(i[label_idx]) for i in dataset]

    def __getitem__(self, i):
        return (self.sentences[i] + (self.labels[i],))

    def __len__(self):
        return (len(self.labels))


# kobert 공식 git에 있는 get_kobert_model 선언
def get_kobert_model(model_path, vocab_file, ctx="cpu"):
    bertmodel = BertModel.from_pretrained(model_path)
    device = torch.device(ctx)
    bertmodel.to(device)
    bertmodel.eval()
    vocab_b_obj = nlp.vocab.BERTVocab.from_sentencepiece(vocab_file,
                                                         padding_token='[PAD]')
    return bertmodel, vocab_b_obj


tokenizer = KoBERTTokenizer.from_pretrained('skt/kobert-base-v1')
bertmodel, vocab = get_kobert_model('skt/kobert-base-v1', tokenizer.vocab_file)

# 새로운 문장 테스트
# 토큰화
tok = nlp.data.BERTSPTokenizer(tokenizer, vocab, lower=False)

# Setting parameters
max_len = 64
batch_size = 64
warmup_ratio = 0.1
num_epochs = 10
max_grad_norm = 1
log_interval = 200
learning_rate = 5e-5

model_path = 'saved_model.pt'
model = torch.load(model_path)


def predict(predict_sentence):
    data = [predict_sentence, '0']
    dataset_another = [data]

    another_test = BERTDataset(dataset_another, 0, 1, tok, max_len, True, False)
    test_dataloader = torch.utils.data.DataLoader(another_test, batch_size=batch_size, num_workers=5)

    model.eval()
    with torch.no_grad():

        for batch_id, (token_ids, valid_length, segment_ids, label) in enumerate(test_dataloader):
            token_ids = token_ids.long().to(device)
            segment_ids = segment_ids.long().to(device)

            valid_length = valid_length
            label = label.long().to(device)

            out = model(token_ids, valid_length, segment_ids)

            test_eval = []
            for i in out:
                logits = i
                logits = logits.detach().cpu().numpy()

                if np.argmax(logits) == 0:
                    test_eval.append("불안이")
                elif np.argmax(logits) == 1:
                    test_eval.append("당황이")
                elif np.argmax(logits) == 2:
                    test_eval.append("분노가")
                elif np.argmax(logits) == 3:
                    test_eval.append("슬픔이")
                elif np.argmax(logits) == 4:
                    test_eval.append("중립이")
                elif np.argmax(logits) == 5:
                    test_eval.append("행복이")
                elif np.argmax(logits) == 6:
                    test_eval.append("혐오가")

            print(">> 입력하신 내용에서 " + test_eval[0] + " 느껴집니다.")


# 질문 무한반복하기! 0 입력시 종료
end = 1
while end == 1:
    sentence = input("하고싶은 말을 입력해주세요 : ")
    if sentence == "0":
        break
    predict(sentence)
    print("\n")
