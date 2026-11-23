"""해설집 개념 상자 표의 항목(첫 칸) 중 문제은행에서 아직 정답으로 묻지 않은 것을 센다."""
import json
import re
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
Z = Q.parent / "quiz"
D = json.loads((Z / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]
NEW = []
for f in (Q / "src" / "new").glob("*.json"):
    NEW += json.loads(f.read_text(encoding="utf-8"))


def sq(s):
    return re.sub(r"[\s·()\[\]./,-]", "", str(s)).lower()


answers = set()
for q in D + NEW:
    a = re.sub(r"^[①②③④]\s*", "", q.get("ansText", "") or "")
    answers.add(sq(a))
    for x in q.get("accept") or []:
        answers.add(sq(x))

boxes = {}
for q in D:
    b = (q.get("ex") or {}).get("개념")
    if not b:
        continue
    for line in b["body"]:
        if line.startswith("|") and not set(line) <= set("|-: "):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and not cells[0].startswith("-"):
                boxes.setdefault(b["title"], set()).add(cells[0])

terms = {(t, x) for t, xs in boxes.items() for x in xs}
heads = {"코드", "구분", "방식", "종류", "측정기", "확장자", "스위치", "기능", "명령", "단계", "좌표", "장비", "재료", "기호"}
terms = {(t, x) for t, x in terms if x not in heads and len(x) <= 30}
tested = {(t, x) for t, x in terms if any(sq(p) in answers for p in re.split(r"[/,]", x))}
untested = sorted(terms - tested)
uniq = {sq(x) for _, x in untested}
print(f"개념 상자 {len(boxes)}개, 표 항목 {len(terms)}개, 이미 정답으로 물은 항목 {len(tested)}개, 아직 안 물은 항목 {len(untested)}개(서로 다른 용어 {len(uniq)}개)")
for t, x in untested[:60]:
    print(f"  {t} | {x}")
