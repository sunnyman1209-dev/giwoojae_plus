"""1차 묶음 보류 35문항(쌍둥이)을 여섯 기준으로 다시 판정받는 지시문. 정답을 함께 보여 준다(정답은 이미 두 AI가 맞힘).
사용: rejudge_1123.py  → work\\1123\\rejudge_gpt, rejudge_cursor"""
import json
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
Z = Q.parent / "quiz"
if not Z.is_dir():  # 작업틀(worktree)에서 돌릴 때: 원래 저장소 옆의 quiz 폴더를 쓴다
    import subprocess
    _c = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=Q, capture_output=True, text=True).stdout.strip()
    Z = Path(_c).parent.parent / "quiz"
OLD = {q["id"]: q for q in json.loads((Z / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]}
H = json.loads((Q / "work" / "1123" / "보류.json").read_text(encoding="utf-8"))
C, K = "①②③④", "㉠㉡㉢㉣"


def show(q, tag):
    L = [f"    ({tag}) [{q['t']}] {q['stem']}"]
    if q.get("choices"):
        L.append(f"    ({tag} 보기) " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
    if q.get("left"):
        L.append(f"    ({tag} 왼쪽) " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["left"])))
        L.append(f"    ({tag} 오른쪽) " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(q["right"])))
    L.append(f"    ({tag} 정답) {q.get('ansText')}")
    return L


L = ["# 난이도 비교 (원본 대비 쌍둥이 문항)", "",
     "아래 여섯 기준마다 원본 대비 같음/쉬움/어려움을 판정한다.",
     "① 대상의 익숙함(묻는 대상이 얼마나 자주 다뤄지는가) ② 지문의 단서(정답 낱말이 지문에 드러나는가)",
     "③ 오답 보기의 헷갈림 ④ 묻는 방향(정의→용어, 용어→정의, '아닌 것') ⑤ 풀이 단계(계산·단위 변환) ⑥ 알아야 할 양", ""]
for n, q in enumerate(H, 1):
    L.append(f"R{n}.")
    L += show(q, "새 문항")
    L += show(OLD[q["from"]], "원본")
    L.append("")
TASK = """`compare.md`의 R1~R35마다 새 문항을 원본과 비교해 여섯 기준의 난이도를 판정하라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- 최종 응답은 표 하나만: | 번호 | 난이도 ①②③④⑤⑥ | 차이 나는 기준과 이유(한 줄) |
- 난이도 칸은 순서대로 '같/쉬/어'로 적는다(예: 같 같 쉬 같 같 같). 35행을 모두 채운다.
"""
AG = """# 난이도 비교 폴더

컴퓨터응용가공산업기사 문항의 난이도를 원본과 비교하는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `compare.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
for name, sub in (("rejudge_gpt", ".gpt-delegate"), ("rejudge_cursor", ".cursor-delegate")):
    d = Q / "work" / "1123" / name
    (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "compare.md").write_text("\n".join(L), encoding="utf-8")
    (d / "AGENTS.md").write_text(AG, encoding="utf-8")
    (d / sub / "task.md").write_text(TASK, encoding="utf-8")
(Q / "work" / "1123" / "rejudge_order.json").write_text(json.dumps([q["id"] for q in H]), encoding="utf-8")
print(len(H))
