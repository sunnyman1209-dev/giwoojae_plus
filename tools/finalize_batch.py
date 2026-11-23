"""draft.json + results.json → src\\new\\<묶음>.json(통과) 와 work\\<묶음>\\대조표.md(보류).
통과: 두 AI 정답 일치, 쌍둥이는 두 AI 모두 난이도 차이 기준 2개 이하, items 파일의 HOLD에 없음.
사용: finalize_batch.py <묶음>"""
import importlib.util
import json
import sys
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
B = Q / "work" / sys.argv[1]
DR = json.loads((B / "draft.json").read_text(encoding="utf-8"))
RS = json.loads((B / "results.json").read_text(encoding="utf-8"))
HOLD = set()
for f in B.glob("items_*.py"):
    spec = importlib.util.spec_from_file_location(f.stem, f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    HOLD |= getattr(m, "HOLD", set())
C = "①②③④"
import re


def josa(word):
    """받침을 보고 은/는을 고른다(한글은 받침, 숫자·영문은 읽는 소리 기준)."""
    ch = word.rstrip(")）]\"' ")[-1:] or "가"
    if "가" <= ch <= "힣":
        return "은" if (ord(ch) - 0xAC00) % 28 else "는"
    if ch.isdigit():
        return "은" if ch in "013678" else "는"
    return "은" if ch.upper() in "LMNR" else "는"


def clean_tf(g):
    """다른 방향 진위형 해설에서 원래 4지 문항을 가리키는 말과 '은(는)'을 고친다."""
    g = re.sub(r"(\S+?)은\(는\)", lambda m: m.group(1) + josa(m.group(1)), g)
    g = re.sub(r"\s*\(문항의[^)]*\)", "", g)
    g = re.sub(r"\s*(문제|문항)의 '[^']*'[^.]*\.", "", g)
    g = re.sub(r"\s*문항은[^.]*\.", "", g)
    g = g.replace("보기 중에서는 ", "").replace("이 답이다.", "이 맞다.").replace("문제 조건과", "문장의 조건과")
    g = g.replace("그래서 답은 이다.", "그래서 절삭속도의 단위는 m/min이다.")
    # X 해설 앞머리 겹침: '틀리다. 앤빌의 고정은 앤빌은 …' → '틀리다. 앤빌은 …'
    m = re.match(r"^틀리다\. ([^.]+?)(은|는) ((?:\S+ ){0,2}?\S+?(?:은|는|에는)) ", g)
    if m:
        term, topic = m.group(1), m.group(3)
        hang = {term[i:i + 2] for i in range(len(term) - 1) if "가" <= term[i] <= "힣"}
        alnum = set(re.findall(r"[A-Za-z]+\d*|\d+", term))
        if any(h in topic for h in hang) or any(a in topic for a in alnum):
            g = "틀리다. " + g[len("틀리다. ") + len(term) + len(m.group(2)) + 1:]
    return g.strip()


# 두 AI 해설 검토(2026-11-23 tf_review)에서 4지 흔적이 남았다고 지적된 해설을 새로 쓴 것
OVR = {
    "g2|24t1": "옳다. CNC 선반에서 X·Z는 프로그램 원점 기준의 절대 지령이고, U·W는 현재 위치에서 움직일 거리를 주는 상대(증분) 지령이다. 'G01 U20. W-20.'은 두 축을 모두 U·W로 썼으므로 상대 지령이다.",
    "g5|12t1": "옳다. CNC 선반에서 X·Z는 절대값 주소, U·W는 현재 위치에서 움직일 거리를 쓰는 증분값 주소이다. 'G01 U10. W10.'은 두 축을 모두 U·W로 썼으므로 증분값 지령이다.",
    "m1|14t2": "틀리다. G04에서 U는 초 단위이므로 G04 U5.는 5초 정지이다. 문장의 설명에 해당하는 것은 G04 X0.5이다.",
    "g3|15t2": "틀리다. 재료 기호에는 제품의 지름 같은 크기를 적지 않는다. GC200의 200은 최저 인장강도(200 N/mm²)를 뜻한다.",
    "m2|4t2":"옳다. CNC 선반은 주소 문자로 절대·증분을 구분한다. X·Z는 프로그램 원점에서 잰 위치(절대값), U·W는 지금 위치에서 움직일 거리(증분값)이다. 'G01 X10. Z10.'은 두 축을 모두 X·Z로 썼으므로 절대값 지령이다.",
}


ok_list, held = [], []
for q in DR:
    r = RS.get(q["id"], {})
    why = []
    for w in ("GPT", "Cursor"):
        if w not in r:
            why.append(f"{w} 응답 없음")
            continue
        good, a, diff, dirn, note = r[w]
        if not good:
            why.append(f"{w} 답 '{a}'")
        if q["kind"] == "나" and diff > 2:
            why.append(f"{w} 난이도 차이 {diff}({dirn})")
    if q["id"] in HOLD:
        why.append("다른 이름 답(교사 판단)")
    if why:
        held.append((q, why, r))
        continue
    n = dict(q)
    n.pop("_n", None)
    if n["t"] == "4지선다":
        rest = [i for i in range(4) if i != n["ans"]]
        n["ex"] = dict(n["ex"])
        n["ex"]["오답"] = [f"{C[i]} {txt}" for i, txt in zip(rest, n.pop("exChoice"))]
    if n["t"] == "진위형" and re.search(r"t\d$", n["id"]):
        n["ex"] = dict(n["ex"])
        n["ex"]["근거"] = OVR.get(n["id"]) or clean_tf(n["ex"]["근거"])
    n["verify"] = {"blind": f"GPT·Cursor 블라인드 풀이 일치 (quiz_plus\\work\\{sys.argv[1]}\\results.json)"}
    if n["kind"] == "나":
        n["verify"]["level"] = {"gpt": f"차이 {r['GPT'][2]}", "cursor": f"차이 {r['Cursor'][2]}",
                                "rule": "여섯 기준 중 차이 2개 이하(2026-11-23)"}
    ok_list.append(n)

(Q / "src" / "new" / f"{sys.argv[1]}.json").write_text(json.dumps(ok_list, ensure_ascii=False, indent=1), encoding="utf-8")
L = [f"# {sys.argv[1]} 묶음 대조표 (교사 판단 대기)", "",
     "통과하지 못한 문항이다. 넣으려면 문항 id를 `src\\approved.txt`에 적거나 고칠 점을 알려 주면 된다.", ""]
for q, why, r in held:
    L.append(f"## {q['id']} ({q['kind']}, {q['t']})")
    L.append(f"- 지문: {q['stem']}")
    if q.get("choices"):
        L.append("- 보기: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
    L.append(f"- 정답: {q['ansText']}")
    L.append(f"- 보류 이유: {'; '.join(why)}")
    for w in ("GPT", "Cursor"):
        if w in r and r[w][4]:
            L.append(f"- {w} 의견: {r[w][4]}")
    L.append("")
(B / "대조표.md").write_text("\n".join(L), encoding="utf-8")
print(f"통과 {len(ok_list)}개 → src\\new\\{sys.argv[1]}.json, 보류 {len(held)}개 → 대조표.md")
