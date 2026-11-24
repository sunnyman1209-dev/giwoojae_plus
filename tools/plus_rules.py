r"""데이터 검사 규칙 (SPEC_1124 Testing Decisions 1). check_plus.py가 쓰고, test_check_rules.py가 가짜 문항으로 시험한다.

내부 표시: 교재 예상문제·실전 모의고사에서 넣은 문항은 원본 데이터에 "origin": "교재" 또는 "실전모의"를 둔다.
이 값과 교재 회차-번호가 담긴 id는 화면에 나오지 않는다.
"""
import re

ORIGINS = ("교재", "실전모의")

# 학생 화면에 보이는 필드: 지문, 보기, 연결형 양쪽, 정답 글, 인정 답안, 해설 전체
VISIBLE = ("stem", "choices", "left", "right", "ansText", "accept", "ex", "exChoice")
LEAK = re.compile(r"교재|예상\s*문제|실전\s*모의|\d+\s*쪽|\bp\.\s*\d+|\d+\s*회차|\d+\s*회\s*[-–]?\s*\d+\s*번|\d+\s*회\s*[-–]\s*\d+")
# 해설의 원본 지칭: '문제', '보기 ③', '③번·2번', '문항'
REF = re.compile(r"문제|문항|보기\s*[①-⑥\d]|(?<![\d.])[①-⑥\d]+\s*번(?!째)")


def texts(x):
    """필드 값 안의 글을 모두 꺼낸다(문자열·목록·사전)."""
    if isinstance(x, str):
        return [x]
    if isinstance(x, list):
        return [s for v in x for s in texts(v)]
    if isinstance(x, dict):
        return [s for v in x.values() for s in texts(v)]
    return []


def is_textbook(q):
    return q.get("origin") in ORIGINS


def textbook_errors(q):
    """교재·실전모의 문항에 정답, 근거, (단답형) 인정 답안이 있는가. 문제마다 한 줄."""
    if not is_textbook(q):
        return []
    out, t = [], q.get("t")
    if t in ("4지선다", "진위형"):
        has = q.get("ans") is not None
    elif t == "연결형":
        has = bool(q.get("ans"))
    elif t == "계산형":
        has = q.get("value") is not None and bool(str(q.get("unit") or "").strip())
    else:  # 단답형, 서술형
        has = bool(str(q.get("ansText") or "").strip())
    if not has:
        out.append("정답 없음")
    if not str((q.get("ex") or {}).get("근거") or "").strip():
        out.append("해설 근거 없음")
    if t == "단답형" and not [a for a in (q.get("accept") or []) if str(a).strip()]:
        out.append("인정 답안 없음")
    return out


def leaks(q):
    """화면에 보이는 글에 드러난 출처: [(필드, 찾은 글), ...]"""
    out = []
    for f in VISIBLE:
        for s in texts(q.get(f)):
            for m in LEAK.finditer(s):
                out.append((f, m.group()))
    return out


def refs(q):
    """해설에 남은 원본 지칭: [찾은 글, ...]"""
    return [m.group() for s in texts(q.get("ex")) for m in REF.finditer(s)]
