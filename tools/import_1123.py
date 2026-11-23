r"""첫 묶음(2026-11-23 종이 시험용 80문항) → src\new\1123.json + work\1123\보류.json

python -I quiz_plus\tools\import_1123.py

- 입력: quiz\work\variant\exam_1123.json ('가' 변형 40, '나' 새 기출형(쌍둥이) 40)
- 블라인드 풀이: 시험지_1123\검토기록.md (GPT 80/80, Cursor 79/80 → 어긋난 1문항 교체 후 재확인)
- 난이도: diff_gpt·diff_cursor 결과표. (나)는 두 모델 모두 '같음'인 문항만 넣고 나머지는 보류(교사 대조표).
- 해설(ex): 해설집 원문 줄만 쓴다. 원본 문항 해설·개념 상자에서 정답·보기 낱말이 들어 있는 줄을 골라 근거·오답으로 붙인다.
"""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # quiz_plus
H = os.path.dirname(P)                                             # 기우제반_해설집
V = os.path.join(H, "quiz", "work", "variant")
sys.path.insert(0, os.path.join(H, "tools"))
from hs import parse  # noqa: E402

CIRC, PAIR = "①②③④⑤⑥", "㉠㉡㉢㉣㉤㉥"
norm = lambda s: re.sub(r"[\s·,.\-_'\"()\[\]]", "", re.sub(r"\([^)]*\)", "", str(s or ""))).lower()


# 4지 오답 이유: 자동으로 고르면 한 글자 보기(S·T 등)가 엉뚱한 줄에 걸리므로, 개념 상자 표의 줄을 그대로 풀어 적는다.
OVR = {
    "g1|17v1": {"근거": "개념 상자 '자동 운전 보조 기능' 표: 머신 록은 축은 움직이지 않고 화면 좌표만 변한다.",
                "오답": ["① 싱글블록: 한 블록씩 실행한 뒤 정지하는 기능이다.",
                        "③ 드라이런: 프로그램의 F를 무시하고 조작판 이송속도로 이동하는 기능이다.",
                        "④ 피드홀드: 자동 운전 중 이송을 잠시 멈추는 기능이다."]},
    "g2|22v1": {"근거": "개념 상자 'CNC 프로그램 주소(어드레스)' 표: T는 공구 기능이다.",
                "오답": ["① S: 주축 기능이다.", "③ F: 이송 기능이다.", "④ M: 보조 기능이다."]},
    "g2|27v1": {"근거": "개념 상자 '머시닝센터 공구 보정' 표: 공구 지름 좌측·우측·취소(G41·G42·G40)의 번호는 D이다. 예: G41 X0. Y0. D12;",
                "오답": ["① S: 주축 기능(회전수)이다.", "② H: 공구 길이 보정(G43·G44·G49)의 번호이다.", "③ T: 공구 기능이다."]},
    "g3|13v1": {"근거": "개념 상자 '기하공차의 종류' 표: 자세 공차는 평행도, 직각도, 경사도이다.",
                "오답": ["② 진직도공차: 모양 공차이다.", "③ 평면도공차: 모양 공차이다.", "④ 대칭도공차: 위치 공차이다."]},
}


def table(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def load_parts():
    parts = {}
    for f in os.listdir(os.path.join(H, "해설")):
        if f.endswith(".md"):
            items, _ = parse(os.path.join(H, "해설", f))
            con = {}
            for it in items.values():
                if it.get("개념"):
                    cid, _, title = it["개념"].partition("|")
                    con[cid.strip()] = {"title": title.strip(), "body": it["개념본문"]}
            parts[f[:-3]] = (items, con)
    return parts


def src_lines(h, con):
    """원본 문항 해설의 모든 줄(해설집 원문)."""
    L = []
    for k in ("근거", "정의", "비슷한말", "고친문장", "보충"):
        if h.get(k):
            L.append(h[k])
    for k in ("오답", "짝"):
        L += h["_lists"].get(k, [])
    return L


def main():
    E = json.load(open(os.path.join(V, "exam_1123.json"), encoding="utf-8"))
    dg = table(os.path.join(V, "diff_gpt", ".gpt-delegate", "result.md"))
    dc = table(os.path.join(V, "diff_cursor", ".cursor-delegate", "result.md"))
    parts = load_parts()
    ok, hold, warn = [], [], []
    for kind in ("가", "나"):
        for q in E[kind]:
            part, no = q["src"].split("|")
            items, con = parts[part]
            h = items[no]
            cid_tag, _, item = q["tag"].partition("-")
            box = con.get(cid_tag) or next((c[1][cid_tag] for c in parts.values() if cid_tag in c[1]), None)
            if not box:
                warn.append(f"{kind}{q['no']} 꼬리표 개념 상자 '{cid_tag}' 없음")
            src_cid = (h.get("개념") or "").partition("|")[0].strip() or (h.get("참조") or "").strip()
            box = box or con.get(src_cid)
            n = {"id": q["src"] + "v1", "from": q["src"], "kind": kind, "src": "new", "t": q["t"],
                 "stem": q["stem"], "tag": {"box": box["title"] if box else cid_tag, "item": item}}
            lines = src_lines(h, con) + (box["body"] if box else [])
            pick = lambda keys: [l for l in lines if not l.lstrip().startswith("|")
                                 and any(len(norm(k)) >= 2 and norm(k) in norm(l) for k in keys)]
            ex = {}
            t = q["t"]
            if t == "진위형":
                n["ans"] = q["ans"]
                n["ansText"] = q["ans"]
            elif t == "4지선다":
                a = q["ans"] - 1
                n["choices"], n["ans"] = q["choices"], a
                n["ansText"] = f"{CIRC[a]} {q['choices'][a]}"
                ex["오답"] = []
                for i, c in enumerate(q["choices"]):
                    if i == a:
                        continue
                    m = pick([c])
                    ex["오답"].append(f"{CIRC[i]} {c}: " + (m[0] if m else "이 문제의 답이 아니다(개념 상자 참고)."))
                g = pick([q["choices"][a]])
                if g:
                    ex["근거"] = g[0]
            elif t == "연결형":
                n["left"], n["right"] = q["left"], q["right"]
                pr = re.findall(r"([①-⑥])-([㉠-㉥])", q["ans"])
                key = [None] * len(pr)
                for l, r in pr:
                    key[CIRC.index(l)] = PAIR.index(r)
                n["ans"], n["ansText"] = key, q["ans"]
            elif t == "단답형":
                n["accept"], n["ans"], n["ansText"] = q["accept"], None, q["ans"]
                g = pick([q["ans"]] + q["accept"])
                if g:
                    ex["근거"] = " ".join(g[:2])
            elif t == "계산형":
                n["value"], n["ans"], n["ansText"] = q["value"], None, q["ans"]
                m = re.match(r"^\s*[-\d.,]+\s*(.*)$", q["ans"])
                n["unit"] = m.group(1).strip() if m else ""
                n["calcExpr"] = q.get("calc")
            ex.update(OVR.get(n["id"], {}))
            if not ex.get("근거") and box and t == "단답형":   # 개념 상자 표에서 정답 칸이 있는 줄
                keys = {norm(k) for k in [q["ans"]] + q.get("accept", []) if norm(k)}
                for l in box["body"]:
                    cells = [c.strip() for c in l.strip().strip("|").split("|")] if l.lstrip().startswith("|") else []
                    if any(norm(c) in keys or any(norm(x) in keys for x in re.split(r"[/·,]", c)) for c in cells):
                        ex["근거"] = f"개념 상자 '{box['title']}' 표: " + " — ".join(c for c in cells if c)
                        break
            if not ex.get("근거"):
                ex["근거"] = "아래 개념 상자에 이 문제의 근거가 있다."
            if box:
                ex["개념"] = box
            n["ex"] = ex
            n["verify"] = {"blind": "GPT·Cursor 블라인드 풀이 일치 (quiz\\work\\variant\\시험지_1123\\검토기록.md)"}
            if kind == "나":
                n["verify"]["level"] = {"gpt": dg.get(q["no"]), "cursor": dc.get(q["no"])}
                if not (dg.get(q["no"]) == "같음" and dc.get(q["no"]) == "같음"):
                    hold.append(n)
                    continue
            ok.append(n)
    os.makedirs(os.path.join(P, "src", "new"), exist_ok=True)
    os.makedirs(os.path.join(P, "work", "1123"), exist_ok=True)
    json.dump(ok, open(os.path.join(P, "src", "new", "1123.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(hold, open(os.path.join(P, "work", "1123", "보류.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 교사 대조표
    L = ["# 첫 묶음(2026-11-23) 보류 문항 대조표", "",
         "새 기출형(쌍둥이)은 GPT·Cursor 두 모델이 모두 원본 대비 난이도 '같음'으로 본 문항만 문제은행에 넣었다(SPEC 8절).",
         "아래 문항은 정답은 세 모델이 일치했지만 난이도 판정이 '같음'으로 모이지 않아 보류했다.",
         "넣어도 되는 문항은 `src\\approved.txt`에 id를 한 줄씩 적고 `build_plus.py`를 다시 돌리면 들어간다.", "",
         "| id | 유형 | 새 문항 | GPT | Cursor |", "|---|---|---|---|---|"]
    for n in hold:
        L.append(f"| {n['id']} | {n['t']} | {n['stem'].replace('|', '/')} | {n['verify']['level']['gpt']} | {n['verify']['level']['cursor']} |")
    open(os.path.join(P, "work", "1123", "대조표.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"넣음 {len(ok)}, 보류 {len(hold)}")
    for w in warn:
        print("경고", w)
    nb = [n["id"] for n in ok if n["ex"]["근거"].startswith("아래 개념")]
    print("근거 줄을 못 찾아 개념 상자만 붙인 문항", len(nb), nb)


if __name__ == "__main__":
    main()
