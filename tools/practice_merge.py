r"""실전 모의고사 중복 판정(Claude·Cursor·GPT)을 합쳐 판정표를 만든다 (SPEC_1124 A, 작업표 04). tools/textbook_merge.py와 같은 규칙.

사용: python -I tools/practice_merge.py <판정표 md 경로>
- 입력: work/tb04/items.json, work/tb04/judge_claude.md, judge_cursor.md, judge_gpt.md (표: | M1-1 | 판정 | 문제은행 id | 근거 |)
- 합치기: 두 곳 이상 같음·개념같음 -> 있음(제외), 두 곳 이상 판정불가(그림 문항은 하나라도) -> 판정불가, 두 곳 이상 다름 -> 없음(넣기), 나머지 갈림
- 앱에 없음이어도 교재 예상문제의 같은 문항이 작업표 03(1~6회 단답·계산, 7~10회)에서 들어갈 예정이면 03에 맡긴다(이중 입력 방지).
- 출력: work/tb04/merged.json, 판정표 md
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
Q = Path(__file__).resolve().parents[1]
_g = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=Q, capture_output=True, text=True).stdout.strip()
TB = Path(_g).parent / "work" / "교재대조"
D = Q / "work" / "tb04"
TB02 = ("4지형", "4지선다형", "진위형", "연결형")


def load(p):
    r = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        c = [x.strip(" `*") for x in ln.strip().strip("|").split("|")]
        if len(c) >= 2 and re.fullmatch(r"M[12]-\d{1,2}", c[0]):
            v = c[1].replace(" ", "")
            v = "개념같음" if "개념" in v else "같음" if v.startswith("같음") else "판정불가" if "불가" in v else "다름"
            r[c[0]] = (v, c[2] if len(c) > 2 else "-", c[3] if len(c) > 3 else "")
    return r


def sq(s):
    return re.sub(r"[^가-힣A-Za-z0-9]", "", str(s))


def bg(s):
    s = sq(s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main():
    items = json.loads((D / "items.json").read_text(encoding="utf-8"))
    J = {k: load(D / f"judge_{k.lower()}.md") for k in ("Claude", "Cursor", "GPT")}
    for k, v in J.items():
        print(k, len(v), Counter(x[0] for x in v.values()))
    # 교재 예상문제 중 작업표 03이 넣을 문항(merged '넣기'이고 1~6회 객관식이 아닌 것)
    titems = json.loads((TB / "items.json").read_text(encoding="utf-8"))
    tins = set(json.loads((TB / "merged.json").read_text(encoding="utf-8"))["넣기"])
    t03 = [(x["id"], bg(x["text"])) for x in titems if x["id"] in tins and (x["r"] > 6 or x["sec"] not in TB02)]
    res = {"있음": [], "없음": [], "판정불가": [], "갈림": [], "03에 맡김": []}
    rows = []
    for it in items:
        lab = "M" + it["id"].split("|")[1]
        vs = {k: J[k].get(lab, ("응답 없음", "-", "")) for k in J}
        ov = sum(v[0] in ("같음", "개념같음") for v in vs.values())
        na = sum(v[0] == "판정불가" for v in vs.values())
        df = sum(v[0] == "다름" for v in vs.values())
        note = ""
        if ov >= 2:
            cat = "있음"
        elif na >= 2 or (it["fig"] and na >= 1):
            cat = "판정불가"
        elif df >= 2:
            cat = "없음"
            b = bg(it["stem"] + " ".join(it.get("choices") or it.get("left", []) + it.get("right", [])))
            best = max(((len(b & o) / max(1, min(len(b), len(o))), k) for k, o in t03), default=(0, ""))
            if best[0] >= 0.85:
                cat, note = "03에 맡김", f"교재 {best[1]}와 같음({best[0]:.2f})"
        else:
            cat = "갈림"
        res[cat].append(it["id"])
        rows.append((it, lab, vs, cat, note))
    print({k: len(v) for k, v in res.items()})
    (D / "merged.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# 04 실전 모의고사 중복 판정표", "",
         "- 대상: 외부평가 실전 모의고사 1회(종합) 50문항, 2회(CNC밀링) 50문항, 문제은행 1068문항(spec-1124, 02·07 병합 뒤)",
         "- 판정: Claude, Cursor(auto), GPT가 각각 '같음 / 개념같음 / 다름 / 판정불가'로 판정(원판정: quiz_plus 작업틀 work/tb04/judge_*.md)",
         "- 합치기(tools/practice_merge.py, textbook_merge.py와 같은 규칙): 두 곳 이상 같음·개념같음이면 있음, 두 곳 이상 판정불가(그림 문항은 하나라도)면 판정불가, 두 곳 이상 다름이면 없음, 나머지 갈림",
         "- '03에 맡김': 앱에 없지만 교재 예상문제의 같은 문항이 작업표 03(1~6회 단답·계산, 7~10회)에서 들어갈 예정이라 04에서는 넣지 않는다.",
         "- 문제은행 id의 세로선은 '/'로 적었다.", "",
         "| 구분 | 문항 수 |", "|---|---|"] + [f"| {k} | {len(v)} |" for k, v in res.items()] + [""]
    for cat in res:
        L += [f"## {cat} ({len(res[cat])})", "", "| 문항 | 지문 | Claude | Cursor | GPT | 비고 |", "|---|---|---|---|---|---|"]
        for it, lab, vs, c, note in rows:
            if c != cat:
                continue
            t = re.sub(r"\s+", " ", it["stem"])[:60].replace("|", "/")
            cell = lambda v: f"{v[0]} {v[1] if v[1] not in ('-', '') else ''}".strip().replace("|", "/")
            L.append(f"| {lab} | {t} | " + " | ".join(cell(v) for v in vs.values()) + f" | {note} |")
        L.append("")
    Path(sys.argv[1]).write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
