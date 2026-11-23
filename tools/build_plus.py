r"""기우제반 플러스 데이터 만들기 (SPEC 4절)

python -I quiz_plus\tools\build_plus.py

입력
- 기존 590문항: quiz\docs\data\questions.json (해설을 고쳤으면 quiz\tools\build_data.py 를 먼저 돌린다)
- 새 문항: src\new\*.json (검증 통과분), src\approved.txt 에 적은 id는 work\*\보류.json 에서 가져온다
- 계산형 숫자 바꾸기: src\calc.json
- 보기 섞지 않을 문항: src\noshuffle.txt (자동 판정에 더함)
출력: docs\data\questions.json
"""
import glob, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.dirname(P)
CIRC = "①②③④⑤⑥"


def norm(s):
    s = re.sub(r"\([^)]*\)", "", str(s or "")).lower()
    return re.sub(r"[\s·,.\-_'\"“”‘’()（）\[\]]", "", s)


def lines(path):
    if not os.path.exists(path):
        return []
    return [l.split("#")[0].strip() for l in open(path, encoding="utf-8") if l.split("#")[0].strip()]


# 보기를 봐야만 풀 수 있는 지문 → 주관식 모드 대상이 아니다
# '~것은?'은 여러 답이 될 수 있는 경우가 많아(예: 안지름 측정에 쓰이는 것) 뺀다. 답이 하나로 정해지는 '~은?/~는?' 꼴만 남긴다.
NOT_OPEN = re.compile(r"옳|틀린|틀리|아닌|않|없는|없다|부적|불필요|못하|먼 것|관계|다른 것|그림|보기|순서|나열|짝지|모두|묶|해당|적합|잘못|바르|적절|맞게|알맞|가장|아래|다음|것은|것을|것이|것으로|어느|역할|장점|단점|특징|무엇으로")
# 보기끼리 서로 가리키는 보기 → 섞지 않는다
CROSS = re.compile(r"[①-⑥]|모두|없다|없음|해당 없|이상 모두|ㄱ|ㄴ|ㄷ|ㄹ|가\s*,\s*나")
NUM = re.compile(r"^\s*[-+]?\d+(?:\.\d+)?\s*[A-Za-z°%/㎜a-z가-힣]*\s*$")


def ex_choice(q):
    """해설 '오답' 줄을 보기 번호에서 떼어 원래 보기 순서 배열로 (정답 자리는 None)."""
    out = [None] * len(q["choices"])
    for s in (q.get("ex") or {}).get("오답") or []:
        m = re.match(r"^\s*([①-⑥])\s*(.*)$", s)
        if m:
            out[CIRC.index(m.group(1))] = m.group(2)
    return out


def auto_noshuffle(q):
    ch = q["choices"]
    if all(NUM.match(c) for c in ch):
        return "숫자 보기"
    if any(CROSS.search(c) for c in ch):
        return "보기끼리 가리킴"
    if re.search(r"[①-⑥]", q["stem"]):
        return "지문에 원 번호"
    return None


def auto_open(q):
    if q.get("fig") or NOT_OPEN.search(q["stem"]):
        return None
    a = q["choices"][q["ans"]]
    core = re.sub(r"\([^)]*\)", "", a).strip()
    if not core or len(norm(core)) > 14 or len(core.split()) > 3 or re.search(r"[,→~:=±]", core):
        return None
    if any(norm(c) == norm(a) for i, c in enumerate(q["choices"]) if i != q["ans"]):
        return None
    acc = [core]
    for alt in re.findall(r"\(([^)]*)\)", a):           # 괄호 안 다른 이름(해설집 보기 글자 그대로)
        if alt.strip() and not re.search(r"[=,:×±⁻]", alt):
            acc.append(alt.strip())
    return acc


def tag_old(q):
    box = ((q.get("ex") or {}).get("개념") or {}).get("title")
    t = q["t"]
    if t == "4지선다":
        item = q["choices"][q["ans"]]
    elif t == "단답형":
        item = q.get("ansText") or ""
    elif t == "계산형":
        item = "계산:" + (q.get("unit") or "")
    else:
        item = q["stem"][:40]
    if not box:
        box = "개념 상자 없음: " + re.sub(r"\s+", " ", str(item))[:20]
    return {"box": box, "item": str(item)}


def main():
    old = json.load(open(os.path.join(H, "quiz", "docs", "data", "questions.json"), encoding="utf-8"))
    parts = old["parts"]
    qs = []
    for q in old["questions"]:
        q = dict(q)
        q["src"] = "old"
        q["tag"] = tag_old(q)
        qs.append(q)
    new = []
    for f in sorted(glob.glob(os.path.join(P, "src", "new", "*.json"))):
        new += json.load(open(f, encoding="utf-8"))
    approved = set(lines(os.path.join(P, "src", "approved.txt")))
    if approved:
        for f in glob.glob(os.path.join(P, "work", "*", "보류.json")):
            new += [n for n in json.load(open(f, encoding="utf-8")) if n["id"] in approved]
    for n in new:
        n = {k: v for k, v in n.items() if k not in ("verify", "calcExpr", "basis")}
        n["src"], n["p"] = "new", "new"
        qs.append(n)

    calc = json.load(open(os.path.join(P, "src", "calc.json"), encoding="utf-8"))
    calc.pop("_설명", None)
    byid = {q["id"]: q for q in qs}
    errs = []
    for cid, c in calc.items():
        if cid not in byid:
            errs.append(f"calc.json: 없는 문항 {cid}")
            continue
        if "same" in c:
            base = dict(calc[c["same"]])
            base.update({k: v for k, v in c.items() if k != "same"})
            c = base
        byid[cid]["calc"] = c
    noshuf = set(lines(os.path.join(P, "src", "noshuffle.txt")))
    stats = {"섞지 않음": 0, "주관식 대상": 0, "CBT": 0}
    for q in qs:
        t = q["t"]
        if t == "4지선다" and q.get("choices"):
            if q["src"] == "old" or not q.get("exChoice"):
                q["exChoice"] = ex_choice(q)
            why = auto_noshuffle(q) or ("목록" if q["id"] in noshuf else None)
            if why:
                q["noShuffle"] = True
                stats["섞지 않음"] += 1
            op = auto_open(q)
            if op:
                q["open"] = op
                stats["주관식 대상"] += 1
        ok = (t in ("진위형", "4지선다") and q.get("ans") is not None) \
            or (t == "연결형" and q.get("left") and q.get("right") and q.get("ans")) \
            or (t == "단답형" and q.get("accept")) \
            or (t == "계산형" and q.get("value") is not None and q.get("unit"))
        if ok:
            q["cbt"] = True
            stats["CBT"] += 1
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    out = {"ver": len(qs), "parts": parts + [{"id": "new", "title": "새 문항", "group": "새 문항"}], "questions": qs}
    path = os.path.join(P, "docs", "data", "questions.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    n_new = sum(q["src"] == "new" for q in qs)
    print(f"문항 {len(qs)} (기존 {len(qs) - n_new}, 새 {n_new}), 계산 숫자 바꾸기 {sum('calc' in q for q in qs)}, {stats}")


if __name__ == "__main__":
    main()
