"""재판정 통과 id를 approved.txt에 넣고 보류.json의 verify.level을 새 기준 값으로 바꾼다."""
import json
import re
from pathlib import Path

Q = Path(__file__).resolve().parents[1]
W = Q / "work" / "1123"
ok = (W / "rejudge_ok.txt").read_text(encoding="utf-8").split()
order = json.loads((W / "rejudge_order.json").read_text(encoding="utf-8"))
res = {}
for who, d in (("gpt", "rejudge_gpt/.gpt-delegate"), ("cursor", "rejudge_cursor/.cursor-delegate")):
    for line in (W / d / "result.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*R(\d+)\s*\|([^|]*)\|", line)
        if m:
            res.setdefault(order[int(m.group(1)) - 1], {})[who] = len(re.findall(r"[쉬어]", m.group(2)))
H = json.loads((W / "보류.json").read_text(encoding="utf-8"))
for h in H:
    if h["id"] in ok:
        r = res[h["id"]]
        h["verify"]["level"] = {"gpt": f"차이 {r['gpt']}", "cursor": f"차이 {r['cursor']}",
                                "rule": "여섯 기준 중 차이 2개 이하(2026-11-23 재판정)"}
(W / "보류.json").write_text(json.dumps(H, ensure_ascii=False, indent=1), encoding="utf-8")
ap = Q / "src" / "approved.txt"
lines = ap.read_text(encoding="utf-8").splitlines() if ap.exists() else []
add = [i for i in ok if i not in lines]
if add:
    lines += ["# 2026-11-23 여섯 기준 재판정 통과(두 AI 모두 차이 2개 이하)"] + add
ap.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("approved 추가", len(add))
