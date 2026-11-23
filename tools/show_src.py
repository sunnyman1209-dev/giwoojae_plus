"""새 문항 원본 후보를 간추려 보여 준다.
사용: show_src.py <파트> [유형] [시작] [개수]
제외: exclude.txt, 그림 문항, 이미 원본으로 쓴 문항(src\\new\\*.json의 from, 1123 시험 80문항)."""
import json
import sys
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
Z = Q.parent / "quiz"
D = json.loads((Z / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]
exc = {l.strip() for l in (Z / "tools" / "exclude.txt").read_text(encoding="utf-8").splitlines()
       if l.strip() and not l.startswith("#")}
used = set()
for f in (Q / "src" / "new").glob("*.json"):
    used |= {x["from"] for x in json.loads(f.read_text(encoding="utf-8"))}
E = json.loads((Z / "work" / "variant" / "exam_1123.json").read_text(encoding="utf-8"))
for k in E:
    used |= {x["src"] for x in E[k]}

part = sys.argv[1]
typ = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
cnt = int(sys.argv[4]) if len(sys.argv) > 4 else 15
C = "①②③④"
L = [q for q in D if q["p"] == part and q["id"] not in exc and q["id"] not in used and not q.get("fig")
     and (typ is None or q["t"] == typ)]
print(f"후보 {len(L)}개")
for q in L[start:start + cnt]:
    ex = q.get("ex", {})
    print(f"\n[{q['id']}] {q['t']} | {q['stem']}")
    if q.get("choices"):
        print("  보기:", " / ".join(f"{C[i]}{c}" for i, c in enumerate(q["choices"])), "| 정답", q["ansText"])
    elif q.get("left"):
        print("  ", q["left"], q["right"], "| 정답", q.get("ansText"))
    else:
        print("  정답:", q.get("ansText"))
    if ex.get("개념"):
        print("  개념:", ex["개념"]["title"], "|", " ".join(ex["개념"]["body"])[:400])
    for o in ex.get("오답", [])[:3]:
        print("  오답:", o[:120])
