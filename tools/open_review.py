"""주관식 모드 대상(open) 문항을 두 AI가 판정하도록 묶는다 → work\\open_review\\gpt, cursor
읽기: open_review.py read → 두 AI 모두 '적합'이 아닌 id를 src\\open_block.txt에 쓴다."""
import json
import re
import sys
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
W = Q / "work" / "open_review"
D = json.loads((Q / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))
D = D["questions"] if isinstance(D, dict) else D

if len(sys.argv) > 1 and sys.argv[1] == "read":
    order = json.loads((W / "order.json").read_text(encoding="utf-8"))
    res = {}
    for who, d in (("GPT", "gpt/.gpt-delegate"), ("Cursor", "cursor/.cursor-delegate")):
        for line in (W / d / "result.md").read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*S(\d+)\s*\|\s*([^|]+)\|(.*)", line)
            if m:
                res.setdefault(order[int(m.group(1)) - 1], {})[who] = (m.group(2).strip(), m.group(3).strip(" |")[:90])
    keep = [i for i in order if all(res.get(i, {}).get(w, ("",))[0].startswith("적합") for w in ("GPT", "Cursor"))]
    block = [i for i in order if i not in keep]
    (Q / "src" / "open_block.txt").write_text(
        "# 주관식 모드에서 뺄 문항(두 AI 판정: 보기 없이는 답을 떠올리기 어렵거나 답이 하나로 정해지지 않음, 2026-11-23)\n"
        + "\n".join(block) + "\n", encoding="utf-8")
    print(f"판정 GPT {sum('GPT' in v for v in res.values())}, Cursor {sum('Cursor' in v for v in res.values())} / {len(order)}")
    print(f"주관식 유지 {len(keep)}, 제외 {len(block)}")
    for i in block[:200]:
        r = res.get(i, {})
        print("제외", i, " | ".join(f"{w}:{r[w][0]} {r[w][1]}" for w in ("GPT", "Cursor") if w in r)[:230])
    sys.exit()

T = [q for q in D if q.get("open")]
L = ["# 주관식 전환 판정", "",
     "각 문항은 원래 4지선다인데, 학습 앱의 주관식 모드에서는 보기를 감추고 지문만 보여 준 뒤 답을 직접 쓰게 한다.", ""]
for n, q in enumerate(T, 1):
    L += [f"## S{n}", f"지문: {q['stem']}", f"주관식 정답(인정 답안): {', '.join(q['open'])}", ""]
TASK = f"""`review.md`의 S1~S{len(T)}마다, 보기 없이 지문만 주고 답을 쓰게 하는 주관식으로 바꿔도 되는지 판정하라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- '적합'의 조건(모두 만족):
  1. 보기 없이 지문만 읽고도 공부한 학생이 이 답을 떠올릴 수 있다(보기를 봐야 고를 수 있는 문항이 아니다).
  2. 지문에 맞는 답이 사실상 하나다(다른 말로도 정답이 되거나, 여러 답이 가능하지 않다).
  3. 지문과 답이 자연스럽게 이어진다(지문이 묻는 것과 답의 종류가 맞는다).
- 하나라도 어긋나면 '부적합'.
- 최종 응답은 표 하나만: | 번호 | 판정(적합/부적합) | 이유(부적합일 때 한 줄) |. S1~S{len(T)} 모든 행을 채운다.
"""
AG = """# 주관식 전환 판정 폴더

컴퓨터응용가공산업기사 문항을 주관식으로 바꿔도 되는지 판정하는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `review.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
for name, sub in (("gpt", ".gpt-delegate"), ("cursor", ".cursor-delegate")):
    d = W / name
    (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "review.md").write_text("\n".join(L), encoding="utf-8")
    (d / "AGENTS.md").write_text(AG, encoding="utf-8")
    (d / sub / "task.md").write_text(TASK, encoding="utf-8")
(W / "order.json").write_text(json.dumps([q["id"] for q in T]), encoding="utf-8")
print(len(T))
for q in T[:8]:
    print(q["id"], "|", q["stem"][:60], "→", q["open"])
