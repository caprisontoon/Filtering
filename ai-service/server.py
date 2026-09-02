"""
FastAPI 서버: 규칙 + KcELECTRA 하이브리드 필터

POST /api/ai-filter  {"text": "..."}  →  {label, probs, p_bad, action, rule_hit}
GET  /health

환경변수:
  MODEL_DIR       모델 경로 (기본 ./model, ONNX면 ./model_onnx)
  USE_ONNX        "1" 이면 onnxruntime 백엔드 사용(CPU 경량)
  BLOCK_THRESHOLD 기본 차단 임계값(기본 0.9) — 프론트 슬라이더가 재계산하므로 참고용
  ALLOW_ORIGINS   CORS 허용 도메인(콤마구분). 예) https://filtering-six.vercel.app
실행: uvicorn server:app --host 0.0.0.0 --port 8000
"""
import os
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoTokenizer
import rules

MODEL_DIR = os.getenv("MODEL_DIR", "./model")
USE_ONNX = os.getenv("USE_ONNX", "0") == "1"
BLOCK_THRESHOLD = float(os.getenv("BLOCK_THRESHOLD", "0.9"))
ALLOW_ORIGINS = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "*").split(",") if o.strip()]

LABELS = ["normal", "offensive", "L1_hate", "L2_hate"]
KEYS = ["normal", "offensive", "l1_hate", "l2_hate"]   # 응답 키(소문자)

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
if USE_ONNX:
    from optimum.onnxruntime import ORTModelForSequenceClassification
    model = ORTModelForSequenceClassification.from_pretrained(MODEL_DIR)
else:
    import torch
    from transformers import AutoModelForSequenceClassification
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()

def _softmax(x):
    e = np.exp(x - np.max(x)); return e / e.sum()

def classify(text: str):
    enc = tok(text, return_tensors=("np" if USE_ONNX else "pt"),
              truncation=True, max_length=128)
    if USE_ONNX:
        logits = model(**enc).logits[0]
    else:
        import torch
        with torch.no_grad():
            logits = model(**enc).logits[0].numpy()
    probs = _softmax(np.asarray(logits, dtype=np.float64))
    return {KEYS[i]: float(probs[i]) for i in range(len(LABELS))}

def decide(probs, threshold):
    p_bad = 1.0 - probs["normal"]
    block = probs["l2_hate"] >= 0.70 or p_bad >= threshold
    top = max(probs, key=probs.get)
    return top, p_bad, ("block" if block else "allow")

app = FastAPI(title="Toonation AI Filter (beta)")
app.add_middleware(CORSMiddleware, allow_origins=ALLOW_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

class Req(BaseModel):
    text: str
    threshold: float | None = None

@app.get("/health")
def health():
    return {"ok": True, "onnx": USE_ONNX, "labels": LABELS}

@app.post("/api/ai-filter")
def ai_filter(req: Req):
    text = req.text or ""
    th = req.threshold if req.threshold is not None else BLOCK_THRESHOLD
    # ① 규칙(우회) 1차 — 명백하면 즉시 차단
    if rules.rule_block(text):
        return {"text": text, "rule_hit": True, "label": "offensive",
                "probs": {"normal": 0.0, "offensive": 1.0, "l1_hate": 0.0, "l2_hate": 0.0},
                "p_bad": 1.0, "action": "block"}
    # ② AI 문맥 판정
    probs = classify(text)
    label, p_bad, action = decide(probs, th)
    return {"text": text, "rule_hit": False, "label": label,
            "probs": probs, "p_bad": p_bad, "action": action}
