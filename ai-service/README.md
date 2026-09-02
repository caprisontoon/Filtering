# ai-service — 규칙 + KcELECTRA 하이브리드 필터 (베타)

투네이션 후원 메시지 문맥 판정용 백엔드. 프론트(`index.html`의 "AI 필터(베타)" 탭)가 이 서버의
`POST /api/ai-filter` 를 호출한다.

- **목적**: 사용성 최우선. 비속어가 섞인 일반 문장은 최대한 통과, **명백·악의적 욕설만 차단**.
- **구성**: ① 규칙(정규식, 우회 차단) → ② KcELECTRA(K-HATERS 학습) 문맥 판정.
- **정적 사이트와 무관**: 이 서버가 없어도 기존 규칙 화면은 정상 동작한다.

## 라이선스 (상업적 사용 가능 조합)
- 모델: **KcELECTRA (MIT)** — beomi/KcELECTRA-base
- 학습 데이터: **K-HATERS (CC-BY 4.0)** — 출처표시(논문 인용)만 하면 상업 사용 가능
- 규칙 정규식: **KoreanCursewordRegex (CC0)** — 의무 없음
> ※ 상용 배포 전 각 원문 라이선스를 법무로 최종 확인 권장.

## 디렉터리
```
ai-service/
  requirements.txt   # 의존성
  train.py           # KcELECTRA × K-HATERS 파인튜닝(4분류)  ← GPU 권장(무료 Colab OK)
  export_onnx.py     # ONNX 변환 + int8 양자화(추론 경량화)
  rules.py           # CC0 정규식 우회 차단(1차 필터) — 실제 패턴은 여기 채워넣기
  server.py          # FastAPI 서버: /api/ai-filter, /health (CORS)
  Dockerfile         # 컨테이너 배포용(선택)
```

## 실행 순서
### 1) 학습 (한 번, GPU 권장)
```bash
pip install -r requirements.txt
python train.py            # → ./model/ 에 저장 (label: normal/offensive/L1_hate/L2_hate)
```
K-HATERS 데이터 위치는 `train.py` 상단 `DATA_SOURCE` 로 지정(HF 허브 id 또는 로컬 경로).
데이터셋 형식은 `text`, `label` 컬럼을 기대한다. (K-HATERS 원본 라벨: normal/offensive/L1_hate/L2_hate)

### 2) (선택) ONNX 경량화 — CPU 서빙 최적화
```bash
python export_onnx.py      # → ./model_onnx/ (int8)
```

### 3) 서버 실행
```bash
# 환경변수(선택): MODEL_DIR(기본 ./model), USE_ONNX=1, ALLOW_ORIGINS, BLOCK_THRESHOLD
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4) 프론트 연결
배포된 주소(예: `https://<서버>/api/ai-filter`)를 "AI 필터(베타)" 탭의 **AI API 주소**에 입력·저장.
CORS 때문에 `ALLOW_ORIGINS` 에 정적 사이트 도메인(`https://filtering-six.vercel.app`)을 넣어야 한다.

## API
`POST /api/ai-filter`  요청 `{"text": "..."}`
응답:
```json
{
  "text": "...",
  "rule_hit": false,
  "label": "offensive",
  "probs": {"normal":0.02,"offensive":0.95,"l1_hate":0.02,"l2_hate":0.01},
  "p_bad": 0.98,
  "action": "block"
}
```
- `rule_hit=true` 면 규칙(우회)에서 즉시 차단된 것.
- 프론트는 `probs` 를 받아 슬라이더 임계값으로 통과/차단을 **실시간 재계산**한다(서버 `action` 은 기본 임계값 기준).

## 사양 / 스케일
- **추론은 CPU로 충분**(문장당 ~10~30ms, ONNX int8). GPU 불필요.
- 상태 없는 서비스 → 트래픽 증가 시 **복제(수평 확장)** + 로드밸런서. 규칙 1차 필터가 AI 호출량을 줄여줌.
