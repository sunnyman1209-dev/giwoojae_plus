"""1차 묶음 보류 35문항 재판정 결과 읽기. 두 AI 모두 차이 2개 이하인 id를 approved 후보로 보여 준다."""
import json
import re
from pathlib import Path

W = Path(__file__).resolve().parents[1] / "work" / "1123"
order = json.loads((W / "rejudge_order.json").read_text(encoding="utf-8"))
res = {}
for who, d in (("GPT", "rejudge_gpt/.gpt-delegate"), ("Cursor", "rejudge_cursor/.cursor-delegate")):
    for line in (W / d / "result.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*R(\d+)\s*\|([^|]*)\|(.*)", line)
        if m:
            lv = m.group(2)
            res.setdefault(order[int(m.group(1)) - 1], {})[who] = (len(re.findall(r"[쉬어]", lv)), lv.strip(), m.group(3).strip(" |")[:80])
ok = [i for i in order if all(w in res.get(i, {}) and res[i][w][0] <= 2 for w in ("GPT", "Cursor"))]
print(f"응답 GPT {sum('GPT' in v for v in res.values())}, Cursor {sum('Cursor' in v for v in res.values())}; 통과 {len(ok)} / {len(order)}")
for i in order:
    r = res.get(i, {})
    tag = "통과" if i in ok else "보류"
    print(tag, i, " | ".join(f"{w}:{r[w][0]}({r[w][1]})" for w in ("GPT", "Cursor") if w in r))
(W / "rejudge_ok.txt").write_text("\n".join(ok), encoding="utf-8")
