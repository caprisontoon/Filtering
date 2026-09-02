# CPU 추론용 경량 이미지 (GPU 불필요)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
# 서빙만 할 경우 torch 없이 ONNX로 구동 가능 → 이미지 경량화하려면 requirements에서 torch/datasets 제거
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py rules.py ./
# 학습·양자화 산출물(./model 또는 ./model_onnx)은 빌드시 COPY 하거나 볼륨/오브젝트스토리지로 주입
COPY model_onnx ./model_onnx

ENV MODEL_DIR=./model_onnx USE_ONNX=1 BLOCK_THRESHOLD=0.9
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
