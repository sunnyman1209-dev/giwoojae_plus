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
