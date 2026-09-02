"""
파인튜닝 모델 → ONNX 변환 + int8 동적 양자화 (CPU 추론 경량화)

입력:  ./model       (train.py 결과)
출력:  ./model_onnx  (양자화된 ONNX + 토크나이저)

실행: python export_onnx.py
"""
from pathlib import Path
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForSequenceClassification, ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig

SRC = "./model"
OUT = "./model_onnx"

def main():
    Path(OUT).mkdir(parents=True, exist_ok=True)
    # 1) ONNX로 내보내기
    model = ORTModelForSequenceClassification.from_pretrained(SRC, export=True)
    tok = AutoTokenizer.from_pretrained(SRC)
    model.save_pretrained(OUT); tok.save_pretrained(OUT)

    # 2) int8 동적 양자화 (CPU). arm64 서버면 arm64=True 로 변경.
    quantizer = ORTQuantizer.from_pretrained(OUT)
    qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False)
    quantizer.quantize(save_dir=OUT, quantization_config=qconfig)
    print("ONNX(int8) 저장 완료 →", OUT)

if __name__ == "__main__":
    main()
