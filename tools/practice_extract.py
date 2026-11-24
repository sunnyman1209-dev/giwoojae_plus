r"""외부평가 실전 모의고사(1회 종합, 2회 CNC밀링) 문항을 뽑고 문제은행 후보를 붙인다 (SPEC_1124 A, 작업표 04).

사용: python -I tools/practice_extract.py
- 입력: %USERPROFILE%\Documents\카카오톡 받은 파일\외부평가 실전 모의고사.hwpx (읽기만), docs/data/questions.json
- 출력: work/tb04/items.json(문항, 원본 정답·해설은 given에 따로), work/tb04/대조자료.md(문항별 비슷한 후보 5개),
        work/tb04/bank.md(문제은행 전체 한 줄 목록, 중복 판정 AI가 찾아볼 때 씀)
- tools/textbook_match.py(교재 예상문제)와 같은 2글자 묶음 겹침으로 후보를 고른다.
"""
import html
import json
import re
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
Q = Path(__file__).resolve().parents[1]
HWPX = Path.home() / "Documents" / "카카오톡 받은 파일" / "외부평가 실전 모의고사.hwpx"
OUT = Q / "work" / "tb04"
SEC = {"진위형": "진위형", "연결형": "연결형", "4지택일": "4지선다", "단답형": "단답형", "계산형": "계산형"}
C = "①②③④"
K = "㉠㉡㉢㉣"


def paras():
    z = zipfile.ZipFile(HWPX)
    out = []
    for n in sorted(x for x in z.namelist() if re.match(r"Contents/section\d+\.xml", x)):
        x = z.read(n).decode("utf-8")
        for p in re.findall(r"<hp:p[ >].*?</hp:p>", x, re.S):
            t = "".join(re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", p, re.S))
            t = html.unescape(re.sub(r"<[^>]+>", "", t))
            eq = re.findall(r"<hp:script>(.*?)</hp:script>", p, re.S)
            if eq:
                t += " [수식: " + " | ".join(html.unescape(e) for e in eq) + "]"
            if "<hp:pic" in p:
                t += " [그림]"
            for ln in t.split("\n"):
                if ln.strip():
                    out.append(ln.rstrip())
    return out


def split_items(lines):
    items, cur, r, sec = [], None, 1, ""
    for ln in lines:
        s = ln.strip()
        if s.startswith("외부평가 실전 모의고사 2회"):
            r, cur = 2, None
            continue
        m = re.match(r"^<\s*(진위형|연결형|4지택일|단답형|계산형)\s*>", s)
        if m:
            sec = SEC[m.group(1)]
            continue
        m = re.match(r"^(\d{1,2})\.\s*(.*)", s)
        if m and (cur is None and int(m.group(1)) == 1 or cur is not None and int(m.group(1)) == cur["n"] + 1):
            cur = {"id": f"mock|{r}-{int(m.group(1))}", "r": r, "n": int(m.group(1)), "sec": sec, "raw": [m.group(2)]}
            items.append(cur)
            continue
        if cur is not None:
            cur["raw"].append(s)
    return items


def cut_ex(raw):
    """(본문 줄, 해설 글, '정답:' 줄 글)"""
    body, ex, ans, in_ex = [], [], None, False
    for s in raw:
        m = re.match(r"^-?\s*정답\s*:\s*(.*)", s)
        if m:
            ans, in_ex = m.group(1).strip(), False
            continue
        m = re.match(r"^-?\s*해설\s*:\s*(.*)", s)
        if m:
            in_ex = True
            ex.append(m.group(1))
            continue
        (ex if in_ex else body).append(s)
    return body, " ".join(x for x in ex if x).strip(), ans


def paren_ans(s):
    m = re.search(r"\(\s*([①-④])\s*\)\s*$", s)
    return m.group(1) if m else None


def strip_paren(s):
    return re.sub(r"\s*\(\s*[①-④]?\s*\)\s*$", "", s).strip()


def parse(it):
    body, ex, ans = cut_ex(it["raw"])
    fig = any("[그림]" in s for s in body) or bool(re.search(r"그림을|사진을|다음 도면", body[0]))
    body = [s.replace("[그림]", "").strip() for s in body]
    body = [s for s in body if s and s != "●"]
    t = it["sec"]
    if it["r"] == 2 and it["n"] >= 48:  # 2회 48~50은 단답형 꼭지 아래에 있으나 계산과정·답이 붙은 계산형
        t = "계산형"
    q = {"id": it["id"], "r": it["r"], "n": it["n"], "t": t, "fig": fig}
    given = {"ex": ex}
    if t == "진위형":
        given["ans"] = paren_ans(body[0]) or (ans or "")[:1]
        st = []
        for s in body[1:]:
            if s.startswith("①"):
                break
            st.append(s)
        q["stem"] = " ".join(st)
        given["ans"] = {"①": "O", "②": "X"}.get(given["ans"], given["ans"])
    elif t == "연결형":
        head = body[0]
        rest = body[1:]
        if head.endswith("①"):
            head, rest = head[:-1], ["①"] + rest
        q["stem"] = head.strip()
        left, right, cur = [], [], None
        for s in rest:
            if s in C:
                cur = left
                left.append("")
            elif s in K:
                cur = right
                right.append("")
            elif cur is not None:
                cur[-1] = (cur[-1] + " " + s).strip()
        q["left"], q["right"] = left, right
        given["ans"] = ans
    elif t == "4지선다":
        st, ch = [], []
        for s in body:
            if ch or re.match(r"^[①-④]", s):
                ch.append(s)
            else:
                st.append(s)
        given["ans"] = paren_ans(st[0]) or (ans or "")[:1]
        st[0] = strip_paren(st[0])
        st = [strip_paren(s) for s in st]
        q["stem"] = "\n".join(s for s in st if s)
        q["choices"] = [c.strip() for c in re.split(r"[①-④]", " ".join(ch))[1:]]
    elif t == "단답형":
        if ans is None:
            ans = body[-1]
            body = body[:-1]
        q["stem"] = "\n".join(body)
        given["ans"] = re.sub(r"^[\W-]+", "", ans).strip()
    else:  # 계산형
        st, calc, a = [], [], None
        for s in body:
            m = re.match(r"^\W*답\s*:\s*(.*)", s)
            if m:
                a = m.group(1).strip()
            elif "계산과정" in s or calc:
                calc.append(s)
            else:
                st.append(s.lstrip("Ÿ").strip())
        q["stem"] = "\n".join(s for s in st if s)
        given["ans"] = a
        given["calc"] = " ".join(calc)
    q["given"] = given
    return q


def sq(s):
    return re.sub(r"[^가-힣A-Za-z0-9]", "", str(s))


def bg(s):
    s = sq(s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def full(q):
    return " ".join(map(str, [q.get("stem", ""), q.get("ansText", "")] + (q.get("choices") or []) + (q.get("left") or []) + (q.get("right") or [])))


def main():
    items = [parse(x) for x in split_items(paras())]
    QS = json.loads((Q / "docs" / "data" / "questions.json").read_text(encoding="utf-8"))["questions"]
    qb = [bg(full(q)) for q in QS]
    L = ["# 실전 모의고사 문항과 문제은행 후보 (2글자 묶음 겹침 상위 5개)", ""]
    for it in items:
        txt = it["stem"] + " " + " ".join(it.get("choices") or it.get("left", []) + it.get("right", [])) + " " + str(it["given"]["ans"])
        b = bg(txt)
        sc = sorted(((len(b & o) / max(1, min(len(b), len(o))), k) for k, o in enumerate(qb)), reverse=True)[:5]
        it["cand"] = [(round(s, 2), QS[k]["id"]) for s, k in sc]
        L.append(f"## {it['id']} ({it['t']}{', 그림' if it['fig'] else ''})")
        L.append(it["stem"])
        if it.get("choices"):
            L.append("보기: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(it["choices"])))
        if it.get("left"):
            L.append("왼쪽: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(it["left"])))
            L.append("오른쪽: " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(it["right"])))
        L.append(f"원본 정답: {it['given']['ans']}")
        for s, k in sc:
            q = QS[k]
            L.append(f"- 후보 {q['id']} [{s:.2f}] ({q['t']}) {full(q)[:260]}")
        L.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "대조자료.md").write_text("\n".join(L), encoding="utf-8")
    B = ["# 문제은행 전체 (id | 유형 | 지문·보기·정답)", ""]
    for q in QS:
        B.append(f"{q['id']} | {q['t']} | " + re.sub(r"\s+", " ", full(q))[:400])
    (OUT / "bank.md").write_text("\n".join(B), encoding="utf-8")
    from collections import Counter
    print(len(items), Counter((i["r"], i["t"]) for i in items), "그림", [i["id"] for i in items if i["fig"]])


if __name__ == "__main__":
    main()
