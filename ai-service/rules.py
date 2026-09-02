"""
규칙(정규식) 1차 필터 — 명백한 '우회 욕설'만 좁게 차단.

- 목적: AI가 놓치기 쉬운 우회(시★발, ㅅㅂ, tlqkf 등)를 싸게 잡는다.
- 사용성 우선: 부분매칭은 최소화(정상어 오탐 유발 금지). 애매한 건 AI에게 넘긴다.
- 라이선스: KoreanCursewordRegex(CC0)의 패턴을 아래 CURSE_REGEX 에 붙여넣어 사용.
  https://github.com/curioustorvald/KoreanCursewordRegex  (CC0, 상업적 사용 자유)
"""
import re

# 간단 정규화(구분자·반복 제거) — index.html normalize의 축약판
_SEP = re.compile(r"[\s_\-.,~!@#$%^&*()\[\]{}<>|/\\+=:;'\"`?★☆♥♡●◆■□·・…]")
def normalize(text: str) -> str:
    t = (text or "")
    t = _SEP.sub("", t)
    t = re.sub(r"(.)\1{2,}", r"\1", t)   # 3회 이상 반복 축약(ㅋㅋㅋ→ㅋ)
    return t

# ── 여기에 KoreanCursewordRegex(CC0) 전체 패턴을 붙여넣으세요 ──
# 아래는 자리표시용 최소 예시(반드시 실제 패턴으로 교체).
CURSE_REGEX = re.compile(
    r"(시[\s]*발|씨[\s]*발|병[\s]*신|개[\s]*새[\s]*끼|ㅅㅂ|tlqkf)"
)

def rule_block(text: str) -> bool:
    """규칙상 '명백'하면 True(차단). 좁게 유지."""
    if not text:
        return False
    raw = text
    norm = normalize(text)
    return bool(CURSE_REGEX.search(raw) or CURSE_REGEX.search(norm))
