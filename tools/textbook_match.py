"""2027 교재 예상문제(1~10회차)를 문항으로 뽑고, 문제은행 전체에서 비슷한 후보 3개씩 붙여 대조 파일을 만든다."""
import json, re, sys
from pathlib import Path
import pymupdf
H = Path.home()
PDF = H / "Documents" / "카카오톡 받은 파일" / "2027 컴퓨터응용가공산업기사 교재.pdf"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "work" / "교재대조"
QS = json.loads((ROOT / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]
doc = pymupdf.open(PDF)
lines = []
for i in range(24, len(doc)):
    for ln in doc[i].get_text().splitlines():
        lines.append((i + 1, ln))
items, cur, rnd, sec = [], None, 0, ""
for pg, ln in lines:
    s = ln.strip()
    m = re.match(r"^(\d{1,2})회차", s)
    if m:
        rnd = int(m.group(1)); continue
    if s.startswith("▶"):
        sec = re.sub(r"\s*\(.*", "", s[1:]); continue
    if re.fullmatch(r"\d{1,3}", s) or s.startswith("< 외부평가"):
        continue
    m = re.match(r"^(\d{1,2})\s*[.,]\s*(.*)", s)
    if m and rnd and (cur is None or int(m.group(1)) == cur["n"] + 1 or int(m.group(1)) == 1):
        cur = {"id": f"T{rnd}-{int(m.group(1))}", "r": rnd, "n": int(m.group(1)), "sec": sec, "pdf": pg, "text": m.group(2)}
        items.append(cur); continue
    if cur is not None:
        cur["text"] += "\n" + s
def sq(s): return re.sub(r"[^가-힣A-Za-z0-9]", "", str(s))
def bg(s): s = sq(s); return {s[i:i + 2] for i in range(len(s) - 1)}
def full(q): return " ".join(map(str, [q.get("stem", ""), q.get("ansText", "")] + (q.get("choices") or []) + (q.get("left") or []) + (q.get("right") or [])))
qb = [bg(full(q)) for q in QS]
L = []
for it in items:
    it["text"] = re.sub(r"[ \t]+", " ", it["text"]).strip()
    it["fig"] = bool(re.search(r"그림|사진|다음 측정기의 명칭|눈금을 읽", it["text"]))
    b = bg(it["text"])
    sc = sorted(((len(b & o) / max(1, min(len(b), len(o))), k) for k, o in enumerate(qb)), reverse=True)[:3]
    it["cand"] = [(round(s, 2), QS[k]["id"]) for s, k in sc]
    L.append(f"## {it['id']} ({it['sec']}{', 그림' if it['fig'] else ''})\n{it['text'][:500]}\n")
    for s, k in sc:
        q = QS[k]
        L.append(f"- 후보 {q['id']} [{s:.2f}] {full(q)[:260]}")
    L.append("")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "대조자료.md").write_text("\n".join(L), encoding="utf-8")
from collections import Counter
print(len(items), Counter(i["r"] for i in items), "그림", sum(i["fig"] for i in items))
