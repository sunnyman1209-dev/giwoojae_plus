r"""데이터 검증기 (SPEC Testing Decisions 1): python -I quiz_plus\tools\check_plus.py
빌드한 docs\data\questions.json 의 겉으로 드러나는 성질만 본다. 문제가 있으면 끝 코드 1.
"""
import glob, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.dirname(P)
if not os.path.isdir(os.path.join(H, "quiz")):  # 작업틀(worktree)에서 돌릴 때: 원래 저장소 옆의 quiz 폴더를 쓴다
    import subprocess
    _c = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=P, capture_output=True, text=True).stdout.strip()
    H = os.path.dirname(os.path.dirname(_c))
sys.path.insert(0, os.path.join(H, "tools"))
from hs import parse  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plus_rules as R  # noqa: E402
import test_check_rules  # noqa: E402

D = json.load(open(os.path.join(P, "docs", "data", "questions.json"), encoding="utf-8"))
QS = D["questions"]
BY = {q["id"]: q for q in QS}
errs = []
err = errs.append
for f in test_check_rules.run():  # 규칙 자체의 시험이 먼저 통과해야 아래 결과를 믿는다
    err("규칙 시험 실패: " + f)
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
    if R.is_textbook(n):  # 교재·실전모의 문항은 원본이 기존 문항이 아니다. 블라인드 풀이 기록만 본다.
        if not (n.get("verify") or {}).get("blind"):
            err(f"{n['id']} 블라인드 풀이 기록 없음")
        continue
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

# 4-1. 모든 문항에 해설 근거가 있다(2026-11-23: 새 진위형 253문항에 해설이 빠졌던 일을 막기 위함)
for q in QS:
    if not ((q.get("ex") or {}).get("근거") or "").strip():
        err(f"{q['id']} 해설 근거 없음")

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

# 7. 2차 명세(SPEC_1124) 규칙
#  - 교재·실전모의 문항: 정답, 근거, 단답형 인정 답안
#  - 화면 글의 출처 노출: 새 문항은 실패, 기존 590문항(해설집 원본)은 경고(06에서 덮어쓰기로 고침)
#  - 해설의 원본 지칭: 경고. --notes <경로>를 주면 경고 목록을 md로 남긴다.
for q in QS:
    for e in R.textbook_errors(q):
        err(f"{q['id']} 교재 문항 {e}")
leak_warn, ref_warn = [], []
for q in QS:
    lk = R.leaks(q)
    if lk:
        msg = ", ".join(sorted({f"{f}:'{m}'" for f, m in lk}))
        if q["src"] == "old":
            leak_warn.append((q["id"], msg))
        else:
            err(f"{q['id']} 화면 글에 출처 노출 {msg}")
    rf = R.refs(q)
    if rf:
        ref_warn.append((q["id"], ", ".join(sorted(set(rf)))))
print(f"경고: 해설 원본 지칭 {len(ref_warn)}문항, 기존 문항 출처 노출 {len(leak_warn)}문항")
if "--notes" in sys.argv:
    out = sys.argv[sys.argv.index("--notes") + 1]
    L = ["# 01 데이터 검사 경고 목록", "", f"- 만든 도구: tools/check_plus.py --notes (문항 {len(QS)})",
         "- 고치는 일은 06(기존 590)·07(쌍둥이)·08(새 문항)에서 한다. 경고는 검사 실패가 아니다.", "",
         f"## 해설 원본 지칭 ({len(ref_warn)}문항)", "", "찾는 말: '문제', '문항', '보기 ○', '○번'", "",
         "| id | 찾은 말 |", "|---|---|"]
    cell = lambda i: i.replace("|", r"\|")  # id의 세로선이 표를 깨지 않게
    L += [f"| {cell(i)} | {m} |" for i, m in ref_warn]
    L += ["", f"## 기존 문항 화면 글의 출처 노출 ({len(leak_warn)}문항)", "",
          "새 문항이면 실패, 기존 590문항은 해설집 원본 글이라 경고로만 둔다.", "", "| id | 필드:찾은 말 |", "|---|---|"]
    L += [f"| {cell(i)} | {m} |" for i, m in leak_warn]
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"경고 목록 저장: {out}")

print(f"문항 {len(QS)} (새 {sum(q['src'] == 'new' for q in QS)}), 계산 숫자 바꾸기 {sum('calc' in q for q in QS)}, 주관식 대상 {sum('open' in q for q in QS)}, CBT 후보 {sum(bool(q.get('cbt')) for q in QS)}")
print("\n".join(errs) if errs else "검증 통과")
sys.exit(1 if errs else 0)
