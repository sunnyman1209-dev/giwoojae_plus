r"""데이터 검사 규칙 (SPEC_1124 Testing Decisions 1). check_plus.py가 쓰고, test_check_rules.py가 가짜 문항으로 시험한다.

내부 표시: 교재 예상문제·실전 모의고사에서 넣은 문항은 원본 데이터에 "origin": "교재" 또는 "실전모의"를 둔다.
교재 이론(책 1~20쪽) 공백 주제로 새로 만든 문항(작업표 05)은 "origin": "교재이론", id 'th|<책 쪽>-<번호>'.
이 값과 교재 회차-번호가 담긴 id는 화면에 나오지 않는다.
"""
import re

ORIGINS = ("교재", "실전모의", "교재이론")

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
    basis = str((q.get("ex") or {}).get("근거") or "").strip()
    if not basis:
        out.append("해설 근거 없음")
    elif "NCS 자료집" not in basis:
        out.append("근거 출처 'NCS 자료집' 없음")
    if q.get("origin") == "교재" and not re.match(r"^tb\|\d+-\d+$", str(q.get("id"))):
        out.append("id에 교재 회차-번호 없음(tb|회차-번호)")
    if q.get("origin") == "교재이론" and not re.match(r"^th\|\d+-\d+$", str(q.get("id"))):
        out.append("id에 교재 이론 쪽-번호 없음(th|쪽-번호)")
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


# 기존 590문항 해설 덮어쓰기(SPEC_1124 C, 작업표 06): src/ex_override.json = {문항 id: {해설 칸: 새 값 | null}}
# 원래 앱(quiz)의 데이터는 그대로 두고 플러스 쪽에서만 고친다. null이면 그 칸을 지운다.
EX_KEYS = ("근거", "오답", "개념", "정의", "비슷한말", "보충", "짝", "계산", "모범답안", "고친문장")


def apply_ex_override(by_id, ov):
    """by_id의 기존 문항 해설에 덮어쓰기를 적용하고 잘못된 항목을 [글, ...]로 돌려준다."""
    errs = []
    for qid, patch in ov.items():
        q = by_id.get(qid)
        if q is None:
            errs.append(f"해설 덮어쓰기: 없는 문항 {qid}")
            continue
        if q.get("src") != "old":
            errs.append(f"해설 덮어쓰기: {qid}는 기존 문항이 아님(새 문항은 src/new에서 고친다)")
            continue
        ex = dict(q.get("ex") or {})
        changed = False
        for k, v in patch.items():
            if k not in EX_KEYS:
                errs.append(f"해설 덮어쓰기: {qid} 모르는 칸 '{k}'")
                continue
            if v is None:
                changed |= k in ex
                ex.pop(k, None)
            else:
                changed |= ex.get(k) != v
                ex[k] = v
        if not str(ex.get("근거") or "").strip():
            errs.append(f"해설 덮어쓰기: {qid} 근거가 비었음")
        elif not changed:
            errs.append(f"해설 덮어쓰기: {qid} 원본과 같아 바뀐 것 없음")
        else:
            q["ex"] = ex
    return errs


def apply_ans_override(by_id, av):
    """기존 문항의 정답 글(ansText)을 고친다. 4지선다는 고친 글이 정답 보기와 같아야 한다."""
    errs = []
    for qid, txt in av.items():
        q = by_id.get(qid)
        if q is None:
            errs.append(f"정답 글 덮어쓰기: 없는 문항 {qid}")
            continue
        if q.get("src") != "old":
            errs.append(f"정답 글 덮어쓰기: {qid}는 기존 문항이 아님(새 문항은 src/new에서 고친다)")
            continue
        if not isinstance(txt, str) or not txt.strip():
            errs.append(f"정답 글 덮어쓰기: {qid} 글이 비었음")
            continue
        if txt == q.get("ansText"):
            errs.append(f"정답 글 덮어쓰기: {qid} 원본과 같아 바뀐 것 없음")
            continue
        if q.get("t") == "4지선다" and isinstance(q.get("ans"), int):
            want = "①②③④⑤"[q["ans"]] + " " + q["choices"][q["ans"]]
            if txt != want:
                errs.append(f"정답 글 덮어쓰기: {qid} 정답 보기와 다름(기대: {want})")
                continue
        q["ansText"] = txt
    return errs
