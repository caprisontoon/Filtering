"""
투네이션 후원 메시지 필터 · AI 테스트 (Streamlit Community Cloud, 무료·개인 테스트용)

- 공개된 한국어 혐오/욕설 분류 모델을 불러와 문맥 판정.
- 차단점수 = 1 - (정상/clean 확률). 슬라이더 임계값 이상이면 '차단'.
- 목적: 사용성 우선(임계값을 높이면 명백한 것만 차단).
※ 개인 테스트용. 상업 사용 시 모델·데이터 라이선스 별도 확인.
"""
import streamlit as st
from transformers import pipeline

# 테스트용 공개 모델(한국어 혐오/욕설 다중 라벨). 메모리 부족 시 더 가벼운 모델로 교체.
MODEL_ID = "smilegate-ai/kor_unsmile"
CLEAN_NAMES = {"clean", "정상", "normal", "none", "not_hate"}

st.set_page_config(page_title="투네이션 필터 AI 테스트", page_icon="🛡️")

@st.cache_resource(show_spinner="AI 모델 불러오는 중… (처음 한 번만, 30초~1분)")
def load_model():
    return pipeline("text-classification", model=MODEL_ID, top_k=None)

def clean_prob(scores):
    for s in scores:
        if str(s["label"]).strip().lower() in CLEAN_NAMES or "clean" in str(s["label"]).lower():
            return s["score"]
    return 0.0

st.title("🛡️ 투네이션 후원 메시지 필터 · AI 테스트")
st.caption("문장을 넣고 통과/차단을 확인하세요. 임계값이 높을수록 관대(통과↑). · 개인 테스트용")

try:
    clf = load_model()
    ok = True
except Exception as e:
    ok = False
    st.error(f"모델 로드 실패: {e}\n(메모리 부족일 수 있어요. 더 가벼운 모델로 교체가 필요합니다.)")

th = st.slider("차단 임계값 (높을수록 관대)", 0.50, 0.99, 0.90, 0.01)
text = st.text_area("후원 메시지", placeholder="예) 오늘 방송 존나 웃겼다", height=90)

if st.button("AI 검사", type="primary") and ok:
    t = (text or "").strip()
    if not t:
        st.warning("문장을 입력하세요.")
    else:
        scores = clf(t)[0]
        clean = clean_prob(scores)
        p_bad = 1.0 - clean
        block = p_bad >= th
        if block:
            st.markdown(f"### 🔴 차단  \n차단점수 **{p_bad*100:.1f}%** ≥ 기준 {th*100:.0f}%")
        else:
            st.markdown(f"### 🟢 통과  \n차단점수 **{p_bad*100:.1f}%** < 기준 {th*100:.0f}%")
        st.write("클래스별 확률:")
        st.json({str(s["label"]): round(float(s["score"]), 4) for s in scores})

st.divider()
st.caption("모델: 공개 한국어 혐오/욕설 분류(테스트용) · 실제 서비스 적용 시 라이선스·성능 검증 필요")
