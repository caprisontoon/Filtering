"""
KcELECTRA × K-HATERS 파인튜닝 (4분류: normal/offensive/L1_hate/L2_hate)

- 모델: beomi/KcELECTRA-base (MIT)
- 데이터: K-HATERS (CC-BY 4.0) — text, label 컬럼 기대
- GPU 권장(무료 Colab 가능). 결과는 ./model 에 저장.

실행: python train.py
※ 이 저장소(정적 사이트) 환경이 아니라 실제 GPU 서버/Colab에서 실행하세요.
"""
import numpy as np
from datasets import load_dataset
from sklearn.metrics import f1_score, accuracy_score
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          TrainingArguments, Trainer, DataCollatorWithPadding)

# ── 설정 ─────────────────────────────────────────────
MODEL_NAME = "beomi/KcELECTRA-base"
# K-HATERS 데이터 위치: HF 허브 데이터셋 id 또는 로컬 파일(csv/json) 경로.
# 실제 사용 전 데이터셋 id/형식을 확인하세요(README 참고).
DATA_SOURCE = "humane-lab/K-HATERS"   # 예시. 로컬이면 {"train":"path.csv", ...} 형태로 교체
OUT_DIR = "./model"
MAX_LEN = 128
EPOCHS = 3
BATCH = 32
LR = 2e-5

# 라벨 표준화(대소문자/표기 흔들림 흡수)
LABELS = ["normal", "offensive", "L1_hate", "L2_hate"]
label2id = {l: i for i, l in enumerate(LABELS)}
id2label = {i: l for l, i in label2id.items()}
def norm_label(v):
    s = str(v).strip().lower().replace("-", "_")
    table = {"normal": "normal", "none": "normal",
             "offensive": "offensive",
             "l1_hate": "L1_hate", "l1": "L1_hate", "hate": "L1_hate",
             "l2_hate": "L2_hate", "l2": "L2_hate"}
    return table.get(s, "normal")

def main():
    ds = load_dataset(DATA_SOURCE) if isinstance(DATA_SOURCE, str) else load_dataset("csv", data_files=DATA_SOURCE)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)

    def prep(batch):
        enc = tok(batch["text"], truncation=True, max_length=MAX_LEN)
        enc["labels"] = [label2id[norm_label(x)] for x in batch["label"]]
        return enc

    keep = ds["train"].column_names
    ds = ds.map(prep, batched=True, remove_columns=keep)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABELS), id2label=id2label, label2id=label2id)

    def metrics(p):
        pred = np.argmax(p.predictions, axis=1)
        return {"accuracy": accuracy_score(p.label_ids, pred),
                "f1_macro": f1_score(p.label_ids, pred, average="macro")}

    args = TrainingArguments(
        output_dir=OUT_DIR, learning_rate=LR,
        per_device_train_batch_size=BATCH, per_device_eval_batch_size=BATCH,
        num_train_epochs=EPOCHS, weight_decay=0.01,
        eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="f1_macro",
        logging_steps=100)

    trainer = Trainer(
        model=model, args=args,
        train_dataset=ds["train"],
        eval_dataset=ds.get("validation") or ds.get("test"),
        tokenizer=tok, data_collator=DataCollatorWithPadding(tok),
        compute_metrics=metrics)

    trainer.train()
    trainer.save_model(OUT_DIR)
    tok.save_pretrained(OUT_DIR)
    print("저장 완료 →", OUT_DIR)

if __name__ == "__main__":
    main()
