r"""실전 모의고사 묶음 확정 (SPEC_1124 A, 작업표 04). tools/textbook_finalize.py와 같은 흐름.

사용: python -I tools/practice_finalize.py [--out <보류 대조표 md>]
- draft.json(practice_batch.py) + 세 AI 블라인드 풀이(work/tb04/claude_blind.md, r1_gpt·r1_cursor result.md) + 원본 정답(items.json의 given)
- 셋 모두 원본 정답과 같으면 넣는다(src/new/tb04.json), 하나라도 다르면 보류 대조표에 남긴다.
  계산형은 앱 채점과 같이 원본 정답의 1% 안이면 같은 답으로 본다.
- 해설은 work/tb04/ex.py 의 EX(계산형 값·단위는 CALC)에서 붙인다. 근거 끝에 '출처: NCS 자료집'.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
Q = Path(__file__).resolve().parents[1]
B = Q / "work" / "tb04"
NAME = "tb04"
C = "①②③④"
K = "㉠㉡㉢㉣"
SOURCE = "출처: NCS 자료집"
# 답은 셋 다 같으나 두 곳 이상이 '정답이 둘이거나 없을 수 있다'고 본 문항: {id: 이유}
HOLD = {
    "mock|1-47": "답은 셋 다 9.93°(원본 9.95°, 1% 안)이나 Claude·GPT 모두 '여유각 공식(어느 거리 기준인지)이 지문에 없어 답이 하나로 정해지지 않는다'고 지적",
    "mock|2-34": "답은 셋 다 같으나 Cursor·GPT 모두 '로터리 테이블은 고정 장치보다 분할 장치라 ④도 답이 될 수 있다'고 지적(Claude도 같은 점 언급)",
    "mock|2-36": "답은 셋 다 같으나 세 AI 모두 확신 낮음, '캡 가공'이 정의되지 않은 용어라 정답이 없을 수 있다고 지적",
}
# 지문 손질 뒤(블라인드 풀이 뒤) 해설 단계에서 더 고친 것: {id: (원문 조각, 고친 조각)}
REVIEW_FIX = {
    "mock|1-46": ("길이 120mm의 피삭재를 주축 회전수 900rpm, 이송 0.3mm/rev 조건으로 절삭할 때 가공에 소요되는 시간을 구하시오.",
                  "길이 120 mm의 피삭재를 주축 회전수 900 rpm, 이송 0.3 mm/rev 조건으로 절삭할 때 가공에 소요되는 시간[초]을 구하시오."),
    "mock|2-30": ("원호를 가공하는 데 시점에서 원호의 중심까지의 거리를 지정하는 데 X성분의 어드레스는?",
                  "원호를 가공할 때 시점에서 원호 중심까지 거리의 X성분을 지정하는 어드레스는?"),
}


def num(s):
    """'26.67 초', '0.44 min' 같은 답 글 → 초 단위 값(분이면 60배). 숫자가 없으면 None."""
    s = str(s)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    v = float(m.group())
    tail = s[m.end():m.end() + 6]
    return v * 60 if re.match(r"\s*(min|분)", tail) else v


def key_of(t, s):
    s = str(s).strip()
    if t == "진위형":
        s = s.replace("○", "O").upper()
        return "O" if s.startswith("O") else "X" if s.startswith("X") else "?"
    if t == "연결형":
        s = s.translate(str.maketrans("1234", "①②③④"))
        return "".join(a + b for a, b in re.findall(r"([①-④])\s*-\s*([㉠-㉣])", s))
    if t == "계산형":
        return num(s)
    nums = set(re.findall(r"[①-④]", s))
    return "복수" if len(nums) > 1 else (nums.pop() if nums else "?")


def same(t, a, b):
    if t == "계산형":
        return a is not None and b is not None and abs(a - b) <= abs(b) * 0.01
    return a == b


def table(path, prefix="N"):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\|\s*({prefix}\d+)\s*\|([^|]*)\|", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main():
    draft = json.loads((B / "draft.json").read_text(encoding="utf-8"))
    given = {x["id"]: x["given"] for x in json.loads((B / "items.json").read_text(encoding="utf-8"))}
    sols = {"Claude": table(B / "claude_blind.md"),
            "GPT": table(B / "r1_gpt" / ".gpt-delegate" / "result.md"),
            "Cursor": table(B / "r1_cursor" / ".cursor-delegate" / "result.md")}
    spec = importlib.util.spec_from_file_location("ex", B / "ex.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    EX, CALC = m.EX, getattr(m, "CALC", {})

    ok, held = [], []
    for n, q in enumerate(draft, 1):
        iid, t = q["id"], q["t"]
        right = key_of(t, given[iid]["ans"])
        got = {w: s.get(f"N{n}", "") for w, s in sols.items()}
        why = [f"{w} {a or '응답 없음'}" for w, a in got.items() if not same(t, key_of(t, a), right)]
        if iid in HOLD:
            why.append(HOLD[iid])
        if why:
            held.append((q, given[iid]["ans"], got, why))
            continue
        if iid not in EX:
            raise SystemExit(f"{iid} 해설 없음")
        if iid in REVIEW_FIX:
            a, b = REVIEW_FIX[iid]
            if a not in q["stem"]:
                raise SystemExit(f"{iid} 검토 손질 원문을 찾지 못함")
            q = {**q, "stem": q["stem"].replace(a, b)}
        basis, lines, title, body = EX[iid]
        o = {"id": iid, "origin": "실전모의", "kind": "실전모의", "src": "new", "t": t, "stem": q["stem"]}
        ex = {"근거": basis + "\n\n" + SOURCE}
        if t == "4지선다":
            a = C.index(right)
            o.update(choices=q["choices"], ans=a, ansText=f"{C[a]} {q['choices'][a]}")
            item = q["choices"][a]
            rest = [i for i in range(4) if i != a]
            if len(lines) != 3 or any(not l.startswith(C[i]) for i, l in zip(rest, lines)):
                raise SystemExit(f"{iid} 오답 줄 번호가 보기와 맞지 않음")
            ex["오답"] = lines
        elif t == "진위형":
            o.update(ans=right, ansText=right)
            item = q["stem"][:40]
        elif t == "계산형":
            value, unit = CALC[iid]
            if not same(t, value, right):
                raise SystemExit(f"{iid} 해설 값 {value}이 원본 정답 {right}과 1% 넘게 다름")
            o.update(value=value, unit=unit, ans=None, ansText=f"{value:g} {unit}")
            item = "계산:" + unit
        else:
            raise SystemExit(f"{iid} 처리하지 않는 유형 {t}")
        ex["개념"] = {"title": title, "body": body}
        o["tag"] = {"box": title, "item": item}
        o["ex"] = ex
        o["verify"] = {"blind": f"Claude·Cursor·GPT 블라인드 풀이가 원본 해설의 정답과 일치 (quiz_plus 작업틀 work\\{NAME})",
                       "source": f"외부평가 실전 모의고사 {iid.split('|')[1].replace('-', '회 ')}번"}
        ok.append(o)

    (Q / "src" / "new" / f"{NAME}.json").write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# 04 보류 대조표 (외부평가 실전 모의고사, 교사 판단 대기)", "",
         f"- 넣음 {len(ok)}문항(src/new/{NAME}.json), 보류 {len(held)}문항. 세 AI(Claude·Cursor·GPT) 블라인드 답이 모두 원본 해설의 정답과 같을 때만 넣었다.",
         "- 계산형은 앱 채점과 같이 원본 정답의 1% 안이면 같은 답으로 보았다.",
         "- 원본 정답 표기: 4지는 번호, 진위형은 O/X, 계산형은 값과 단위.", ""]
    for q, right, got, why in held:
        L.append(f"## {q['id']} ({q['t']})")
        L.append(f"- 지문: {q['stem']}")
        if q.get("choices"):
            L.append("- 보기: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
        L.append(f"- 원본 정답: {right}")
        L.append("- 세 AI: " + " / ".join(f"{w} {a}" for w, a in got.items()))
        L.append(f"- 보류 이유: {'; '.join(why)}")
        L.append("")
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else str(B / "보류.md")
    Path(out).write_text("\n".join(L), encoding="utf-8")
    print(f"넣음 {len(ok)}, 보류 {len(held)} → {out}")
    for q, right, got, why in held:
        print("보류", q["id"], right, "|", "; ".join(why))


if __name__ == "__main__":
    main()
