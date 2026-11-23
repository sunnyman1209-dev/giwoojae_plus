"""work\\<묶음>\\items_*.py → work\\<묶음>\\draft.json, 겹침 검사, 두 AI용 블라인드 지시문.
사용: make_batch.py <묶음 이름>
- 개념 상자·basis는 원본 문항 해설(questions.json ex)에서 자동으로 붙인다.
- 4지 오답 이유는 원본 개념 상자 표 줄/오답 줄에서 그 보기 글자가 나오는 줄을 찾아 붙인다(없으면 '확인 필요' 표시).
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
Z = Q.parent / "quiz"
B = Q / "work" / sys.argv[1]
OLD = {q["id"]: q for q in json.loads((Z / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]}
NEW = []
for f in (Q / "src" / "new").glob("*.json"):
    NEW += json.loads(f.read_text(encoding="utf-8"))
C = "①②③④"


def sq(s):
    return re.sub(r"[\s·()\[\]./-]", "", str(s)).lower()


items = []
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
for f in sorted(B.glob("items_*.py")):
    if ONLY and f.stem not in ONLY:
        continue
    spec = importlib.util.spec_from_file_location(f.stem, f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    items += [x for x in m.ITEMS if x[0] not in getattr(m, "DROP", set())]

out, warn = [], []
ids = set()
for it in items:
    (iid, frm, kind, t, stem, choices, ans, accept, value, unit, item, basis_txt) = it[:12]
    manual = it[12] if len(it) > 12 else None
    assert iid not in ids, iid
    ids.add(iid)
    src = OLD[frm]
    ex0 = src.get("ex", {})
    box = ex0.get("개념", {}).get("title") or f"개념 상자 없음: {item}"
    body = ex0.get("개념", {}).get("body", [])
    lines = body + ex0.get("오답", []) + [ex0.get("근거", "")]
    q = {"id": iid, "from": frm, "kind": kind, "src": "new", "t": t, "stem": stem,
         "tag": {"box": box, "item": item}}
    if t == "4지선다":
        q["choices"], q["ans"] = choices, ans
        q["ansText"] = f"{C[ans]} {choices[ans]}"
        exc = []
        for i, c in enumerate(choices):
            if i == ans:
                continue
            hit = next((l for l in lines if sq(c) and sq(c) in sq(l) and not sq(choices[ans]) in sq(l)), None)
            if hit is None:
                hit = next((l for l in lines if sq(c) and sq(c) in sq(l)), None)
            if hit is None:
                warn.append(f"{iid} 보기 '{c}' 근거 줄 없음")
                exc.append(f"{c}: (해설 확인 필요)")
            else:
                exc.append(f"{c}: " + re.sub(r"^[-\s>|①②③④]*", "", hit).strip(" |"))
        q["exChoice"] = manual or exc
        if manual:
            warn[:] = [w for w in warn if not (w.startswith(iid + " 보기"))]
    elif t == "진위형":
        q["ans"] = q["ansText"] = ans
    else:
        q["ansText"] = accept[0] if accept else f"{value} {unit}"
        if accept:
            q["accept"] = accept
        if value is not None:
            q["value"], q["unit"] = value, unit
    key = sq(choices[ans]) if t == "4지선다" else sq(item) if t == "진위형" else sq((accept or [str(value)])[0])
    q["basis"] = [l for l in body if key and key in sq(l)][:2]
    if t == "진위형":
        # 해설(근거·개념 상자)을 붙인 뒤 넘어간다 — 처음 판은 이 줄 없이 넘어가 진위형에 해설이 빠졌다(2026-11-23 고침)
        q["ex"] = {"근거": basis_txt, "개념": ex0.get("개념")} if ex0.get("개념") else {"근거": basis_txt}
        out.append(q)
        continue
    if not q["basis"] and t != "계산형":
        warn.append(f"{iid} 정답 '{q['ansText']}'이 원본 개념 상자에 없음")
    q["ex"] = {"근거": basis_txt, "개념": ex0.get("개념")} if ex0.get("개념") else {"근거": basis_txt}
    # 겹침: 기존·새 문항 중 정답 글자가 같은 문항
    for o in list(OLD.values()) + NEW:
        oa = o.get("ansText", "")
        oa = re.sub(r"^[①②③④]\s*", "", oa)
        if sq(oa) and sq(oa) == sq(q["ansText"].split(" ", 1)[-1] if t == "4지선다" else q["ansText"]):
            warn.append(f"{iid} 정답이 기존 {o['id']}와 같음: {o['stem'][:50]}")
    # 겹침 2: 지문+정답 글자 2-gram 유사도
    def grams(s):
        s = sq(s)
        return {s[i:i + 2] for i in range(len(s) - 1)}
    g = grams(stem + q["ansText"])
    for o in list(OLD.values()) + NEW:
        if o["id"] == frm:
            continue
        go = grams(o["stem"] + o.get("ansText", ""))
        if g and go:
            j = len(g & go) / len(g | go)
            if j >= 0.45:
                warn.append(f"{iid} 지문 유사도 {j:.2f} 기존 {o['id']}: {o['stem'][:50]} / {o.get('ansText','')}")
    out.append(q)

(B / "draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(out)}문항 (나 {sum(q['kind']=='나' for q in out)}, 가 {sum(q['kind']=='가' for q in out)})")
for w in warn:
    print("확인:", w)

# 블라인드 지시문 (정답 없음). (나)는 원본을 함께 보여 준다.
RUB = """## 난이도 판정 기준 (쌍둥이 N번 문항만)
원본과 비교해 아래 여섯 기준마다 같음/쉬움/어려움을 적는다.
① 대상의 익숙함(묻는 대상이 얼마나 자주 다뤄지는가) ② 지문의 단서(정답 낱말이 지문에 드러나는가)
③ 오답 보기의 헷갈림 ④ 묻는 방향(정의→용어, 용어→정의, '아닌 것') ⑤ 풀이 단계(계산·단위 변환) ⑥ 알아야 할 양
"""
L = ["# 문제지 (정답 없음)", "", RUB]
for n, q in enumerate(out, 1):
    q["_n"] = n
    tag = "쌍둥이" if q["kind"] == "나" else "변형"
    L.append(f"N{n}. [{q['t']}·{tag}] {q['stem']}")
    if q.get("choices"):
        L.append("    " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
    if q["kind"] == "나":
        s = OLD[q["from"]]
        L.append(f"    (원본) {s['stem']}")
        if s.get("choices"):
            L.append("    (원본 보기) " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(s["choices"])) + f"  (원본 정답 {s['ansText']})")
    L.append("")
TASK = """`blind.md`의 문항(N1~)을 기계가공·CNC·측정·제도의 일반 지식으로 직접 풀어라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- 최종 응답은 표 하나만: | 번호 | 답 | 근거(한 줄) | 다른 답도 맞을 수 있는가 | 오류·모호함 | 난이도 ①②③④⑤⑥ |
- 모든 번호를 채운다. 4지선다는 번호와 보기, 단답·계산은 답(단위 포함).
- 정답이 둘 이상이거나 보기 중 정답이 없을 수 있으면 반드시 '다른 답' 칸에 적는다. 확신이 없으면 '확신 낮음'.
- '난이도' 칸은 쌍둥이 문항만: 원본 대비 여섯 기준을 순서대로 '같/쉬/어'로 적는다(예: 같 같 쉬 같 같 같). 변형 문항은 '-'.
"""
AG = """# 블라인드 풀이 폴더

컴퓨터응용가공산업기사(과정평가형) 새 문항을 정답 없이 풀어 보는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `blind.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
# 문제지는 --to <폴더 이름 접두어>를 줄 때만 쓴다(두 AI가 푸는 중에 덮어쓰지 않도록). 예: --to r1 → r1_gpt, r1_cursor
import os
TO = sys.argv[sys.argv.index("--to") + 1] if "--to" in sys.argv else None
for name, sub in (((f"{TO}_gpt", ".gpt-delegate"), (f"{TO}_cursor", ".cursor-delegate")) if TO else ()):
    d = B / name
    (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "blind.md").write_text("\n".join(L), encoding="utf-8")
    (d / "AGENTS.md").write_text(AG, encoding="utf-8")
    (d / sub / "task.md").write_text(TASK, encoding="utf-8")
(B / "draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
