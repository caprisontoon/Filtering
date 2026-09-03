# Cloud Run용 (CPU) — 모델을 이미지에 미리 받아두어 콜드스타트 단축
FROM python:3.11-slim

WORKDIR /app
ENV HF_HOME=/app/hf-cache MODEL_ID=smilegate-ai/kor_unsmile

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
# 빌드 시 모델을 캐시에 미리 다운로드(런타임 콜드스타트에서 재다운로드 방지)
RUN python -c "from transformers import pipeline; import os; pipeline('text-classification', model=os.environ['MODEL_ID'], top_k=None)"

# Cloud Run은 $PORT(기본 8080)로 요청을 보냄
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
