r"""교재 예상문제(1~6회차) 객관식을 문항 초안으로 정리하고 블라인드 문제지를 만든다 (SPEC_1124 A, 작업표 02).

사용: python -I tools/textbook_batch.py <묶음 이름>
- 입력: 메인 작업 폴더 work\교재대조\items.json, merged.json('넣기')
- 출력: work\<묶음>\draft.json(정답 없음), work\<묶음>\r1_gpt|r1_cursor\blind.md + 위임 지시문
- 지문 손질(FIX)은 원문과 함께 work\<묶음>\손질.json에 남긴다. 정답 파일은 이 도구가 읽지 않는다.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
Q = Path(__file__).resolve().parents[1]
_g = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=Q, capture_output=True, text=True).stdout.strip()
MAIN_WORK = Path(_g).parent / "work"
SRC = MAIN_WORK / "교재대조"
B = Q / "work" / sys.argv[1]
C = "①②③④"
K = "㉠㉡㉢㉣㉤"
TYPES = {"4지선다형": "4지선다", "진위형": "진위형", "연결형": "연결형"}
SKIP = {"T5-14": "그림 문항(그림 없이 풀 수 없음)"}

# 지문·보기 손질: 오탈자·띄어쓰기·추출 깨짐만. {id: {필드: 새 값}} (원문은 손질.json에 함께 남는다)
FIX = {
    "T1-1": {"stem": "원점 복귀 시 절대 명령으로 이송시키는 것이 충돌을 방지하는 가장 올바른 방법이다."},
    "T1-2": {"stem": "ALTER 기능은 프로그램을 수정할 때 사용하는 기능이다."},
    "T1-4": {"stem": "3D 스케치 명령어 그룹으로 올바른 것을 찾아 연결하시오."},
    "T1-9": {"stem": "인서트 팁 규격 CNMG090308RF에서 N이 의미하는 것은?"},
    "T1-10": {"choices": ["스텝모터", "서보모터", "전기모터", "회전모터"]},
    "T1-24": {"stem": "다음 프로그램에서 오류가 나는 이유는?\nG90 G00 X5. X10. F100"},
    "T2-8": {"stem": "주성분이 W, Ti, Co, C 등인 공구합금은 무엇인가?"},
    "T3-3": {"right": ["측정값과 참값의 차이이며, 오차는 측정값 - 참값이다.",
                       "측정자의 부주의로 발생하는 오차이다.",
                       "오차와 참값(또는 측정값)의 비율이며, 오차 ÷ 참값(또는 측정값)이다."]},
    "T3-4": {"right": ["물체의 일부를 파단한 경계 또는 일부를 떼어 낸 경계를 표시하는 데 사용한다.",
                       "되풀이되는 도형의 피치를 취하는 기준을 표기하는 데 사용한다.",
                       "물체의 보이는 부분을 표시하는 데 사용한다."]},
    "T3-20": {"choices": ["크레이터 마모", "플랭크 마모", "치핑", "구성인선"]},
    "T3-24": {"stem": "다이얼 테스트 인디케이터나 다이얼게이지를 부착하여 고정용으로 널리 사용되며, 직각도, 진원도, 평행도를 측정할 때 사용하는 측정기 고정용 보조 기구로 옳은 것은?"},
    "T4-18": {"stem": "금속의 열처리 중 담금질(quenching)의 주된 목적은?"},
    "T5-7": {"stem": "구멍의 최소 치수에서 축의 최대 치수를 뺐을 때 구해지는 치수의 명칭으로 옳은 것은?"},
    "T5-19": {"stem": "피치 3 mm의 2줄 나사가 2회전하였을 때 이동 거리로 옳은 것은?"},
}


def parse(x):
    """추출 글 → (지문, 보기) 또는 (지문, 왼쪽, 오른쪽)."""
    t = x["text"].replace("–", "-")
    t = re.sub(r"\(\s*\)", "", t)
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    stem, rest = [], []
    for l in lines:
        (rest if rest or re.match(r"^[①-④]", l) else stem).append(l)
    stem = re.sub(r"\s+", " ", " ".join(stem)).strip()
    stem = re.sub(r"\s*\?$", "?", stem)
    sec = x["sec"]
    if sec == "연결형":
        left, right = [], []
        for l in rest:
            if l.startswith("⚫"):
                right.append(re.sub(r"^⚫\s*[㉠-㉤]?\s*", "", l).strip())
            elif re.match(r"^[①-④]", l):
                left.append(re.sub(r"^[①-④]\s*|\s*⚫$", "", l).strip())
        return {"stem": stem, "left": left, "right": right}
    ch = []
    for l in rest:
        if re.match(r"^[①-④]", l):
            ch.append(re.sub(r"^[①-④]\s*", "", l).strip())
        elif l in ("Ÿ",) or l.startswith("주성분:"):
            break
        elif ch and len(ch) < 4:
            ch[-1] += " " + l
    if sec == "진위형":
        stem = re.sub(r"(인가|하는가)\?$", "이다.", stem)
        return {"stem": stem}
    return {"stem": stem, "choices": ch[:4]}


def main():
    items = {x["id"]: x for x in json.loads((SRC / "items.json").read_text(encoding="utf-8"))}
    ins = json.loads((SRC / "merged.json").read_text(encoding="utf-8"))["넣기"]
    out, fixlog, skipped = [], [], []
    for iid in ins:
        x = items[iid]
        if x["r"] > 6 or x["sec"] not in TYPES:
            continue
        if iid in SKIP or x.get("fig"):
            skipped.append({"id": iid, "why": SKIP.get(iid, "그림 문항")})
            continue
        q = parse(x)
        for f, v in FIX.get(iid, {}).items():
            fixlog.append({"id": iid, "field": f, "원문": q.get(f), "고침": v})
            q[f] = v
        q = {"id": f"tb|{x['r']}-{x['n']}", "src_id": iid, "t": TYPES[x["sec"]], "pdf": x["pdf"], **q}
        if q["t"] == "4지선다" and len(q["choices"]) != 4:
            raise SystemExit(f"{iid} 보기 {len(q['choices'])}개")
        if q["t"] == "연결형" and len(q["left"]) != len(q["right"]):
            raise SystemExit(f"{iid} 연결 양쪽 개수 다름")
        out.append(q)
    B.mkdir(parents=True, exist_ok=True)
    (B / "draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (B / "손질.json").write_text(json.dumps({"fix": fixlog, "skip": skipped}, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 문제지 (정답 없음)", ""]
    for n, q in enumerate(out, 1):
        L.append(f"N{n}. [{q['t']}] {q['stem']}")
        if q["t"] == "4지선다":
            L.append("    " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["choices"])))
        elif q["t"] == "진위형":
            L.append("    O / X")
        else:
            L.append("    왼쪽: " + "  ".join(f"{C[i]} {c}" for i, c in enumerate(q["left"])))
            L.append("    오른쪽: " + "  ".join(f"{K[i]} {c}" for i, c in enumerate(q["right"])))
        L.append("")
    task = """`blind.md`의 문항(N1~)을 기계가공·CNC·CAD/CAM·측정·제도의 일반 지식으로 직접 풀어라.

- 파일을 수정하거나 만들지 말 것. 이 폴더 밖 파일을 읽지 말 것.
- 최종 응답은 표 하나만: | 번호 | 답 | 근거(한 줄) | 다른 답도 맞을 수 있는가 | 오류·모호함 |
- 모든 번호를 채운다. 4지선다는 번호(①~④)와 보기 글, 진위형은 O 또는 X, 연결형은 '①-㉠, ②-㉡' 꼴.
- 정답이 둘 이상이거나 보기 중 정답이 없을 수 있으면 반드시 '다른 답' 칸에 적는다. 확신이 없으면 '확신 낮음'.
"""
    ag = """# 블라인드 풀이 폴더

컴퓨터응용가공산업기사(과정평가형) 객관식 문항을 정답 없이 풀어 보는 폴더다.
- 한국어로 답한다.
- 이 폴더의 `blind.md`만 읽는다. 상위 폴더나 다른 파일은 읽지 않는다.
- 파일을 수정하거나 만들지 않는다. 답은 최종 응답으로만 낸다.
"""
    for name, sub in (("r1_gpt", ".gpt-delegate"), ("r1_cursor", ".cursor-delegate")):
        d = B / name
        (d / sub).mkdir(parents=True, exist_ok=True)
        (d / "blind.md").write_text("\n".join(L), encoding="utf-8")
        (d / "AGENTS.md").write_text(ag, encoding="utf-8")
        (d / sub / "task.md").write_text(task, encoding="utf-8")
    print(f"{len(out)}문항, 손질 {len(fixlog)}건, 제외 {len(skipped)}")


if __name__ == "__main__":
    main()
