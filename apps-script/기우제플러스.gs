/**
 * 기우제반 플러스 시험 기록 스크립트 (SPEC 7-2, 7-4, 9절)
 *
 * 붙이는 곳: script.google.com 에서 새 프로젝트(독립 프로젝트)
 * 처음 한 번: 함수 목록에서 '설정하기' 실행 → 배포 > 새 배포 > 웹 앱(실행: 나, 액세스: 모든 사용자)
 *            → 웹 앱 주소를 docs/index.html 의 SHEET_URL 에 넣는다.
 * 고친 뒤: 저장 + 배포 관리 > 수정 > 새 버전 (doGet·doPost가 바뀐 경우)
 * 교사용 화면: 앱 주소 뒤에 #teacher. 비밀번호는 TEACHER_PW_INIT에 적고 '설정하기'를 실행해 저장한다.
 *   시험 열기·닫기, 회차·제한 시간, 결과 보기, 기록표용 CSV 내려받기를 그 화면에서 한다(시트를 열 필요 없음).
 *
 * 탭
 *   설정    : B1 회차(기록표 회차 이름과 똑같이, 예: 8회차) / B2 상태(열림·닫힘) / B3 제한 시간(분)
 *   결과    : 제출 한 번에 한 줄. 회차 | 이름 | 점수 | 탭 이탈 | 상태 | 제출 시각 | 브라우저 | 제출 번호
 *             제출 번호는 제출 응답으로 학생 기기에 돌려주며, 기기의 '내 시험 결과'와 이 줄을 잇는 열쇠다.
 *   기록표용 : '기록표용_만들기'를 실행하면 설정 회차의 첫 응시만 이름 | 점수 로 정리한다(CSV로 내려받아 점수표에 넣음)
 *   신고    : 학습 화면의 '이 문제 이상해요'. 시각 | 문항 id | 보인 내용 | 사유 | 처리
 */

const T_SET = '설정', T_RES = '결과', T_REC = '기록표용', T_REP = '신고';
const HEAD = {
  [T_RES]: ['회차', '이름', '점수', '탭 이탈', '상태', '제출 시각', '브라우저', '제출 번호'],
  [T_REC]: ['이름', '점수'],
  [T_REP]: ['시각', '문항 id', '보인 내용', '사유', '처리']
};
const REPORT_PER_DAY = 50;   // 같은 문항 신고를 하루에 받는 최대 수
// 교사용 화면(#teacher) 비밀번호. 붙여 넣은 뒤 여기에 적고 '설정하기'를 한 번 실행하면 스크립트 속성에 저장된다.
// 공개 저장소에는 비워 둔다(저장된 뒤에는 이 줄을 다시 비워도 된다).
const TEACHER_PW_INIT = '';
const PW_FAIL_LIMIT = 10;     // 10분 안에 비밀번호를 이만큼 틀리면 10분 동안 교사용 명령을 막는다

/* ---------- 공통 ---------- */
function ss_() {
  const id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  if (id) return SpreadsheetApp.openById(id);
  const active = SpreadsheetApp.getActive();
  if (active) return active;
  throw new Error('먼저 편집기에서 설정하기를 실행하세요.');
}
// 이름 비교는 띄어쓰기를 무시한다(홍 길동 = 홍길동)
function norm_(s) { return String(s == null ? '' : s).replace(/^'/, '').replace(/\s+/g, ''); }
// =, +, -, @로 시작하는 글이 수식으로 읽히지 않게 한다
function safe_(s) { s = String(s); return /^[=+@-]/.test(s) ? "'" + s : s; }
function tab_(ss, name) {
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    if (HEAD[name]) { sh.getRange(1, 1, 1, HEAD[name].length).setValues([HEAD[name]]).setFontWeight('bold'); sh.setFrozenRows(1); }
  }
  return sh;
}
function out_(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
function config_(ss) {
  const v = tab_(ss, T_SET).getRange('B1:B3').getValues();
  const round = String(v[0][0]).trim();
  const open = String(v[1][0]).trim() === '열림';
  const minutes = Math.max(1, Math.round(Number(v[2][0]) || 30));
  return { round: round, open: open && !!round, minutes: minutes };
}

/* ---------- 처음 설정 ---------- */
function 설정하기() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('SHEET_ID');
  const ss = id ? SpreadsheetApp.openById(id) : (SpreadsheetApp.getActive() || SpreadsheetApp.create('기우제플러스 기록'));
  props.setProperty('SHEET_ID', ss.getId());
  if (TEACHER_PW_INIT) { props.setProperty('TEACHER_PW', String(TEACHER_PW_INIT)); Logger.log('교사용 비밀번호를 저장했습니다.'); }
  Logger.log('기록 시트 주소: ' + ss.getUrl());
  const st = tab_(ss, T_SET);
  st.getRange('A1:A3').setValues([['회차'], ['상태'], ['제한 시간(분)']]).setFontWeight('bold');
  if (!st.getRange('B2').getValue()) st.getRange('B2').setValue('닫힘');
  if (!st.getRange('B3').getValue()) st.getRange('B3').setValue(30);
  st.getRange('B2').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(['열림', '닫힘'], true).build());
  st.getRange('A5').setValue('회차는 기록표의 회차 이름과 똑같이 적는다(예: 8회차). 시험을 열 때 상태를 열림, 끝나면 닫힘으로 바꾼다. 학생은 제출 직후 점수·정답·해설을 본다.');
  [T_RES, T_REC, T_REP].forEach(n => tab_(ss, n));
  const s1 = ss.getSheetByName('시트1'); if (s1 && ss.getSheets().length > 1) ss.deleteSheet(s1);
  Logger.log('설정 완료');
}

/* ---------- 앱이 읽는 설정 ---------- */
function doGet(e) {
  if (e && e.parameter && e.parameter.action === 'config') {
    try { const c = config_(ss_()); c.ok = true; return out_(c); }
    catch (err) { return out_({ ok: false, error: String(err) }); }
  }
  return ContentService.createTextOutput('기우제반 플러스 기록 서버가 동작 중입니다.');
}

/* ---------- 앱이 보내는 기록 ---------- */
function doPost(e) {
  try {
    const d = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      const ss = ss_();
      if (d.kind === 'exam') return out_(exam_(ss, d));
      if (d.kind === 'report') return out_(report_(ss, d));
      if (d.kind === 'admin') return out_(admin_(ss, d));
      return out_({ ok: false, error: 'kind' });
    } finally { lock.releaseLock(); }
  } catch (err) {
    return out_({ ok: false, error: String(err) });
  }
}

function exam_(ss, d) {
  const name = String(d.name || '').replace(/\s+/g, ' ').trim().slice(0, 20);
  const score = Number(d.score), leaves = Math.max(0, Math.round(Number(d.leaves) || 0));
  const round = String(d.round || '').trim();
  const cfg = config_(ss);
  if (!name || !Number.isInteger(score) || score < 0 || score > 100 || !round || round !== cfg.round)
    return { ok: false, error: 'bad data' };
  const sh = tab_(ss, T_RES);
  if (!sh.getRange(1, 8).getValue()) sh.getRange(1, 8).setValue(HEAD[T_RES][7]).setFontWeight('bold');   // 예전 판 결과 탭
  const n = sh.getLastRow();
  const rows = n >= 2 ? sh.getRange(2, 1, n - 1, 8).getValues() : [];
  // 앱이 만든 제출 번호를 쓴다. 같은 번호가 이미 있으면 다시 보낸 것이므로 줄을 늘리지 않는다.
  const sid = /^[a-z0-9]{6,24}$/.test(String(d.sid || '')) ? String(d.sid) : newSid_();
  const dup = rows.find(r => String(r[7]) === sid);
  if (dup) return { ok: true, status: String(dup[4]), sid: sid };
  const again = rows.some(r => String(r[0]) === round && norm_(r[1]) === norm_(name));
  const st = [again ? '재응시' : '첫 응시'];
  if (!cfg.open) st.push('마감 후');
  const when = d.submitted ? new Date(d.submitted) : new Date();
  sh.appendRow([safe_(round), safe_(name), score, leaves, st.join(', '), isNaN(when) ? new Date() : when, safe_(String(d.browser || '').slice(0, 60)), sid]);
  return { ok: true, status: st.join(', '), sid: sid };
}
// 제출 번호: 영문 소문자·숫자 12자(시각 + 무작위)
function newSid_() { return (Date.now().toString(36) + Math.random().toString(36).slice(2, 8) + '000000').slice(0, 12); }

function report_(ss, d) {
  const id = String(d.id || '').slice(0, 60);
  if (!id) return { ok: false, error: 'bad data' };
  const sh = tab_(ss, T_REP);
  const n = sh.getLastRow();
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const rows = n >= 2 ? sh.getRange(2, 1, n - 1, 2).getValues() : [];
  const cnt = rows.filter(r => String(r[1]) === id && new Date(r[0]) >= today).length;
  if (cnt >= REPORT_PER_DAY) return { ok: true, skipped: true };
  sh.appendRow([new Date(), safe_(id), safe_(String(d.shown || '').slice(0, 200)), safe_(String(d.memo || '').slice(0, 100)), '']);
  return { ok: true };
}

/* ---------- 교사용 화면(#teacher) ---------- */
// action: status(현황만) | open(회차·시간을 적고 열림) | close(닫힘) | record(기록표용 탭 만들기)
function admin_(ss, d) {
  const pw = PropertiesService.getScriptProperties().getProperty('TEACHER_PW') || '';
  const cache = CacheService.getScriptCache();
  const fails = Number(cache.get('pwfail') || 0);
  if (!pw) return { ok: false, error: 'nopw' };
  if (fails >= PW_FAIL_LIMIT) return { ok: false, error: 'locked' };
  if (String(d.pw || '') !== pw) { cache.put('pwfail', String(fails + 1), 600); return { ok: false, error: 'pw' }; }
  const st = tab_(ss, T_SET);
  const a = String(d.action || 'status');
  if (a === 'open') {
    const r = String(d.round || '').replace(/\s+/g, ' ').trim().slice(0, 20);
    const m = Math.max(1, Math.min(180, Math.round(Number(d.minutes) || 30)));
    if (!r) return { ok: false, error: 'round' };
    st.getRange('B1:B3').setValues([[safe_(r)], ['열림'], [m]]);
  } else if (a === 'close') {
    st.getRange('B2').setValue('닫힘');
  } else if (a === 'record') {
    기록표용_만들기(String(d.round || '').trim() || undefined);
  }
  const cfg = config_(ss);
  cfg.state = String(st.getRange('B2').getValue()).trim();
  const round = String(d.round || '').trim() || cfg.round;
  const sh = tab_(ss, T_RES);
  const n = sh.getLastRow();
  const all = n >= 2 ? sh.getRange(2, 1, n - 1, 7).getValues() : [];
  const rounds = [];
  all.forEach(r => { const k = String(r[0]).replace(/^'/, ''); if (k && rounds.indexOf(k) < 0) rounds.push(k); });
  const rows = all.filter(r => String(r[0]).replace(/^'/, '') === round).map(r => ({
    name: String(r[1]).replace(/^'/, ''), score: r[2], leaves: r[3], status: String(r[4]),
    at: r[5] instanceof Date ? r[5].toISOString() : String(r[5])
  }));
  return { ok: true, cfg: cfg, round: round, rows: rows, rounds: rounds };
}

/* ---------- 기록표에 넣기 ---------- */
// 설정 탭의 회차(또는 인자로 준 회차)의 '첫 응시'만 골라 기록표용 탭에 이름 | 점수 로 쓴다.
function 기록표용_만들기(round) {
  const ss = ss_();
  round = String(round || config_(ss).round).trim();
  const sh = tab_(ss, T_RES);
  const n = sh.getLastRow();
  const rows = n >= 2 ? sh.getRange(2, 1, n - 1, 5).getValues() : [];
  const seen = {}, out = [];
  rows.forEach(r => {
    if (String(r[0]) !== round) return;
    const key = norm_(r[1]);
    if (seen[key]) return;                       // 첫 응시 점수만 인정
    seen[key] = true;
    out.push([r[1], r[2]]);
  });
  const rec = tab_(ss, T_REC);
  rec.clearContents();
  rec.getRange(1, 1, 1, 2).setValues([HEAD[T_REC]]).setFontWeight('bold');
  if (out.length) rec.getRange(2, 1, out.length, 2).setValues(out);
  rec.getRange(1, 4).setValue(round + ' 첫 응시 ' + out.length + '명');
  Logger.log(round + ' 첫 응시 ' + out.length + '명을 기록표용 탭에 썼습니다.');
  return out.length;
}
