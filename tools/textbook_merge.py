"""교재 예상문제 중복 판정(Claude·Cursor·GPT)을 합쳐 보고서를 만든다."""
import json, re
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "work" / "교재대조"
items = json.loads((D / "items.json").read_text(encoding="utf-8"))
def load(p):
    r = {}
    if not p.exists(): return r
    for ln in p.read_text(encoding="utf-8").splitlines():
        p = [x.strip(" `*-") for x in re.split(r"\s+\|\s+", ln.strip())]
        if len(p) >= 2 and re.fullmatch(r"T\d{1,2}-\d{1,2}", p[0]):
            v = p[1].replace(" ", "")
            v = "개념같음" if "개념" in v else "같음" if v.startswith("같음") else "판정불가" if "불가" in v else "다름"
            r[p[0]] = (v, p[2] if len(p) > 2 else "-")
    return r
J = {"Claude": load(D / "claude.txt"), "Cursor": load(ROOT / ".cursor-delegate" / "result.md"), "GPT": load(ROOT / ".gpt-delegate" / "result.md")}
for k, v in J.items(): print(k, len(v), Counter(x[0] for x in v.values()))
res = {"제외": [], "넣기": [], "그림·판정불가": [], "갈림": []}
rows = []
for it in items:
    vs = {k: J[k].get(it["id"], ("없음", "")) for k in J}
    ov = sum(v[0] in ("같음", "개념같음") for v in vs.values())
    na = sum(v[0] == "판정불가" for v in vs.values())
    df = sum(v[0] == "다름" for v in vs.values())
    if ov >= 2: cat = "제외"
    elif na >= 2 or (it["fig"] and na >= 1): cat = "그림·판정불가"
    elif df >= 2: cat = "넣기"
    else: cat = "갈림"
    res[cat].append(it["id"])
    rows.append((it, vs, cat))
print({k: len(v) for k, v in res.items()})
L = ["# 2027 교재 예상문제와 문제은행 중복 판정 (2026-11-24)", "",
     "- 대상: 교재 예상문제 1~10회차 400문항, 문제은행 998문항",
     "- 판정: Claude, Cursor(auto), GPT가 각각 '같음 / 개념같음 / 다름 / 판정불가'로 판정",
     "- 합치기: 두 곳 이상이 같음·개념같음이면 제외, 두 곳 이상이 판정불가면 그림·판정불가, 두 곳 이상이 다름이면 넣기, 나머지는 갈림", "",
     "| 구분 | 문항 수 |", "|---|---|"] + [f"| {k} | {len(v)} |" for k, v in res.items()] + [""]
for cat in res:
    L += [f"## {cat} ({len(res[cat])})", "", "| 문항 | 지문 | Claude | Cursor | GPT |", "|---|---|---|---|---|"]
    for it, vs, c in rows:
        if c != cat: continue
        t = re.sub(r"\s+", " ", it["text"])[:70].replace("|", "/")
        L.append(f"| {it['id']} | {t} | " + " | ".join(f"{v[0]} {v[1] if v[1] not in ('-', '') else ''}".strip().replace("|", "¦") for v in vs.values()) + " |")
    L.append("")
(D / "중복판정.md").write_text("\n".join(L), encoding="utf-8")
(D / "merged.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
