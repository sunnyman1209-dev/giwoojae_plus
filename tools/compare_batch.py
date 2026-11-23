"""묶음 블라인드 결과 비교. 사용: compare_batch.py <묶음> <폴더(blind.md 있는 곳)> [<폴더2> ...]
blind.md의 N번 지문으로 draft.json 문항을 찾아 정답·난이도(차이 기준 수)를 본다. 여러 폴더면 문항별로 모아 보여 준다."""
import json
import re
import sys
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
B = Q / "work" / sys.argv[1]
DR = {q["stem"].split("\n")[0]: q for q in json.loads((B / "draft.json").read_text(encoding="utf-8"))}
C = "①②③④"


def norm(s):
    return re.sub(r"[\s`*()（）\[\]'\".]", "", s).lower()


res = {}
for folder in sys.argv[2:]:
    d = Q / "work" / sys.argv[1] / folder if not Path(folder).is_absolute() else Path(folder)
    nmap = {}
    for line in (d / "blind.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"N(\d+)\. \[[^\]]+\] (.*)", line)
        if m:
            nmap[m.group(1)] = DR.get(m.group(2))
    rf = next(d.glob(".*-delegate/result.md"))
    who = "GPT" if "gpt" in rf.parent.name else "Cursor"
    for line in rf.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*N(\d+)\s*\|(.*)", line)
        if not m:
            continue
        q = nmap.get(m.group(1))
        if q is None:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        a = cells[0]
        t = q["t"]
        if t == "4지선다":
            ok = a.startswith(C[q["ans"]]) or a.startswith(str(q["ans"] + 1))
        elif t == "진위형":
            aa = norm(a).upper().replace("참", "O").replace("거짓", "X")
            ok = aa.startswith(q["ans"])
        elif t == "계산형":
            num = re.search(r"-?[\d.]+", a.replace(",", ""))
            ok = bool(num) and abs(float(num.group()) - q["value"]) <= abs(q["value"]) * 0.01 + 1e-9
        else:
            ok = any(norm(x) and norm(x) in norm(a) for x in q.get("accept", []))
        lvl = cells[4] if len(cells) > 4 else ""
        diff = len(re.findall(r"[쉬어]", lvl)) if q["kind"] == "나" else 0
        dirn = "쉬" * lvl.count("쉬") + "어" * lvl.count("어")
        note = " / ".join(c for c in cells[2:4] if c and c not in ("-", "—", "없음", "아니요", "아니오", "아니요."))
        res.setdefault(q["id"], {"q": q})[who] = (ok, a, diff, dirn, note)

passed, held = [], []
for iid, r in res.items():
    q = r["q"]
    row = [iid, q["kind"]]
    good = True
    for who in ("GPT", "Cursor"):
        if who not in r:
            row.append(f"{who}:없음")
            good = False
            continue
        ok, a, diff, dirn, note = r[who]
        row.append(f"{who}:{'O' if ok else 'X('+a[:20]+')'} 차이{diff}{dirn}" + (f" [{note[:90]}]" if note else ""))
        if not ok or (q["kind"] == "나" and diff > 2):
            good = False
    (passed if good else held).append(row)
summary = {iid: {w: list(r[w]) for w in ("GPT", "Cursor") if w in r} for iid, r in res.items()}
(B / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"통과 {len(passed)} / 보류 {len(held)}")
for r in held:
    print("보류", " | ".join(r))
for r in passed:
    print("통과", " | ".join(r))
