"""아직 정답으로 묻지 않은 개념 상자 표 줄을 상자별로 보여 준다(원본 후보 id 포함).
사용: untested_boxes.py [시작] [개수]"""
import json
import re
import sys
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
Z = Q.parent / "quiz"
if not Z.is_dir():  # 작업틀(worktree)에서 돌릴 때: 원래 저장소 옆의 quiz 폴더를 쓴다
    import subprocess
    _c = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=Q, capture_output=True, text=True).stdout.strip()
    Z = Path(_c).parent.parent / "quiz"
D = json.loads((Z / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]
exc = {l.strip() for l in (Z / "tools" / "exclude.txt").read_text(encoding="utf-8").splitlines()
       if l.strip() and not l.startswith("#")}
NEW = []
for f in (Q / "src" / "new").glob("*.json"):
    NEW += json.loads(f.read_text(encoding="utf-8"))
for f in (Q / "work").glob("*/items_*.py"):
    NEW += [{"ansText": m} for m in re.findall(r'"item"|, "([^"]+)",\n', "")]  # 자리만


def sq(s):
    return re.sub(r"[\s·()\[\]./,-]", "", str(s)).lower()


answers = set()
for q in D + NEW:
    answers.add(sq(re.sub(r"^[①②③④]\s*", "", q.get("ansText", "") or "")))
    for x in q.get("accept") or []:
        answers.add(sq(x))
# 이번 작업에서 이미 만든 문항의 item도 물은 것으로 본다
for f in (Q / "work").glob("*/items_*.py"):
    for m in re.finditer(r'None, "([^"]+)",\n', f.read_text(encoding="utf-8")):
        answers.add(sq(m.group(1)))

seen = {}
for q in D:
    b = (q.get("ex") or {}).get("개념")
    if not b or q["id"] in exc or q.get("fig"):
        continue
    key = b["title"]
    if key in seen:
        seen[key]["src"].append(q["id"])
        continue
    rows = []
    for line in b["body"]:
        if line.startswith("|") and not set(line) <= set("|-: "):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0] and not any(sq(p) and sq(p) in answers for p in re.split(r"[/,]", cells[0])):
                rows.append(line)
    seen[key] = {"src": [q["id"]], "rows": rows[1:] if rows else []}

L = [(k, v) for k, v in seen.items() if len(v["rows"]) >= 1]
a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
print(f"안 물은 줄이 있는 상자 {len(L)}개, 줄 합계 {sum(len(v['rows']) for _, v in L)}")
for k, v in L[a:a + n]:
    print(f"\n## {k}  (원본 후보 {', '.join(v['src'][:4])})")
    for r in v["rows"]:
        print("  ", r[:160])
