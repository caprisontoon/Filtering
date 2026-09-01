# Filtering

투네이션 비속어·음란 필터 테스트/관리 콘솔 (정적 단일 페이지).

## 구성
- `index.html` — 관리자 필터링 화면 전체(규칙 기반 필터 + 사전 관리 UI). 빌드 불필요.
- `whitelist_auto.json` — **자동 생성 화이트리스트**. 국어사전 명사 중 블랙리스트 표준형(canon, 5자모 이상)을
  부분문자열로 포함하되 그 자체가 슬러가 아닌 정상어 목록. 부분문자열 매칭 오탐(예: `시발` 등록 → `시발점` 차단)을 줄인다.
- `scripts/gen_whitelist.mjs` — 위 파일 재생성 배치 스크립트.

## 자동 화이트리스트 재생성
블랙리스트(lisuugi/hlog2e)나 명사 사전이 바뀌면 아래로 다시 생성한다. (Node 18+, 네트워크 필요)

```
node scripts/gen_whitelist.mjs
```

- 정규화 로직은 `index.html`의 `normalize()`를 그대로 추출해 사용하므로 런타임과 100% 동일하다.
- 출처: 블랙리스트 = lisuugi/korean-profanity-filter(Apache-2.0) + hlog2e/bad_word_list,
  명사 = pd-korean-noun-list-for-wordles(Public Domain, 표준국어대사전 표제어).

## 오탐 처리 방식(2계층)
- 깨끗한 텍스트: 화이트리스트(수동 + 자동)를 원문에서 먼저 제거 → 정상 복합어(`시발점`) 통과.
- 우회 텍스트(`시★발`, `ㅅㅂ`): 정규화 + 부분/초성 매칭으로 차단(화이트리스트가 새지 않음).
- 동음이의 단독어(`시발`=始發)는 계속 차단(후원 맥락상 타당). 진짜 문맥 판단은 향후 AI 몫.
