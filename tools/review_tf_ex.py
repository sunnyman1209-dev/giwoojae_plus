"""다른 방향 진위형 문항의 문장·정답·해설을 두 AI 검토용으로 묶는다. → work\\tf_review\\gpt, cursor"""
import json
import re
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
D = json.loads((Q / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))
D = D["questions"] if isinstance(D, dict) else D
T = [q for q in D if q["t"] == "진위형" and re.search(r"t\d$", q["id"])]
L = ["# 진위형 정답·해설 검토용", ""]
for n, q in enumerate(T, 1):
    L += [f"## T{n}", f"문장: {q['stem']}", f"정답: {q['ans']}", f"해설: {q['ex']['근거']}", ""]
TASK = f"""`review.md`의 T1~T{len(T)}마다 진위 문장의 정답(O/X)과 해설이 맞는지 기계가공·CNC·측정·제도의 일반 지식으로 검토하라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- 찾을 것: (1) 정답이 틀렸거나 판정이 갈릴 수 있는 문장 (2) 해설이 문장과 맞지 않거나 사실과 다른 곳 (3) 해설에 남은 어색한 문장, 원래 4지 문항을 가리키는 말(보기·문항·정답 번호 등)
- 최종 응답은 문제가 있는 문항만 표 하나로: | 번호 | 심각도(높음/중간/낮음) | 문제 | 고칠 문장 제안 |
- 제어기마다 다를 수 있다는 정도의 지적은 '낮음'. 문제가 없는 문항은 적지 않는다. 전부 문제없으면 '문제 없음'.
"""
AG = """# 해설 검토 폴더

컴퓨터응용가공산업기사 진위형 문항의 정답과 해설을 검토하는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `review.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
for name, sub in (("gpt", ".gpt-delegate"), ("cursor", ".cursor-delegate")):
    d = Q / "work" / "tf_review" / name
    (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "review.md").write_text("\n".join(L), encoding="utf-8")
    (d / "AGENTS.md").write_text(AG, encoding="utf-8")
    (d / sub / "task.md").write_text(TASK, encoding="utf-8")
(Q / "work" / "tf_review" / "order.json").write_text(json.dumps([q["id"] for q in T]), encoding="utf-8")
print(len(T))
