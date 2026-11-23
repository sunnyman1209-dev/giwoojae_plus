r"""데이터 검증기 (SPEC Testing Decisions 1): python -I quiz_plus\tools\check_plus.py
빌드한 docs\data\questions.json 의 겉으로 드러나는 성질만 본다. 문제가 있으면 끝 코드 1.
"""
import glob, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.dirname(P)
sys.path.insert(0, os.path.join(H, "tools"))
from hs import parse  # noqa: E402

D = json.load(open(os.path.join(P, "docs", "data", "questions.json"), encoding="utf-8"))
QS = D["questions"]
BY = {q["id"]: q for q in QS}
errs = []
err = errs.append
norm = lambda s: re.sub(r"[\s·,.\-_'\"()\[\]]", "", re.sub(r"\([^)]*\)", "", str(s or ""))).lower()

# 1. 문항 수와 id
old = json.load(open(os.path.join(H, "quiz", "docs", "data", "questions.json"), encoding="utf-8"))["questions"]
new_src = []
for f in glob.glob(os.path.join(P, "src", "new", "*.json")):
    new_src += json.load(open(f, encoding="utf-8"))
approved = [l.strip() for l in open(os.path.join(P, "src", "approved.txt"), encoding="utf-8")] if os.path.exists(os.path.join(P, "src", "approved.txt")) else []
approved = [a for a in approved if a and not a.startswith("#")]
if len(QS) != len(old) + len(new_src) + len(approved):
    err(f"문항 수 {len(QS)} ≠ 기존 {len(old)} + 새 {len(new_src)} + 승인 {len(approved)}")
if len(BY) != len(QS):
    err("id 중복")

# 2. 꼬리표
for q in QS:
    if not (q.get("tag") or {}).get("box") or not (q.get("tag") or {}).get("item"):
        err(f"{q['id']} 꼬리표 없음")

# 3. 새 문항: 원본이 기존 문항이고 정정·확인필요가 아님, 검증 기록
excl = {l.strip() for l in open(os.path.join(H, "quiz", "tools", "exclude.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")}
fixed = set()
for f in glob.glob(os.path.join(H, "해설", "*.md")):
    items, _ = parse(f)
    part = os.path.basename(f)[:-3]
    fixed |= {f"{part}|{no}" for no, it in items.items() if it.get("정정")}
for n in new_src:
    if n["from"] not in {q["id"] for q in old}:
        err(f"{n['id']} 원본 {n['from']}이 기존 문항이 아님")
    if n["from"] in excl or n["from"] in fixed:
        err(f"{n['id']} 원본이 정정·확인필요 문항")
    v = n.get("verify") or {}
    if not v.get("blind"):
        err(f"{n['id']} 블라인드 풀이 기록 없음")
    lv = v.get("level", {})
    def lv_ok(x):
        # '같음'(1차 묶음 규칙) 또는 '차이 n'(n ≤ 2, 2026-11-23 사용자 결정: 여섯 기준 중 한두 개 차이 허용)
        return x == "같음" or (isinstance(x, str) and x.startswith("차이 ") and int(x[3:]) <= 2)
    if n.get("kind") == "나" and not (lv_ok(lv.get("gpt")) and lv_ok(lv.get("cursor"))):
        err(f"{n['id']} 쌍둥이 난이도 기준 미달")

# 4. 4지: exChoice는 정답 자리만 비어 있다
for q in QS:
    if q["t"] == "4지선다" and q.get("choices"):
        ec = q.get("exChoice") or []
        if len(ec) != len(q["choices"]) or ec[q["ans"]] is not None:
            err(f"{q['id']} exChoice 모양")
        elif q["src"] == "old" and sum(x is None for x in ec) != 1:
            err(f"{q['id']} 오답 이유 빠짐")

# 5. 주관식 대상 지문
for q in QS:
    if q.get("open") and re.search(r"옳|틀린|아닌|않|없는|것은", q["stem"]):
        err(f"{q['id']} 주관식 대상인데 보기를 봐야 하는 지문")

# 6. CBT 후보가 시험 한 번을 채울 만큼 있다(꼬리표가 다른 문항 기준)
need = {"진위형": 2, "연결형": 3, "4지선다": 25, "단답형": 8, "계산형": 2}
for t, n in need.items():
    tags = {norm(q["tag"]["box"]) + "|" + norm(q["tag"]["item"]) for q in QS if q.get("cbt") and q["t"] == t}
    if len(tags) < n:
        err(f"CBT {t} 후보 부족 {len(tags)} < {n}")
n_new = sum(1 for q in QS if q.get("cbt") and q["src"] == "new")
if n_new < 20:
    print(f"알림: CBT용 새 문항 {n_new}개라 시험지의 새 문항이 20개보다 적다(SPEC 7-1 규칙대로 기존 문항으로 채움)")
if any(q.get("cbt") and q["t"] == "서술형" for q in QS):
    err("서술형이 CBT 대상")

print(f"문항 {len(QS)} (새 {sum(q['src'] == 'new' for q in QS)}), 계산 숫자 바꾸기 {sum('calc' in q for q in QS)}, 주관식 대상 {sum('open' in q for q in QS)}, CBT 후보 {sum(bool(q.get('cbt')) for q in QS)}")
print("\n".join(errs) if errs else "검증 통과")
sys.exit(1 if errs else 0)
