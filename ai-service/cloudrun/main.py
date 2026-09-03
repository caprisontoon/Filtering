"""
Cloud Run용 AI 필터 API (KcELECTRA 계열 분류기)

- 기본 모델: smilegate-ai/kor_unsmile (KcELECTRA를 한국어 혐오/욕설로 학습한 공개 분류기)
  → 나중에 자체 학습 모델(KcELECTRA×K-HATERS)로 MODEL_ID만 바꾸면 됨.
- 프론트 "AI 필터(베타)" 탭이 기대하는 형태로 응답:
  {text, rule_hit, label, probs:{normal,offensive,l1_hate,l2_hate}, p_bad, action}

환경변수:
  MODEL_ID        기본 smilegate-ai/kor_unsmile
  BLOCK_THRESHOLD 기본 0.9 (프론트 슬라이더가 최종 재계산)
  ALLOW_ORIGINS   CORS 허용 도메인(콤마구분). 예) https://filtering-six.vercel.app
"""
import os
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline

MODEL_ID = os.getenv("MODEL_ID", "smilegate-ai/kor_unsmile")
BLOCK_THRESHOLD = float(os.getenv("BLOCK_THRESHOLD", "0.9"))
ALLOW_ORIGINS = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "*").split(",") if o.strip()]

CLEAN_NAMES = {"clean", "정상", "normal", "none", "not_hate"}
ABUSE_NAMES = {"악플/욕설", "욕설", "offensive", "abuse", "toxic"}

clf = pipeline("text-classification", model=MODEL_ID, top_k=None)

def to_probs(scores):
    """모델 라벨 → 프론트 4키(normal/offensive/l1_hate/l2_hate)로 매핑."""
    clean = 0.0; offensive = 0.0; hate_max = 0.0
    for s in scores:
        name = str(s["label"]).strip(); low = name.lower(); sc = float(s["score"])
        if low in CLEAN_NAMES or "clean" in low:
            clean = max(clean, sc)
        elif name in ABUSE_NAMES or low in ABUSE_NAMES:
            offensive = max(offensive, sc)
        else:
            hate_max = max(hate_max, sc)   # 나머지는 집단 혐오 계열로 취급
    return {"normal": clean, "offensive": offensive, "l1_hate": hate_max, "l2_hate": 0.0}

def classify(text):
    scores = clf(text)[0]
    probs = to_probs(scores)
    raw = {str(s["label"]): round(float(s["score"]), 4) for s in scores}
    return probs, raw

def decide(probs, threshold):
    p_bad = 1.0 - probs["normal"]
    block = probs["l2_hate"] >= 0.70 or p_bad >= threshold
    label = max(probs, key=probs.get)
    return label, p_bad, ("block" if block else "allow")

app = FastAPI(title="Toonation AI Filter (Cloud Run)")
app.add_middleware(CORSMiddleware, allow_origins=ALLOW_ORIGINS or ["*"],
                   allow_methods=["*"], allow_headers=["*"])

class Req(BaseModel):
    text: str
    threshold: float | None = None

@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_ID}

@app.get("/api/ai-filter")
def ping():
    # 프론트의 "연결 확인"(GET)이 200을 받도록
    return {"ok": True, "model": MODEL_ID, "hint": "POST {text} 로 검사하세요"}

@app.post("/api/ai-filter")
def ai_filter(req: Req):
    text = req.text or ""
    th = req.threshold if req.threshold is not None else BLOCK_THRESHOLD
    if not text.strip():
        return {"text": text, "rule_hit": False, "label": "normal",
                "probs": {"normal": 1.0, "offensive": 0.0, "l1_hate": 0.0, "l2_hate": 0.0},
                "p_bad": 0.0, "action": "allow"}
    probs, raw = classify(text)
    label, p_bad, action = decide(probs, th)
    return {"text": text, "rule_hit": False, "label": label,
            "probs": probs, "p_bad": p_bad, "action": action, "raw": raw}
