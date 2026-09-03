# Google Cloud Run 배포 가이드 (AI 필터 API)

목표: 이 폴더(`ai-service/cloudrun`)를 Cloud Run에 올려 **항상 접속 가능한 API 주소**를 만들고,
필터 사이트의 **"AI 필터(베타)" 탭**에 연결한다. (설치 불필요 — 브라우저의 Cloud Shell로 진행)

- 모델: `smilegate-ai/kor_unsmile` (KcELECTRA 계열 공개 분류기). 나중에 자체 모델로 교체 가능.
- 비용: 신규 가입 **$300 크레딧(90일)**. Cloud Run은 안 쓰면 0으로 축소되어 저렴.

---

## 0) 준비
1. https://console.cloud.google.com 접속 → 구글 계정 로그인.
2. 상단에서 **새 프로젝트** 생성(예: `toonation-filter`).
3. **결제(Billing) 사용 설정** (카드 등록 → $300 무료 크레딧 적용).

## 1) Cloud Shell 열기 (브라우저 터미널, 설치 불필요)
- 콘솔 오른쪽 위 **`>_` (Activate Cloud Shell)** 아이콘 클릭 → 하단에 터미널이 열림.

## 2) 코드 받기
```bash
git clone https://github.com/caprisontoon/Filtering.git
cd Filtering/ai-service/cloudrun
```

## 3) 필요한 서비스 켜기
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```
(프로젝트가 여러 개면 먼저 `gcloud config set project <프로젝트ID>`)

## 4) 배포 (한 줄)
서울 리전(asia-northeast3), 공개 호출 허용, 메모리 2Gi로 배포:
```bash
gcloud run deploy toonation-ai \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 2Gi --cpu 2 --timeout 600 \
  --set-env-vars ALLOW_ORIGINS=https://filtering-six.vercel.app
```
- 처음 실행 시 Artifact Registry 생성 여부를 물으면 **Y**.
- 빌드+배포에 **5~10분**(모델 다운로드 포함). 끝나면 **Service URL** 이 출력됨
  예) `https://toonation-ai-xxxxxxxx-du.a.run.app`

## 5) 필터 사이트에 연결
1. `https://filtering-six.vercel.app` → 왼쪽 **필터링 관리 → AI 필터(베타)**.
2. **AI API 주소** 칸에 위 Service URL 뒤에 `/api/ai-filter` 를 붙여 입력:
   ```
   https://toonation-ai-xxxxxxxx-du.a.run.app/api/ai-filter
   ```
3. **저장** → **연결 확인**(초록 OK) → 문장 입력 후 **AI 검사**.
   - 처음 한 번은 서버가 깨어나며 20~40초 걸릴 수 있음(콜드스타트).

## 6) 비용 관리 팁
- Cloud Run은 요청 없을 때 **자동으로 0 인스턴스**(과금 최소). 기본값이라 별도 설정 불필요.
- 완전히 내리려면: `gcloud run services delete toonation-ai --region asia-northeast3`

---

## 자주 나는 문제
- **연결 확인이 405/실패**: 주소 끝에 `/api/ai-filter` 를 붙였는지 확인. (GET은 200 ok를 반환하도록 되어 있음)
- **CORS 오류**: `--set-env-vars ALLOW_ORIGINS=` 에 실제 사이트 도메인을 정확히(https 포함) 넣었는지 확인.
- **메모리 부족(오류/재시작)**: `--memory 4Gi` 로 올려 재배포.
- **한국어가 아닌 다른 모델로 교체**: `--set-env-vars MODEL_ID=<huggingface 모델id>,ALLOW_ORIGINS=...` 로 재배포.

## 나중에: 자체 학습 모델로 교체
`ai-service/train.py`로 KcELECTRA×K-HATERS(또는 투네이션 데이터) 학습 → 결과 모델을 이미지에 포함하거나
Cloud Storage에서 로드하도록 `MODEL_ID`/로딩 경로만 바꾸면 된다. (`MODEL_GUIDE.md` 참고)
