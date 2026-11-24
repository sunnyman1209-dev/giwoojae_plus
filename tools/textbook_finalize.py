r"""교재 객관식 묶음 확정 (SPEC_1124 A, 작업표 02).

사용: python -I tools/textbook_finalize.py <묶음> <Claude 풀이 md> [--out <보류 대조표 md>]
- draft.json(textbook_batch.py) + 세 AI 블라인드 풀이(Claude 기록 md, r1_gpt·r1_cursor result.md) + 정답 파일
- 셋 모두 정답 파일과 같으면 넣는다(src/new/<묶음>.json), 하나라도 다르면 보류 대조표에 남긴다.
- 해설은 work/<묶음>/ex.py 의 EX에서 붙인다. 근거 끝에 '출처: NCS 자료집'을 붙인다. 교재 쪽수는 verify(화면 밖)에만 둔다.
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
NAME = sys.argv[1]
B = Q / "work" / NAME
C = "①②③④"
K = "㉠㉡㉢㉣"
SOURCE = "출처: NCS 자료집"
# 세 AI 답은 정답 파일과 같지만 두 곳 이상이 '정답이 둘'이라고 본 문항 등, 사람이 보류로 정한 것: {교재 id: 이유}
HOLD = {
    "T1-17": "답은 셋 다 같으나 GPT·Cursor 모두 '보기 네 가지를 실제로 다 쓴다(가공원점=공작물 좌표계)'는 모호함 지적",
    "T2-16": "답은 셋 다 같으나 GPT·Cursor 모두 게이지 블록을 간접측정기로 보는 분류가 교재마다 달라 정답이 없을 수 있다고 지적",
}
# 해설 검토(Cursor·GPT 둘 다 지적) 뒤 고친 지문 오탈자: {교재 id: (원문 조각, 고친 조각)}. 블라인드 풀이는 원문으로 했다.
REVIEW_FIX = {
    "T6-27": ("기준길이 ±0.05로", "기준치수에 ±0.05로"),
    "T5-15": ("제작이나 무게 중심을", "체적이나 무게 중심을"),
    "T3-2": ("표시하는데", "표시하는 데"),
    "T3-4": ("연결하시오", "연결하시오."),
    "T5-20": ("3mm", "3 mm"),
    "T2-9": ("재질정보기준을", "재질 정보 기준을"),
}
# 주관식 모드 인정 답에 더할 동의어(최종판 재검토에서 Cursor·GPT 둘 다 지적): {교재 id: [답, ...]}
OPEN_EXTRA = {
    "T1-20": ["컬럼"],
    "T1-27": ["형상 측정기", "윤곽 측정기"],
    "T2-18": ["담금질", "quenching"],
    "T3-11": ["회전 컷", "회전 돌출 컷", "회전 빼기"],
    "T3-20": ["여유면 마모"],
    "T6-25": ["표면조도 측정기", "조도계", "표면 조도계", "표면거칠기계"],
}


def key_of(t, s):
    """답 글 → 비교용 열쇠. 4지 '③', 진위 'O'/'X', 연결 '①㉠②㉢…'. 4지에 번호가 둘 이상이면 '복수'."""
    s = str(s).strip()
    if t == "진위형":
        if s.startswith(("①",)) and len(s) <= 2:
            return "O"
        if s.startswith(("②",)) and len(s) <= 2:
            return "X"
        s = s.replace("○", "O").upper()
        return "O" if s.startswith("O") else "X" if s.startswith("X") else "?"
    if t == "연결형":
        s = s.translate(str.maketrans("1234", "①②③④"))
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


def main():
    draft = json.loads((B / "draft.json").read_text(encoding="utf-8"))
    ans = json.loads((SRC / "answers_1to6.json").read_text(encoding="utf-8"))
    claude = table(sys.argv[2], "T")
    gpt = table(B / "r1_gpt" / ".gpt-delegate" / "result.md", "N")
    cur = table(B / "r1_cursor" / ".cursor-delegate" / "result.md", "N")
    spec = importlib.util.spec_from_file_location("ex", B / "ex.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    EX = m.EX

    ok, held = [], []
    for n, q in enumerate(draft, 1):
        sid, t = q["src_id"], q["t"]
        right = key_of(t, ans[sid])
        got = {"Claude": claude.get(sid, ""), "GPT": gpt.get(f"N{n}", ""), "Cursor": cur.get(f"N{n}", "")}
        why = [f"{w} {a or '응답 없음'}" for w, a in got.items() if key_of(t, a) != right]
        if sid in HOLD:
            why.append(HOLD[sid])
        if why:
            held.append((q, right, got, why))
            continue
        if sid not in EX:
            raise SystemExit(f"{sid} 해설 없음")
        if sid in REVIEW_FIX:
            a, b = REVIEW_FIX[sid]
            if a not in q["stem"]:
                raise SystemExit(f"{sid} 검토 손질 원문을 찾지 못함")
            q = {**q, "stem": q["stem"].replace(a, b)}
        basis, lines, title, body = EX[sid]
        o = {"id": q["id"], "origin": "교재", "kind": "교재", "src": "new", "t": t, "stem": q["stem"]}
        ex = {"근거": basis + "\n\n" + SOURCE}
        if t == "4지선다":
            a = C.index(right)
            o.update(choices=q["choices"], ans=a, ansText=f"{C[a]} {q['choices'][a]}")
            item = q["choices"][a]
            rest = [i for i in range(4) if i != a]
            if len(lines) != 3 or any(not l.startswith(C[i]) for i, l in zip(rest, lines)):
                raise SystemExit(f"{sid} 오답 줄 번호가 보기와 맞지 않음")
            ex["오답"] = lines
        elif t == "진위형":
            o.update(ans=right, ansText=right)
            item = q["stem"][:40]
        else:
            pairs = re.findall(r"([①-④])([㉠-㉣])", right)
            o.update(left=q["left"], right=q["right"], ans=[K.index(b) for _, b in pairs],
                     ansText=", ".join(f"{a}-{b}" for a, b in pairs))
            item = q["stem"][:40]
            ex["짝"] = lines
        ex["개념"] = {"title": title, "body": body}
        if sid in OPEN_EXTRA:
            o["openExtra"] = OPEN_EXTRA[sid]
        o["tag"] = {"box": title, "item": item}
        o["ex"] = ex
        o["verify"] = {"blind": f"Claude·Cursor·GPT 블라인드 풀이가 정답 파일과 일치 (quiz_plus\\work\\{NAME})",
                       "source": f"교재 예상문제 {sid}, PDF {q['pdf']}쪽"}
        ok.append(o)

    (Q / "src" / "new" / f"{NAME}.json").write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
    L = [f"# 02 보류 대조표 (교재 1~6회차 객관식, 교사 판단 대기)", "",
         f"- 넣음 {len(ok)}문항(src/new/{NAME}.json), 보류 {len(held)}문항. 세 AI(Claude·Cursor·GPT) 블라인드 답이 모두 정답 파일과 같을 때만 넣었다.",
         "- 정답 표기: 4지는 번호, 진위형은 O/X, 연결형은 왼쪽 번호와 오른쪽 기호.", ""]
    for q, right, got, why in held:
        L.append(f"## {q['src_id']} ({q['t']}, PDF {q['pdf']}쪽)")
        L.append(f"- 지문: {q['stem']}")
        if q.get("choices"):
            L.append("- 보기: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
        if q.get("left"):
            L.append("- 왼쪽: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["left"])))
            L.append("- 오른쪽: " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(q["right"])))
        L.append(f"- 정답 파일: {right}")
        L.append("- 세 AI: " + " / ".join(f"{w} {a}" for w, a in got.items()))
        L.append(f"- 보류 이유: {'; '.join(why)}")
        L.append("")
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else str(B / "보류.md")
    Path(out).write_text("\n".join(L), encoding="utf-8")
    print(f"넣음 {len(ok)}, 보류 {len(held)} → {out}")
    for q, right, got, why in held:
        print("보류", q["src_id"], right, "|", "; ".join(why))


if __name__ == "__main__":
    main()
