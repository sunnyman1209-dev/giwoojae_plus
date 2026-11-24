"""다른 방향 문항(진위형) 만들기: 기존 4지(정의→용어) 문항을 '…것은 ○○이다.' 진위 문장으로.
O/X를 번갈아 만들고, X는 원본 오답 보기(해설 '오답' 줄에 설명이 있는 것)로 바꾼다.
사용: gen_tf.py <묶음> <최대 개수>  → work\\<묶음>\\items_tf.py"""
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
used = set()
for f in (Q / "src" / "new").glob("*.json"):
    used |= {x["id"] for x in json.loads(f.read_text(encoding="utf-8"))}
for f in (Q / "work").glob("*/items_*.py"):
    if f.parent.name == sys.argv[1]:
        continue  # 지금 만드는 묶음 자신은 빼고, 다른 묶음에서 이미 만든 id만 건너뛴다
    used |= set(re.findall(r"""\(["']([^"']+t\d)["']""", f.read_text(encoding="utf-8")))
BAD = re.compile(r"아닌|옳지|틀린|옳은|모두|관계\s*없|다른 것|맞는|적합하지|않은|않는|없는|못한|잘못|해당하지|[①-⑥]|<보기>|그림|다음|\(\s*\)|\(\s{2,}|빈칸")
NUM = re.compile(r"^[\d.\s/~×xX±°%-]+[a-zA-Z/²³μ]*$")


def sq(s):
    return re.sub(r"[\s·()\[\]./,-]", "", str(s)).lower()


T1 = {}
for f in (Q / "src" / "new").glob("*.json"):
    for x in json.loads(f.read_text(encoding="utf-8")):
        if x["id"].endswith("t1") and x["t"] == "진위형":
            T1[x["id"]] = x["ans"]
MODE = sys.argv[3] if len(sys.argv) > 3 else "t1"   # t1: 처음 만들기, flip: t1과 진위를 반대로(t2), short: 단답형 원본
seen, out = set(), []
if MODE == "short":
    for q in D:
        if q["t"] != "단답형" or q["id"] in exc or q.get("fig") or "\n" in q["stem"]:
            continue
        st = q["stem"].strip()
        ans = (q.get("accept") or [q.get("ansText", "")])[0]
        if not st.endswith("?") or BAD.search(st) or not re.search(r"(은|는)\s*\?$", st) or not ans or NUM.match(ans) or len(ans) > 22:
            continue
        key = (sq(st), sq(ans))
        if key in seen or f"{q['id']}t1" in used:
            continue
        seen.add(key)
        base = re.sub(r"[①-④]\s*", "", (q.get("ex") or {}).get("근거", "")).strip()
        out.append((f"{q['id']}t1", q["id"], "가", "진위형", f"{st.rstrip(' ?')} {ans}이다.", None, "O", None, None, None,
                    q.get("ansText") or ans, f"옳다. {base}" if base else f"옳다. 설명에 해당하는 것은 {ans}이다."))
        if len(out) >= int(sys.argv[2]):
            break
    D = []
for q in D:
    if q["t"] != "4지선다" or q["id"] in exc or q.get("fig") or "\n" in q["stem"]:
        continue
    st = q["stem"].strip()
    if not st.endswith("?") or BAD.search(st) or not re.search(r"(은|는)\s*\?$", st):
        continue
    ans = q["choices"][q["ans"]]
    if NUM.match(ans) or len(ans) > 22:
        continue
    ex = q.get("ex") or {}
    wrong = []
    for line in ex.get("오답") or []:
        m = re.match(r"^\s*([①-④])\s*([^:：]+)[:：]\s*(.+)$", line)
        if m:
            term = m.group(2).strip()
            if term in q["choices"] and not NUM.match(term) and len(term) <= 22:
                wrong.append((term, m.group(3).strip()))
    key = (sq(st), sq(ans))
    if key in seen:
        continue
    seen.add(key)
    n = len(seen) - 1   # 짝수 O, 홀수 X
    want_o = (n % 2 == 0 or not wrong)
    if MODE == "flip":
        if f"{q['id']}t1" not in T1:
            continue
        want_o = T1[f"{q['id']}t1"] == "X"   # t1과 반대
        if not want_o and not wrong:
            continue
    iid = f"{q['id']}{'t2' if MODE == 'flip' else 't1'}"
    if iid in used:
        continue
    body = st.rstrip(" ?")
    base = re.sub(r"[①-④]\s*", "", ex.get("근거", "")).strip()
    if want_o:
        stmt = f"{body} {ans}이다."
        why = f"옳다. {base}" if base else f"옳다. 설명에 해당하는 것은 {ans}이다."
        a = "O"
    else:
        term, desc = wrong[0]
        stmt = f"{body} {term}이다."
        why = f"틀리다. {term}은(는) {desc} 문장의 설명에 해당하는 것은 {ans}이다."
        a = "X"
    out.append((iid, q["id"], "가", "진위형", stmt, None, a, None, None, None, ans, why))
    if len(out) >= int(sys.argv[2]):
        break

B = Q / "work" / sys.argv[1]
B.mkdir(parents=True, exist_ok=True)
txt = '"""다른 방향 문항(진위형) — gen_tf.py가 기존 4지 문항에서 자동으로 만든 것. item은 원본 정답 보기 글자(꼬리표를 원본과 같게)."""\n\nITEMS = [\n'
txt += "".join("    " + repr(x) + ",\n" for x in out) + "]\n"
(B / "items_tf.py").write_text(txt, encoding="utf-8")
print(f"{len(out)}문항 (O {sum(x[6]=='O' for x in out)}, X {sum(x[6]=='X' for x in out)})")
