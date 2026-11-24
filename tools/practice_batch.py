r"""실전 모의고사 '앱에 없음' 문항을 초안으로 정리하고 블라인드 문제지를 만든다 (SPEC_1124 A, 작업표 04). tools/textbook_batch.py와 같은 흐름.

사용: python -I tools/practice_batch.py
- 입력: work/tb04/items.json, work/tb04/merged.json('없음')
- 출력: work/tb04/draft.json(정답 없음), work/tb04/손질.json(원문과 고친 글), 블라인드 폴더
        work/tb04/r1_gpt|r1_cursor|r1_claude/blind.md + 위임 지시문
- 원본 정답·해설(given)은 문제지에 넣지 않는다.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
Q = Path(__file__).resolve().parents[1]
B = Q / "work" / "tb04"
C = "①②③④"
K = "㉠㉡㉢㉣"
SKIP = {}  # {id: 이유} 그림이 필요하거나 뜻을 바꿔야 풀 수 있는 문항

# 지문·보기 손질: 명백한 오탈자·띄어쓰기만. {id: {필드: 새 값}} (원문은 손질.json에 남는다)
FIX = {
    "mock|1-1": {"stem": "원점 복귀 시 절대 명령으로 이송시키는 것이 충돌을 방지하는 가장 올바른 방법이다."},
    "mock|1-10": {"choices": ["스텝모터", "회전모터", "전기모터", "서보모터"]},
    "mock|1-47": {"stem": "지름 16 mm의 드릴을 사용하여 공작물을 가공한다. 이때, 드릴의 날 끝에서 뒷날까지의 하강량(여유 높이) h가 1.4 mm일 때 여유각(α)을 구하시오."},
    "mock|1-49": {"stem": "선반에서 공작물을 척에 고정한 뒤, 다이얼 게이지로 원주를 1회전 돌려 측정하였다. 다이얼 게이지의 최댓값은 +0.04 mm, 최솟값은 -0.03 mm였다. 이때 공작물의 편위량을 구하시오."},
    "mock|2-16": {"choices": ["형상의 최소 안전 높이를 설정하는 방법이다.", "형상에 따라 각기 다른 가공패턴을 적용하기 위한 영역 설정 방법이다.", "형상의 정삭 여유를 설정하는 최적화 방법이다.", "가공소재의 재질을 설정하기 위한 방법이다."]},
    "mock|2-30": {"stem": "원호를 가공하는 데 시점에서 원호의 중심까지의 거리를 지정하는 데 X성분의 어드레스는?"},
}


def main():
    items = {x["id"]: x for x in json.loads((B / "items.json").read_text(encoding="utf-8"))}
    ins = json.loads((B / "merged.json").read_text(encoding="utf-8"))["없음"]
    out, fixlog, skipped = [], [], []
    for iid in ins:
        x = items[iid]
        if iid in SKIP or x["fig"]:
            skipped.append({"id": iid, "why": SKIP.get(iid, "그림 문항")})
            continue
        q = {k: x[k] for k in ("stem", "choices", "left", "right") if k in x}
        for f, v in FIX.get(iid, {}).items():
            fixlog.append({"id": iid, "field": f, "원문": q.get(f), "고침": v})
            q[f] = v
        q = {"id": iid, "t": x["t"], **q}
        if q["t"] == "4지선다" and len(q["choices"]) != 4:
            raise SystemExit(f"{iid} 보기 {len(q['choices'])}개")
        if q["t"] == "연결형" and len(q["left"]) != len(q["right"]):
            raise SystemExit(f"{iid} 연결 양쪽 개수 다름")
        out.append(q)
    (B / "draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (B / "손질.json").write_text(json.dumps({"fix": fixlog, "skip": skipped}, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 문제지 (정답 없음)", ""]
    for n, q in enumerate(out, 1):
        L.append(f"N{n}. [{q['t']}] " + q["stem"].replace("\n", "\n    "))
        if q["t"] == "4지선다":
            L.append("    " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
        elif q["t"] == "진위형":
            L.append("    O / X")
        elif q["t"] == "연결형":
            L.append("    왼쪽: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["left"])))
            L.append("    오른쪽: " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(q["right"])))
        L.append("")
    task = """`blind.md`의 문항(N1~)을 기계가공·CNC·CAD/CAM·측정·제도의 일반 지식으로 직접 풀어라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- 최종 응답은 표 하나만: | 번호 | 답 | 근거(한 줄) | 다른 답도 맞을 수 있는가 | 오류·모호함 |
- 모든 번호를 채운다. 4지선다는 번호(①~④)와 보기 글, 진위형은 O 또는 X, 연결형은 '①-㉠, ②-㉡' 꼴,
  단답형은 답 낱말, 계산형은 '값 단위'(소수 둘째 자리까지, 예: 26.67 초)와 계산식.
- 정답이 둘 이상이거나 보기 중 정답이 없을 수 있으면 반드시 '다른 답' 칸에 적는다. 확신이 없으면 '확신 낮음'.
"""
    ag = """# 블라인드 풀이 폴더

컴퓨터응용가공산업기사(과정평가형) 문항을 정답 없이 풀어 보는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `blind.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
    for name, sub in (("r1_gpt", ".gpt-delegate"), ("r1_cursor", ".cursor-delegate"), ("r1_claude", None)):
        d = B / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "blind.md").write_text("\n".join(L), encoding="utf-8")
        (d / "AGENTS.md").write_text(ag, encoding="utf-8")
        if sub:
            (d / sub).mkdir(parents=True, exist_ok=True)
            (d / sub / "task.md").write_text(task, encoding="utf-8")
        else:
            (d / "task.md").write_text(task, encoding="utf-8")
    print(f"{len(out)}문항, 손질 {len(fixlog)}건, 제외 {len(skipped)}")


if __name__ == "__main__":
    main()
