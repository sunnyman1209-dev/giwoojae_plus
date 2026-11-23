"""구글 시트 웹 앱 주소를 앱에 넣고 연결을 확인한다.
사용: connect_sheet.py <웹 앱 주소(https://script.google.com/macros/s/.../exec)>
1) 주소로 doGet(action=config)을 불러 설정 JSON이 오는지 확인
2) 통과하면 docs\\index.html의 SHEET_URL에 주소를 넣는다(저장소 올리기는 따로)"""
import json
import re
import sys
import urllib.request
from pathlib import Path

url = sys.argv[1].strip()
if not re.match(r"^https://script\.google\.com/macros/s/[\w-]+/exec$", url):
    sys.exit("주소 모양이 다르다. 'https://script.google.com/macros/s/…/exec' 꼴이어야 한다.")
with urllib.request.urlopen(url + "?action=config", timeout=30) as r:
    body = r.read().decode("utf-8", "replace")
try:
    cfg = json.loads(body)
except ValueError:
    sys.exit("설정 JSON이 아니다(배포 액세스가 '모든 사용자'인지, 설정하기를 실행했는지 확인): " + body[:200])
print("설정 읽기 성공:", cfg)
P = Path(__file__).resolve().parents[1] / "docs" / "index.html"
s = P.read_text(encoding="utf-8")
s2, n = re.subn(r'const SHEET_URL = "[^"]*";', f'const SHEET_URL = "{url}";', s, count=1)
if n != 1:
    sys.exit("index.html에서 SHEET_URL 줄을 찾지 못했다.")
P.write_text(s2, encoding="utf-8")
print("SHEET_URL을 넣었다:", P)
