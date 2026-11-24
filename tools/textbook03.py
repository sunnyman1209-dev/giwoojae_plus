r"""교재 1~6회차 단답·계산·서술형과 7~10회차 전부를 묶음으로 정리한다 (SPEC_1124 A, 작업표 03).

사용:
  python -I tools/textbook03.py batch            → work\tb03\draft.json(정답 없음), 손질.json, r1_gpt|r1_cursor\blind.md
  python -I tools/textbook03.py finalize <Claude 풀이 md> [--out <보류 대조표 md>]
                                                 → src\new\tb03.json, 보류 대조표
- 02의 textbook_batch.py·textbook_finalize.py와 같은 흐름이다. 7~10회차는 추출 때 모두 '단답형'으로 잡혀 TYPE에서 유형을 다시 정한다.
- 1~6회차: 세 AI 답이 모두 정답 파일과 같으면 넣는다. 7~10회차: 정답 파일이 없어 세 AI 답이 모두 같으면 넣는다.
- 단답·계산·서술은 글자 비교가 안 되므로 ANS에 정답·인정 답안과 세 AI 답의 일치 판정(사람이 읽고 적음)을 둔다.
- 해설은 work\tb03\ex.py 의 EX에서 붙인다. 근거 끝에 '출처: NCS 자료집'. 교재 쪽수는 verify(화면 밖)에만 둔다.
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
Q = Path(__file__).resolve().parents[1]
_g = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=Q, capture_output=True, text=True).stdout.strip()
SRC = Path(_g).parent / "work" / "교재대조"
NAME = "tb03"
B = Q / "work" / NAME
C = "①②③④"
K = "㉠㉡㉢㉣"
SOURCE = "출처: NCS 자료집"
OBJ = {"4지선다형": "4지선다", "진위형": "진위형", "연결형": "연결형"}

# 같은 묶음 안에서 겹쳐 풀이에서 뺀 문항: {교재 id: 이유}
DUP = {
    "T10-27": "T9-27과 지문·보기가 글자까지 같음",
    "T9-36": "T9-30과 같은 내용(드라이 런 때 절삭유 상태)",
    "T8-25": "T6-32와 같은 내용(깊이봉으로 재는 치수)",
}
# 7~10회차와 1~6회차 비객관식의 유형(교재 원래 형식). 보기 ①~④가 있으면 4지선다로 본다.
TYPE = {
    "T7-2": "진위형", "T8-1": "진위형", "T9-2": "진위형", "T10-1": "진위형",
    "T7-3": "연결형",
    "T3-39": "계산형", "T3-40": "계산형", "T5-36": "계산형", "T9-35": "계산형", "T9-37": "계산형",
    "T9-38": "계산형", "T9-39": "계산형",
    "T3-33": "서술형", "T4-33": "서술형", "T4-35": "서술형", "T4-36": "서술형", "T4-37": "서술형", "T8-36": "서술형",
}
# 지문 손질: 오탈자·띄어쓰기·추출 깨짐·빈 답 칸 정리만. 원문은 손질.json에 함께 남는다.
FIX = {
    "T2-36": {"stem": "다음 (  )에 알맞은 용어를 쓰시오.\n(  )란 모 품목을 만들기 위해 필요한 조립품, 부품, 부분품, 그리고 원자재를 목록으로 구성한 것이며, 생산 활동에 필요한 제품의 모든 정보를 체계화한 데이터베이스이다."},
    "T3-39": {"stem": "피치 4 mm인 3줄 나사를 1회전시켰을 때의 리드는 몇 mm인가?"},
    "T4-31": {"stem": "CNC 코드 'G90'의 기능을 쓰시오."},
    "T5-32": {"stem": "다음 (  )에 알맞은 측정기를 쓰시오.\n(  )는 측정자의 직선 또는 원호 운동을 기계적으로 확대하여 그 움직임을 지침의 회전 변위로 변환시켜 눈금으로 읽을 수 있는 측정기이다."},
    "T5-36": {"stem": "밀링에서 절삭속도 20 m/min, 커터 지름 50 mm, 날수 12개, 1날당 이송을 0.2 mm로 할 때, 1분간 테이블 이송량은 약 몇 mm인지 구하시오. (소수점 셋째 자리에서 반올림하시오)"},
    "T5-39": {"stem": "서피스 모델링 방식으로 정의된 곡면의 일부를 절단하였을 때 나타나는 형태를 다음 중에서 골라 쓰시오.\n점, 곡선, 곡면, 평면"},
    "T6-31": {"stem": "황동(Brass)의 주성분을 쓰시오. (  +  )"},
    "T7-3": {"left": ["HSS", "P-등급 초경", "N-등급 초경"],
             "right": ["경면가공·저마찰, 비철 합금에 적합", "고속 절삭, 경도·내열성 우수", "인성 높고 형상 가공이 용이"]},
    "T7-16": {"stem": "ISO 인서트 등급 S가 권장되는 재료군은?"},
    "T7-18": {"stem": "G52의 기능 설명으로 맞는 것은?"},
    "T7-22": {"stem": "CMM 측정 시 '프로브 자격화(Qualification)'의 목적은?"},
    "T7-27": {"stem": "BT40과 CAT40의 공통점은?"},
    "T7-36": {"stem": "ISO 인서트 코드에서 코너 R을 나타내는 두 자리는 몇 번째인가? 숫자로 쓰시오."},
    "T8-27": {"stem": "G43 H05와 함께 사용해야 하는 M-코드로 옳은 것은?"},
    "T8-31": {"stem": "도면에서 기본 공차 IT6보다 한 단계 정밀한 등급은 IT(  )이다. 빈칸에 알맞은 숫자를 쓰시오."},
    "T8-35": {"stem": "측정기 교정 주기는 일반적으로 (  )개월(또는 이내) 주기로 계획한다. 빈칸에 알맞은 숫자를 쓰시오."},
    "T8-36": {"stem": "테이퍼 절삭 방법 중 심압대 편위에 의한 방법에서 편위량을 구하는 공식을 쓰시오."},
    "T8-37": {"stem": "황삭 경로에 남기는 잔삭 여유값을 영어로 S(    ) to Leave라 한다. 빈칸에 들어갈 영어 낱말을 쓰시오. (첫 글자는 S)"},
    "T9-32": {"stem": "한글 공차 기호 IT6 바로 위 등급을 숫자로 쓰시오. IT(  )"},
    "T9-33": {"stem": "BT 홀더 테이퍼는 7/24 taper이다. 분모(24)를 쓰시오."},
    "T9-35": {"stem": "다이얼게이지의 눈금 간격이 0.01 mm일 때 5눈금 이동한 거리는 몇 mm인가?"},
    "T7-2": {"stem": "수평 머시닝센터에서 Z축은 스핀들이 공작물 쪽으로 전진·후퇴하는 방향을 뜻한다."},
    "T7-20": {"stem": "기계원점 복귀 순서가 Z → X인 경우 가장 큰 이유는?"},
    "T8-30": {"stem": "절삭유 관리에서 측정하는 'Brix %'란?"},
    "T10-30": {"stem": "다음 내용이 설명하는 2.5D 가공에서 가공 방법으로 옳은 것은?\n정의된 곡선이 반드시 폐곡선이어야 하고, 깊이 절삭 시 드릴 가공을 하는 것이 일반적이었지만, 스파이럴 방식, 지그재그 방식으로 깊이를 절삭하면서 경로를 생성하는 CAM 방법이다."},
    "T9-37": {"stem": "하이트게이지로 50 mm를 측정했더니 0.05 mm 크게 나왔다면 보정값은 몇 mm인가?"},
    "T9-38": {"stem": "이송속도 F500 mm/분으로 300 mm를 가공할 때 가공 시간은 몇 초인가?"},
    "T9-39": {"stem": "폭 40 mm, 깊이 3 mm, 이송 250 mm/분일 때 재료 제거율은 몇 cm³/분인가?"},
    "T10-1": {"stem": "CNC 선반에서 ALTER 기능은 프로그램을 교체할 때 사용한다."},
    "T10-17": {"stem": "밀링 머신 조작 시 사용하지 않는 것은?"},
}
# 세 AI 답은 같거나 정답 파일과 같지만 사람이 보류로 정한 것: {교재 id: 이유}
HOLD = {
    "T7-8": "세 답은 같으나(6.3 µm) 02의 T6-10(같은 기호 ▽▽)에서 정답 파일은 1.6 µm. 교재 안에서 기준이 엇갈림",
    "T7-34": "T7-8과 같은 내용(▽▽의 Ra). 세 답 6.3이나 T6-10 정답 파일(1.6)과 엇갈림",
    "T8-34": "세 답은 같으나(1.6 µm) T6-10 정답 파일이 ▽▽를 1.6 µm로 보아 ▽▽▽의 값이 교재 안에서 엇갈림",
    "T7-27": "세 답은 같으나 Claude·GPT 모두 ③ 풀백 클램핑도 두 홀더의 공통점이라 정답이 둘이라고 지적",
    "T7-28": "세 답은 같으나 GPT·Cursor 모두 농도 점검의 주된 목적은 적정 농도 유지라 맞는 보기가 없을 수 있다고 지적",
    "T8-19": "세 답은 같으나 GPT·Cursor 모두 ① 고속 안정성도 장점이 될 수 있다고 지적(Claude도 확신 낮음)",
    "T8-35": "세 답은 12이나 GPT·Cursor 모두 6개월 등도 가능해 하나로 정해지지 않는다고 지적",
    "T9-30": "세 답은 같으나 GPT·Cursor 모두 드라이 런은 절삭유 상태를 정하지 않아(기계 설정) 정답이 없을 수 있다고 지적",
    "T9-32": "'한글 공차 기호', '바로 위 등급'이 모호(GPT: 5 또는 7). T8-31과 같은 내용",
    "T7-37": "TAG는 세 글자라 지문의 '영어 4글자'와 맞지 않음(GPT 지적), Cursor는 글자 수에 맞춰 LOCK",
    "T7-21": "세 답은 ②이나 GPT·Cursor 모두 실제 첫 단계는 작업자 통보·기계 정지라 맞는 보기가 없을 수 있다고 지적(블라인드 풀이와 해설 검토 둘 다)",
    "T9-33": "지문에 답(24)이 드러나 있어 문항 구실을 못 함(GPT도 지적)",
}
# 해설 검토(두 곳 이상 지적) 뒤 고친 지문: {교재 id: (원문 조각, 고친 조각)}. 블라인드 풀이는 원문으로 했다.
REVIEW_FIX = {
    # 블라인드 풀이 때 GPT 지적: 'S(    )' 꼴과 '낱말 전체를 쓰라'는 지시가 맞지 않음
    "T8-37": [("영어로 S(    ) to Leave라 한다. 빈칸에 들어갈 영어 낱말을 쓰시오. (첫 글자는 S)", "영어로 '(    ) to Leave'라 한다. 빈칸에 들어갈 영어 낱말을 쓰시오. (S로 시작한다)")],
    # 해설 검토 1차: 둘 다 지적
    "T10-8": [("엔드밀 가공경로와 사이의 간격을", "이웃한 엔드밀 가공 경로 사이의 간격을")],
    "T9-21": [("공차구멍 참고치수를 도면에", "참고 치수를 도면에")],
    # 해설 검토 1차: 하나만 지적(띄어쓰기)
    "T4-37": [("교정주기를", "교정 주기를")],
    "T7-23": [("도면검토 단계", "도면 검토 단계")],
    "T8-16": [("도면검토 단계", "도면 검토 단계")],
    # 최종판 재검토: GPT 하나, '눈금폭'은 눈금선 너비로 읽힘(뜻은 그대로)
    "T9-25": [("눈금폭이 0.01 mm일 때", "한 눈금이 0.01 mm일 때")],
}
# 4지 주관식 모드 인정 답 동의어: {교재 id: [답, ...]}
OPEN_EXTRA = {
    "T7-16": ["내열 합금", "초내열 합금", "내열 초합금", "HRSA", "티타늄 합금", "티타늄", "내열 합금·티타늄"],
    "T8-8": ["150 mm/분", "분당 150 mm", "150 mm per min"],
    "T8-13": ["리지드 탭", "리지드 태핑", "리지드 탭 모드", "동기 탭", "rigid tap", "Rigid Tapping", "동기 태핑", "강성 탭"],
    "T8-29": ["좌표 회전", "좌표계 회전 지령"],
    "T8-30": ["절삭유 농도", "희석 농도"],
    "T9-25": ["0.3 mm", "0.3", "0.30"],
}


def parse(x):
    """추출 글 → 지문과 보기. 빈 답 칸 '( )'와 줄바꿈을 정리한다."""
    t = x["text"].replace("–", "-").replace("“", "'").replace("”", "'").replace("‘", "'").replace("’", "'")
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    stem, rest = [], []
    for l in lines:
        (rest if rest or re.match(r"^[①-④]", l) else stem).append(l)
    stem = " ".join(stem)
    stem = re.sub(r"(?<=[가-힣])\s+(?=[를을이가은는의]\b)", "", stem)  # 줄바꿈으로 끊긴 '깊이 를'
    stem = re.sub(r"\(\s*\+?\s*\)\s*$", "", stem.strip()).strip()
    stem = re.sub(r"\s+", " ", stem)
    ch = []
    for l in rest:
        if re.match(r"^[①-④]", l):
            if len(ch) == 4:
                break
            ch.append(re.sub(r"^[①-④]\s*", "", l).strip())
    q = {"stem": stem}
    if ch:
        q["choices"] = ch
    return q


def kind(x):
    if x["r"] <= 6:
        return OBJ.get(x["sec"]) or TYPE.get(x["id"], "단답형")
    if x["id"] in TYPE:
        return TYPE[x["id"]]
    return "4지선다" if re.search(r"^①", x["text"], re.M) else "단답형"


def batch():
    items = {x["id"]: x for x in json.loads((SRC / "items.json").read_text(encoding="utf-8"))}
    ins = json.loads((SRC / "merged.json").read_text(encoding="utf-8"))["넣기"]
    out, fixlog, skipped = [], [], []
    for iid in ins:
        x = items[iid]
        t = kind(x)
        if x["r"] <= 6 and t in OBJ.values():
            continue  # 02에서 다룸
        if iid in DUP:
            skipped.append({"id": iid, "why": "같은 묶음 안 중복: " + DUP[iid]})
            continue
        if x.get("fig"):
            skipped.append({"id": iid, "why": "그림 문항"})
            continue
        q = parse(x)
        if t == "진위형":
            q["stem"] = re.sub(r"\s*\(\s*\)\s*$", "", q["stem"])
        for f, v in FIX.get(iid, {}).items():
            fixlog.append({"id": iid, "field": f, "원문": q.get(f), "고침": v})
            q[f] = v
        if t != "4지선다":
            q.pop("choices", None)
        q = {"id": f"tb|{x['r']}-{x['n']}", "src_id": iid, "t": t, "pdf": x["pdf"], **q}
        if t == "4지선다" and len(q.get("choices") or []) != 4:
            raise SystemExit(f"{iid} 보기 {len(q.get('choices') or [])}개")
        if t == "연결형" and len(q["left"]) != len(q["right"]):
            raise SystemExit(f"{iid} 연결 양쪽 개수 다름")
        out.append(q)
    B.mkdir(parents=True, exist_ok=True)
    (B / "draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (B / "손질.json").write_text(json.dumps({"fix": fixlog, "skip": skipped}, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 문제지 (정답 없음)", ""]
    for n, q in enumerate(out, 1):
        L.append(f"N{n}. [{q['t']}] {q['stem']}")
        if q["t"] == "4지선다":
            L.append("    " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
        elif q["t"] == "진위형":
            L.append("    O / X")
        elif q["t"] == "연결형":
            L.append("    왼쪽: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["left"])))
            L.append("    오른쪽: " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(q["right"])))
        L.append("")
    task = """`blind.md`의 문항(N1~)을 기계가공·CNC·CAD/CAM·측정·제도의 일반 지식으로 직접 풀어라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- 최종 응답은 표 하나만: | 번호 | 답 | 근거(한 줄) | 다른 답도 맞을 수 있는가 | 오류·모호함 |
- 모든 번호를 채운다. 4지선다는 번호(①~④)와 보기 글, 진위형은 O 또는 X, 연결형은 '①-㉠, ②-㉡' 꼴.
- 단답형은 답 낱말, 계산형은 값과 단위(풀이 식 한 줄), 서술형은 핵심을 한두 문장으로 쓴다.
- 단답형은 '다른 답' 칸에 같은 뜻으로 인정할 만한 다른 표기(우리말·영어·약어)를 모두 적는다.
- 정답이 둘 이상이거나 보기 중 정답이 없을 수 있으면 반드시 '다른 답' 칸에 적는다. 확신이 없으면 '확신 낮음'.
- 지문에 오류(숫자·글자 수·용어가 맞지 않음, 답이 지문에 드러남 등)가 있으면 '오류·모호함' 칸에 적는다.
"""
    ag = """# 블라인드 풀이 폴더

컴퓨터응용가공산업기사(과정평가형) 필기 문항을 정답 없이 풀어 보는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `blind.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
    for name, sub in (("r1_gpt", ".gpt-delegate"), ("r1_cursor", ".cursor-delegate")):
        d = B / name
        (d / sub).mkdir(parents=True, exist_ok=True)
        (d / "blind.md").write_text("\n".join(L), encoding="utf-8")
        (d / "AGENTS.md").write_text(ag, encoding="utf-8")
        (d / sub / "task.md").write_text(task, encoding="utf-8")
    from collections import Counter
    print(f"{len(out)}문항 {dict(Counter(q['t'] for q in out))}, 손질 {len(fixlog)}건, 제외 {len(skipped)}")


def key_of(t, s):
    """답 글 → 비교용 열쇠(4지·진위·연결만). 4지에 번호가 둘 이상이면 '복수'."""
    s = str(s).strip()
    if t == "진위형":
        s = s.replace("○", "O").upper()
        return "O" if s.startswith("O") else "X" if s.startswith("X") else "?"
    if t == "연결형":
        s = s.translate(str.maketrans("123", "①②③"))
        return "".join(a + b for a, b in re.findall(r"([①-④])\s*-\s*([㉠-㉣])", s))
    nums = set(re.findall(r"[①-④]", s))
    return "복수" if len(nums) > 1 else (nums.pop() if nums else "?")


def table(path, prefix):
    """md 표에서 {번호: 답 칸}."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\|\s*({prefix}[\w-]+)\s*\|([^|]*)\|", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def finalize():
    draft = json.loads((B / "draft.json").read_text(encoding="utf-8"))
    ans16 = json.loads((SRC / "answers_1to6.json").read_text(encoding="utf-8"))
    claude = table(sys.argv[2], "T")
    gpt = table(B / "r1_gpt" / ".gpt-delegate" / "result.md", "N")
    cur = table(B / "r1_cursor" / ".cursor-delegate" / "result.md", "N")
    m = load(B / "ex.py", "ex")
    EX, ANS = m.EX, m.ANS   # ANS: 단답·계산·서술의 정답과 세 AI 일치 판정, 4지·진위·연결 7~10회차의 사람 확인 메모

    ok, held = [], []
    for n, q in enumerate(draft, 1):
        sid, t = q["src_id"], q["t"]
        r = int(sid[1:].split("-")[0])
        got = {"Claude": claude.get(sid, ""), "GPT": gpt.get(f"N{n}", ""), "Cursor": cur.get(f"N{n}", "")}
        a = ANS.get(sid, {})
        why = []
        if t in ("4지선다", "진위형", "연결형"):
            keys = {w: key_of(t, v) for w, v in got.items()}
            if r <= 6:
                right = key_of(t, ans16[sid])
                why += [f"{w} {got[w] or '응답 없음'}" for w, k in keys.items() if k != right]
            else:
                right = keys["Claude"]
                if len(set(keys.values())) != 1 or "?" in keys.values() or "복수" in keys.values():
                    why.append("세 AI 답이 같지 않음")
        else:
            right = a.get("ansText")
            why += [f"{w} {got[w] or '응답 없음'}" for w in got if not a.get("match", {}).get(w)]
            if r <= 6 and not a.get("file_ok"):
                why.append(f"정답 파일 {ans16.get(sid)}과 다름")
        if sid in HOLD:
            why.append(HOLD[sid])
        if why:
            held.append((q, right if r > 6 or t not in OBJ.values() else right, got, why, ans16.get(sid) if r <= 6 else None))
            continue
        if sid not in EX:
            raise SystemExit(f"{sid} 해설 없음")
        if sid in REVIEW_FIX:
            for x, y in REVIEW_FIX[sid]:
                if x not in q["stem"]:
                    raise SystemExit(f"{sid} 검토 손질 원문을 찾지 못함")
                q = {**q, "stem": q["stem"].replace(x, y)}
        e = EX[sid]
        o = {"id": q["id"], "origin": "교재", "kind": "교재", "src": "new", "t": t, "stem": q["stem"]}
        ex = {"근거": e["근거"] + "\n\n" + SOURCE}
        if t == "4지선다":
            ai = C.index(right)
            o.update(choices=q["choices"], ans=ai, ansText=f"{C[ai]} {q['choices'][ai]}")
            item = q["choices"][ai]
            rest = [i for i in range(4) if i != ai]
            if len(e["오답"]) != 3 or any(not l.startswith(C[i]) for i, l in zip(rest, e["오답"])):
                raise SystemExit(f"{sid} 오답 줄 번호가 보기와 맞지 않음")
            ex["오답"] = e["오답"]
        elif t == "진위형":
            o.update(ans=right, ansText=right)
            item = q["stem"][:40]
        elif t == "연결형":
            pairs = re.findall(r"([①-④])([㉠-㉣])", right)
            o.update(left=q["left"], right=q["right"], ans=[K.index(b) for _, b in pairs],
                     ansText=", ".join(f"{x}-{y}" for x, y in pairs))
            item = q["stem"][:40]
            ex["짝"] = e["짝"]
        elif t == "단답형":
            o.update(ans=None, ansText=a["ansText"], accept=a["accept"])
            item = a["ansText"]
        elif t == "계산형":
            o.update(ans=None, value=a["value"], unit=a["unit"], ansText=f"{a['value']} {a['unit']}")
            item = "계산:" + a["unit"]
            ex["계산"] = e["계산"]
            if a.get("calc"):
                o["calc"] = a["calc"]
        else:  # 서술형
            o.update(ans=None, ansText=a["ansText"], keywords=a["keywords"])
            item = q["stem"][:40]
            ex["모범답안"] = e["모범답안"]
        if e.get("비슷한말"):
            ex["비슷한말"] = e["비슷한말"]
        ex["개념"] = {"title": e["title"], "body": e["body"]}
        if sid in OPEN_EXTRA:
            o["openExtra"] = OPEN_EXTRA[sid]
        o["tag"] = {"box": e.get("box") or e["title"], "item": e.get("item") or item}
        o["ex"] = ex
        how = "정답 파일과 일치" if r <= 6 else "세 답이 서로 일치(정답 파일 없음)"
        o["verify"] = {"blind": f"Claude·Cursor·GPT 블라인드 풀이가 {how} (quiz_plus\\work\\{NAME})",
                       "source": f"교재 예상문제 {sid}, PDF {q['pdf']}쪽"}
        ok.append(o)

    (Q / "src" / "new" / f"{NAME}.json").write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    L = ["# 03 보류 대조표 (교재 1~6회차 단답·계산·서술형, 7~10회차 전부, 교사 판단 대기)", "",
         f"- 넣음 {len(ok)}문항(src/new/{NAME}.json, 유형별 {dict(Counter(o['t'] for o in ok))}), 보류 {len(held)}문항.",
         "- 1~6회차는 세 AI(Claude·Cursor·GPT) 블라인드 답이 모두 정답 파일과 같을 때, 7~10회차는 세 답이 모두 같을 때만 넣었다.",
         "- 단답·계산·서술은 뜻으로 비교했다(표기만 다른 것은 같다고 봄).", ""]
    for q, right, got, why, filed in held:
        L.append(f"## {q['src_id']} ({q['t']}, PDF {q['pdf']}쪽)")
        L.append(f"- 지문: {q['stem']}".replace("\n", " / "))
        if q.get("choices"):
            L.append("- 보기: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
        if q.get("left"):
            L.append("- 왼쪽: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["left"])))
            L.append("- 오른쪽: " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(q["right"])))
        L.append(f"- 정답 파일: {filed if filed is not None else '없음(7~10회차)'}")
        L.append("- 세 AI: " + " / ".join(f"{w} {v}" for w, v in got.items()))
        L.append(f"- 보류 이유: {'; '.join(why)}")
        L.append("")
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else str(B / "보류.md")
    Path(out).write_text("\n".join(L), encoding="utf-8")
    print(f"넣음 {len(ok)} {dict(Counter(o['t'] for o in ok))}, 보류 {len(held)} → {out}")
    for q, right, got, why, filed in held:
        print("보류", q["src_id"], "|", "; ".join(why))


if __name__ == "__main__":
    {"batch": batch, "finalize": finalize}[sys.argv[1]]()
