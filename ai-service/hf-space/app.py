"""
투네이션 후원 메시지 필터 · AI 테스트 (Hugging Face Space, 개인 테스트용)

- 공개된 한국어 혐오/욕설 분류 모델을 그대로 불러와 문맥 판정.
- '차단 점수 = 1 - (정상/clean 확률)'. 슬라이더 임계값 이상이면 '차단'.
- 목적: 사용성 우선 → 임계값을 높게 두면 명백한 것만 차단.
※ 개인 테스트용. 상업 사용 시 모델·데이터 라이선스 별도 확인.
"""
import gradio as gr
from transformers import pipeline

# 테스트용 공개 모델(한국어 혐오/욕설 다중 라벨). 필요하면 다른 모델 id로 교체 가능.
MODEL_ID = "smilegate-ai/kor_unsmile"

clf = pipeline("text-classification", model=MODEL_ID, top_k=None)

# '정상' 계열 라벨 이름 후보(모델마다 표기가 달라 폭넓게 인식)
CLEAN_NAMES = {"clean", "정상", "normal", "none", "not_hate"}

def _clean_prob(scores):
    for s in scores:
        if str(s["label"]).strip().lower() in CLEAN_NAMES or "clean" in str(s["label"]).lower():
            return s["score"]
    # '정상' 라벨을 못 찾으면, 가장 높은 라벨이 정상이 아니라고 보고 보수적으로 0 처리
    return 0.0

def judge(text, threshold):
    text = (text or "").strip()
    if not text:
        return "―", "문장을 입력하세요", {}
    scores = clf(text)[0]                      # [{label, score}, ...]
    clean = _clean_prob(scores)
    p_bad = 1.0 - clean
    block = p_bad >= threshold
    verdict = "🔴 차단" if block else "🟢 통과"
    desc = f"차단점수 {p_bad*100:.1f}%  {'≥' if block else '<'}  기준 {threshold*100:.0f}%"
    detail = {str(s["label"]): round(float(s["score"]), 4) for s in scores}
    return verdict, desc, detail

with gr.Blocks(title="투네이션 필터 AI 테스트") as demo:
    gr.Markdown("## 🛡️ 투네이션 후원 메시지 필터 · AI 테스트\n"
                "문장을 넣고 **통과/차단**을 확인하세요. 임계값이 높을수록 관대(통과↑).")
    with gr.Row():
        txt = gr.Textbox(label="후원 메시지", placeholder="예) 오늘 방송 존나 웃겼다", lines=2, scale=3)
        th = gr.Slider(0.50, 0.99, value=0.90, step=0.01, label="차단 임계값(높을수록 관대)", scale=2)
    btn = gr.Button("AI 검사", variant="primary")
    verdict = gr.Label(label="판정")
    desc = gr.Markdown()
    detail = gr.JSON(label="클래스별 확률")
    btn.click(judge, [txt, th], [verdict, desc, detail])
    txt.submit(judge, [txt, th], [verdict, desc, detail])
    gr.Examples([["오늘 방송 존나 웃겼다", 0.9],
                 ["씨발 꺼져 개객기야", 0.9],
                 ["보지 마세요", 0.9],
                 ["자지러지게 웃었다", 0.9]], [txt, th])

if __name__ == "__main__":
    demo.launch()
