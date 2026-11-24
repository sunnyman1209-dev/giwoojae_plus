# 기우제반 플러스

기우제반 퀴즈(gwooje-quiz)에 새 문항과 CBT 시험을 더한 별도 앱. 명세는 `SPEC.md`.

- 공개 주소: https://sunnyman1209-dev.github.io/giwoojae_plus/ (학습 `#learn`, 시험 `#exam`, 연습 `#exam-demo`, 내 시험 결과 `#exam-results`)
- 저장소: github.com/sunnyman1209-dev/giwoojae_plus (main 브랜치 `docs\` 폴더를 GitHub Pages로 공개)

## 화면
- 처음 화면: 학습 / 시험(CBT) / 내 시험 결과(이 기기에서 제출한 시험이 있을 때).
- 학습: 문제은행 전체에서 무작위 한 문제씩, 출처 표시 없음, 틀린 문항은 10~20문제 뒤 다시. 계산형은 풀 때마다 숫자를 새로 뽑고, 4지는 보기 순서를 섞는다. 범위 시트에서 '주관식 모드'를 켜면 답이 용어·코드·숫자 하나인 4지는 보기 없이 입력한다. '이 문제 신고'는 시트 '신고' 탭으로 간다.
- 시험: 크롬에서만. 이름 → 안내 → 40문항(진위 2·연결 3·4지 25·단답 8·계산 2, 1~30번 2점·31~40번 4점) → 제출하면 바로 점수, 문항별 맞음·틀림, 정답, 해설. 시험지·답·제출 번호는 그 기기에 남아 '내 시험 결과'에서 다시 연다(다른 기기에서는 못 봄).
- 연습(`#exam-demo`, `#exam-demo-closed`): 크롬 확인과 기록 전송 없이 시험 흐름을 미리 본다. 교사 리허설·점검용.

## 시험 운영 (교사)
1. 처음 한 번: `apps-script\기우제플러스.gs`를 script.google.com 새 프로젝트에 붙여 넣고 `설정하기` 실행 → 배포 > 새 배포 > 웹 앱(실행: 나, 액세스: 모든 사용자) → 웹 앱 주소를 `docs\index.html`의 `SHEET_URL`에 넣고 올린다.
2. 시험 날: 시트 '설정' 탭 B1 회차(기록표 회차 이름과 똑같이, 예: `8회차`), B3 제한 시간(분), B2를 `열림`으로.
3. 끝나면 B2를 `닫힘`(닫은 뒤 제출은 '마감 후'). 편집기에서 `기록표용_만들기` 실행 → '기록표용' 탭을 CSV로 내려받기.
4. `Desktop\학생명단`에서:
   ```
   python -I CBT점수_가져오기.py <내려받은.csv> 8회차 YYYYMMDD
   ```
   명단에 없는 이름이 있으면 멈추고 글자 수만 알린다(`--skip-unknown`으로 빼고 진행). 결과는 `산기모의고사_8회차.html`.
- 결과 탭 '상태': 첫 응시 / 재응시(같은 이름, 첫 점수 인정) / 마감 후. '탭 이탈'은 시험 중 다른 화면으로 나간 횟수.
- 알려진 한계: 크롬 시크릿 창은 못 막는다. 문제은행과 채점이 기기에 있어 기술을 아는 학생은 정답을 미리 보거나 가짜 점수를 보낼 수 있다. 다른 이름 응시, 두 번째 기기 사용은 막지 못한다.

## 폴더
| 경로 | 내용 |
|---|---|
| `docs\` | 올리는 사이트(index.html, data\questions.json, fig\, robots.txt) |
| `src\new\*.json` | 새 문항(검증 통과분) |
| `src\calc.json` | 계산형 숫자 바꾸기 정의 |
| `src\approved.txt` | 보류 문항 중 교사가 넣기로 한 id(한 줄에 하나) |
| `src\noshuffle.txt` | 보기 순서를 섞지 않을 4지 id(자동 판정에 더함) |
| `tools\build_plus.py` | 기존 590 + 새 문항 + calc → `docs\data\questions.json` |
| `tools\check_plus.py` | 데이터 검증기 |
| `tools\test_engine.js` | 앱 엔진(계산·섞기·채점·시험지 조합 1,000번) 시험 |
| `tools\import_1123.py` | 첫 묶음(2026-11-23 종이 시험 80문항) 가져오기 |
| `apps-script\기우제플러스.gs` | 구글 시트 웹 앱(설정·결과·신고) |
| `work\` | 보류 문항·대조표 등 작업용. 저장소에 올리지 않는다 |

## 고칠 때
```
python -I quiz_plus\tools\build_plus.py
python -I quiz_plus\tools\check_plus.py
node quiz_plus\tools\test_engine.js
```
세 개가 모두 통과하면 `docs\`를 올린다. 해설집을 고쳤으면 먼저 `quiz\tools\build_data.py`로 기존 앱 데이터를 다시 만든다. (`python`은 `%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe`)
