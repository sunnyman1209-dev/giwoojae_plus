// 가짜 시트로 apps-script/기우제플러스.gs 시험(교사용 명령·시험 제출·기록표용·인정 답안 제안). 실행: node tools/mock_gas.js
const fs = require("fs"), path = require("path"), vm = require("vm");
const src = fs.readFileSync(path.join(__dirname, "..", "apps-script", "기우제플러스.gs"), "utf8")
  .replace("const TEACHER_PW_INIT = '';", "const TEACHER_PW_INIT = 'test-pw-0000';");

function colRow(a1) { const m = /^([A-Z]+)(\d+)$/.exec(a1); return [m[1].charCodeAt(0) - 64, +m[2]]; }
class Sheet {
  constructor(name) { this.name = name; this.d = []; }
  cell(r, c) { return (this.d[r - 1] || [])[c - 1] ?? ""; }
  put(r, c, v) { while (this.d.length < r) this.d.push([]); this.d[r - 1][c - 1] = v; }
  getLastRow() { let n = 0; this.d.forEach((row, i) => { if (row.some(v => v !== "" && v != null)) n = i + 1; }); return n; }
  getRange(a, b, c, e) {
    let r0, c0, nr, nc;
    if (typeof a === "string") { const [p, q] = a.split(":"); const [ca, ra] = colRow(p); const [cb, rb] = q ? colRow(q) : [ca, ra]; r0 = ra; c0 = ca; nr = rb - ra + 1; nc = cb - ca + 1; }
    else { r0 = a; c0 = b; nr = c || 1; nc = e || 1; }
    const sh = this;
    const rg = {
      getValues: () => Array.from({ length: nr }, (_, i) => Array.from({ length: nc }, (_, j) => sh.cell(r0 + i, c0 + j))),
      getValue: () => sh.cell(r0, c0),
      setValues: v => { v.forEach((row, i) => row.forEach((x, j) => sh.put(r0 + i, c0 + j, x))); return rg; },
      setValue: v => { sh.put(r0, c0, v); return rg; },
      setFontWeight: () => rg, setDataValidation: () => rg
    };
    return rg;
  }
  appendRow(row) { this.d.push(row.slice()); }
  setFrozenRows() {} clearContents() { this.d = []; }
}
const sheets = {};
const ss = { getSheetByName: n => sheets[n] || null, insertSheet: n => (sheets[n] = new Sheet(n)), getSheets: () => Object.values(sheets),
  deleteSheet: s => delete sheets[s.name], getId: () => "SHEET1", getUrl: () => "https://example/sheet" };
const props = {}, cache = {}; let lockFree = true;
const ctx = {
  SpreadsheetApp: { openById: () => ss, getActive: () => ss, create: () => ss, flush: () => {},
    newDataValidation: () => ({ requireValueInList() { return this; }, build() { return {}; } }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] ?? null, setProperty: (k, v) => { props[k] = v; } }) },
  CacheService: { getScriptCache: () => ({ get: k => cache[k] ?? null, put: (k, v) => { cache[k] = v; }, remove: k => { delete cache[k]; } }) },
  LockService: { getScriptLock: () => ({ waitLock() {}, tryLock: () => lockFree, releaseLock() {} }) },
  ContentService: { createTextOutput: s => ({ s, setMimeType() { return this; } }), MimeType: { JSON: "json" } },
  Logger: { log: () => {} }, console, Date, JSON, Math, Number, String
};
vm.createContext(ctx); vm.runInContext(src, ctx);
const post = o => JSON.parse(ctx.doPost({ postData: { contents: JSON.stringify(o) } }).s);
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log("실패:", m); } };

ctx.설정하기();
ok(props.TEACHER_PW === "test-pw-0000", "비밀번호 저장");
ok(post({ kind: "admin", pw: "0000", action: "status" }).error === "pw", "틀린 비밀번호 거부");
let r = post({ kind: "admin", pw: "test-pw-0000", action: "status" });
ok(r.ok && r.cfg.state === "닫힘" && r.rows.length === 0, "현황(처음 닫힘)");
ok(post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "" }).error === "round", "회차 없이 열기 거부");
r = post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "8회차", minutes: 40 });
ok(r.ok && r.cfg.open && r.cfg.round === "8회차" && r.cfg.minutes === 40, "열기");
ok(JSON.parse(ctx.doGet({ parameter: { action: "config" } }).s).open === true, "학생 화면 설정 읽기(열림)");
ok(post({ kind: "exam", round: "8회차", name: "가나다", score: 80, leaves: 1, submitted: new Date().toISOString(), browser: "크롬" }).ok, "제출 1");
ok(post({ kind: "exam", round: "8회차", name: "가 나다", score: 90, leaves: 0, submitted: new Date().toISOString(), browser: "크롬" }).status === "재응시", "재응시 표시");
// 제출 번호(SPEC_1124 D): 응답으로 돌려주고 결과 탭 '제출 번호' 칸에 남긴다
const resTab = () => sheets["결과"], col = h => resTab().d[0].indexOf(h);
ok(col("제출 번호") >= 0, "결과 탭에 제출 번호 칸");
const subRow = sid => resTab().d.slice(1).filter(row => row[col("제출 번호")] === sid);
const s1 = post({ kind: "exam", round: "8회차", name: "사아자", score: 60, leaves: 0, sid: "k3x9a7qz2m", browser: "크롬" });
ok(s1.ok && s1.sid === "k3x9a7qz2m" && subRow("k3x9a7qz2m").length === 1, "앱이 만든 제출 번호를 그대로 돌려줌");
const s2 = post({ kind: "exam", round: "8회차", name: "사아자", score: 60, leaves: 0, sid: "k3x9a7qz2m", browser: "크롬" });
ok(s2.ok && s2.sid === "k3x9a7qz2m" && subRow("k3x9a7qz2m").length === 1 && s2.status === s1.status, "같은 제출 번호로 다시 보내면 줄을 늘리지 않음");
const s3 = post({ kind: "exam", round: "8회차", name: "차카타", score: 50, leaves: 0, browser: "크롬" });
const s4 = post({ kind: "exam", round: "8회차", name: "파하", score: 40, leaves: 0, sid: "=bad id!", browser: "크롬" });
ok(s3.ok && /^[a-z0-9]{6,24}$/.test(s3.sid) && s4.ok && /^[a-z0-9]{6,24}$/.test(s4.sid) && s3.sid !== s4.sid, "제출 번호가 없거나 잘못되면 시트가 새로 만듦");
ok(subRow(s3.sid).length === 1 && subRow(s4.sid).length === 1, "새로 만든 제출 번호도 결과 탭에 남음");
ok(post({ kind: "exam", round: "9회차", name: "가", score: 40, sid: "zzzzzz1" }).ok === false && subRow("zzzzzz1").length === 0, "잘못된 제출은 번호를 주지 않음");
r = post({ kind: "admin", pw: "test-pw-0000", action: "close", round: "8회차" });
ok(r.ok && r.cfg.state === "닫힘" && r.rows.length === 5, "닫기·결과 5건");
ok(post({ kind: "exam", round: "8회차", name: "라마바", score: 70, leaves: 0, browser: "크롬" }).status.includes("마감 후"), "닫은 뒤 제출은 마감 후");
r = post({ kind: "admin", pw: "test-pw-0000", action: "record", round: "8회차" });
ok(r.ok && sheets["기록표용"].getLastRow() === 6, "기록표용 만들기(첫 응시 5명)");
// 인정 답안 제안 (SPEC_1124 D): 문항 번호와 학생 답만 신고 탭에, 학번·이름은 남기지 않는다
r = post({ kind: "suggest", id: "g1|3", answer: "크레이터마모", shown: "주관식", name: "가나다" });
ok(r.ok, "인정 답안 제안 받기");
{ const rows = sheets["신고"].d.slice(1), last = rows[rows.length - 1];
  ok(last && last[1] === "g1|3" && String(last[3]).includes("인정 답안 제안") && String(last[3]).includes("크레이터마모"), "신고 탭에 인정 답안 제안 줄");
  ok(last && !last.join("|").includes("가나다"), "이름은 남기지 않음"); }
ok(post({ kind: "suggest", id: "g1|3", answer: "  " }).error === "bad data", "빈 답 제안 거부");
ok(post({ kind: "suggest", id: "", answer: "x" }).error === "bad data", "문항 번호 없는 제안 거부");
// 시험 점수 고치기 (SPEC_1124 D): 제출 때 남긴 문항별 채점(유형 글자 + o/x)으로 시트가 배점 기준 다시 계산
{
  post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "10회차", minutes: 40 });
  // 앱의 EXAM_PLAN 대로 40문항을 모두 맞힌 채점표는 시트 계산으로 100점이어야 한다(배점 일치)
  const html = fs.readFileSync(path.join(__dirname, "..", "docs", "index.html"), "utf8");
  const plan = JSON.parse(/const EXAM_PLAN=(\[\[.*?\]\]);/.exec(html)[1]);
  const code = { "진위형": "T", "연결형": "M", "4지선다": "C", "단답형": "S", "계산형": "N" };
  const all = plan.flatMap(([t, n]) => Array(n).fill(code[t]));
  const full = all.map(c => c + "o").join("");
  const f0 = post({ kind: "exam", round: "10회차", name: "만점", score: 100, sid: "full000001", marks: full });
  ok(f0.ok && subRow("full000001")[0][col("점수")] === 100, "모두 맞힌 채점표는 시트 계산 100점(앱 배점과 같음)");
  // 31~38 단답형(4점), 39~40 계산형(4점). 31·32·33·39번만 틀림 → 100 - 16 = 84
  const wrong = new Set([31, 32, 33, 39]);
  const marks = all.map((c, i) => c + (wrong.has(i + 1) ? "x" : "o")).join("");
  const e0 = post({ kind: "exam", round: "10회차", name: "고치기", score: 100, sid: "fixtest001", marks });
  const row = () => subRow("fixtest001")[0];
  ok(e0.ok && row()[col("점수")] === 84, "학생 기기 점수(100)를 믿지 않고 문항별 채점으로 84점");
  ok(col("원래 점수") >= 0 && col("맞음 처리 문항") >= 0, "결과 탭에 원래 점수·맞음 처리 문항 칸");
  let f = post({ kind: "fix", sid: "fixtest001", nums: [31, 33], score: 100 });
  ok(f.ok && f.score === 92 && row()[col("점수")] === 92 && row()[col("원래 점수")] === 84 && row()[col("맞음 처리 문항")] === "31, 33", "고치기: 92점, 원래 84점, 31, 33");
  f = post({ kind: "fix", sid: "fixtest001", nums: [33, 31, 31] });
  ok(f.ok && row()[col("점수")] === 92 && subRow("fixtest001").length === 1, "같은 요청 두 번(순서·중복 달라도) 같은 결과");
  f = post({ kind: "fix", sid: "fixtest001", nums: [31] });
  ok(f.ok && row()[col("점수")] === 88 && row()[col("맞음 처리 문항")] === "31", "하나 되돌리기: 88점");
  ok(post({ kind: "fix", sid: "없는번호", nums: [31] }).error === "sid", "없는 제출 번호 거부");
  ok(post({ kind: "fix", sid: "fixtest002", nums: [31] }).error === "sid", "결과 탭에 없는 제출 번호 거부");
  ok(post({ kind: "fix", sid: "fixtest001", nums: [39] }).error === "num" && row()[col("점수")] === 88, "계산형 번호 거부, 점수 그대로");
  ok(post({ kind: "fix", sid: "fixtest001", nums: [34] }).error === "num", "이미 맞힌 문항 번호 거부");
  ok(post({ kind: "fix", sid: "fixtest001", nums: [1] }).error === "num", "다른 유형 번호 거부");
  ok(post({ kind: "fix", sid: "fixtest001", nums: [0] }).error === "num" && post({ kind: "fix", sid: "fixtest001", nums: [41] }).error === "num"
    && post({ kind: "fix", sid: "fixtest001", nums: "31" }).error === "num" && post({ kind: "fix", sid: "fixtest001", nums: [31.5] }).error === "num", "범위 밖·잘못된 문항 번호 거부");
  ok(post({ kind: "fix", sid: "k3x9a7qz2m", nums: [31] }).error === "old", "문항별 채점이 없는 예전 제출은 고칠 수 없음");
  post({ kind: "fix", sid: "fixtest001", nums: [31, 32, 33] });
  r = post({ kind: "admin", pw: "test-pw-0000", action: "record", round: "10회차" });
  ok(sheets["기록표용"].d.slice(1).some(x => x[0] === "고치기" && x[1] === 96), "기록표용 탭에 고친 점수(96)");
  const ar = r.rows.find(x => x.name === "고치기");
  ok(ar && ar.score === 96 && ar.orig === 84 && ar.self === "31, 32, 33", "교사 화면 결과 목록(CSV 원본)에 고친 점수·원래 점수·고친 문항");
  f = post({ kind: "fix", sid: "fixtest001", nums: [] });
  ok(f.ok && row()[col("점수")] === 84 && row()[col("원래 점수")] === "" && row()[col("맞음 처리 문항")] === "", "모두 되돌리면 원래 점수로, 옆 칸 비움");
  ok(post({ kind: "admin", pw: "test-pw-0000", action: "status", round: "10회차" }).rows.find(x => x.name === "고치기").orig === "", "되돌린 뒤 교사 화면 원래 점수 비움");
  ok(post({ kind: "exam", round: "10회차", name: "이상", score: 50, sid: "badmarks01", marks: "Zo=x" }).error === "bad data", "잘못된 채점표 거부");
}
// ---------- 작업표 13 검토 반영 ----------
{
  const html = fs.readFileSync(path.join(__dirname, "..", "docs", "index.html"), "utf8");
  const plan = JSON.parse(/const EXAM_PLAN=(\[\[.*?\]\]);/.exec(html)[1]);
  const code = { "진위형": "T", "연결형": "M", "4지선다": "C", "단답형": "S", "계산형": "N" };
  const all = plan.flatMap(([t, n]) => Array(n).fill(code[t]));
  const half = all.map((c, i) => c + (i >= 30 && i < 34 ? "x" : "o")).join("");   // 31~34 단답형 틀림 → 84점
  // 시험 도중 교사가 다음 회차를 열어도, 그 전 회차로 시작한 제출은 '마감 후'로 받는다
  post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "11회차", minutes: 40 });
  const a1 = post({ kind: "exam", round: "11회차", name: "먼저낸", sid: "rnd11aaaa1", marks: half });
  post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "12회차", minutes: 40 });
  const a2 = post({ kind: "exam", round: "11회차", name: "늦게낸", sid: "rnd11bbbb1", marks: half });
  ok(a1.ok && a2.ok && a2.status.includes("마감 후") && subRow("rnd11bbbb1").length === 1, "다음 회차를 연 뒤에도 이전 회차 제출을 '마감 후'로 받음");
  // 기록은 됐는데 응답을 못 받은 제출을 회차가 바뀐 뒤 다시 보내도 성공(줄은 늘지 않음)
  const a3 = post({ kind: "exam", round: "11회차", name: "먼저낸", sid: "rnd11aaaa1", marks: half });
  ok(a3.ok && a3.sid === "rnd11aaaa1" && subRow("rnd11aaaa1").length === 1, "회차가 바뀐 뒤 같은 제출 번호로 다시 보내기 성공");
  ok(post({ kind: "exam", round: "99회차", name: "가", sid: "rnd99aaaa1", marks: half }).error === "bad data", "열린 적 없는 회차 제출은 거부");
  // 모두 맞혀도 100점을 넘는 채점표는 거부(맞음 처리로 100점 초과 방지)
  ok(post({ kind: "exam", round: "12회차", name: "넘침", sid: "over000001", marks: half + "Sx" }).error === "bad data", "100점을 넘을 수 있는 채점표 거부");
  // 점수 고치기 순번: 늦게 도착한 예전 요청은 새 상태를 덮어쓰지 않는다
  const rowA = () => subRow("rnd11aaaa1")[0];
  ok(post({ kind: "fix", sid: "rnd11aaaa1", nums: [31, 32], seq: 2000 }).score === 92, "고치기(순번 2000) 92점");
  const st = post({ kind: "fix", sid: "rnd11aaaa1", nums: [31, 32, 33, 34], seq: 1000 });
  ok(st.ok && st.stale && rowA()[col("점수")] === 92 && rowA()[col("맞음 처리 문항")] === "31, 32", "늦게 온 예전 요청(순번 1000)은 무시");
  ok(post({ kind: "fix", sid: "rnd11aaaa1", nums: [], seq: 3000 }).score === 84 && rowA()[col("원래 점수")] === "", "새 요청(순번 3000) 되돌리기는 반영");
  Object.keys(cache).forEach(k => { if (k !== "pwfail") delete cache[k]; });   // 캐시가 비어도
  ok(post({ kind: "fix", sid: "rnd11aaaa1", nums: [31], seq: 2500 }).stale && rowA()[col("점수")] === 84 && rowA()[col("고침 순번")] === 3000, "순번은 결과 탭에 남아 캐시가 비어도 예전 요청 무시");
  // 설정 탭 B1을 시트에서 직접 바꿔도(교사 화면을 거치지 않아도) 이전 회차 제출을 받는다
  sheets["설정"].put(1, 2, "14회차"); ctx.doGet({ parameter: { action: "config" } });
  sheets["설정"].put(1, 2, "15회차"); ctx.doGet({ parameter: { action: "config" } });
  ok(post({ kind: "exam", round: "14회차", name: "직접", sid: "rnd14aaaa1", marks: half }).ok, "B1 직접 변경 뒤 이전 회차 제출 받음");
  // 기록표용은 상태가 '첫 응시'인 줄만(결과 탭을 정렬해 재응시가 위로 와도)
  post({ kind: "exam", round: "15회차", name: "정렬", sid: "sort000001", marks: half });
  post({ kind: "exam", round: "15회차", name: "정렬", sid: "sort000002", marks: all.map(c => c + "o").join("") });
  { const d = resTab().d, i1 = d.findIndex(r => r[col("제출 번호")] === "sort000001"), i2 = d.findIndex(r => r[col("제출 번호")] === "sort000002");
    [d[i1], d[i2]] = [d[i2], d[i1]]; }
  post({ kind: "admin", pw: "test-pw-0000", action: "record", round: "15회차" });
  ok(sheets["기록표용"].d.slice(1).some(x => x[0] === "정렬" && x[1] === 84), "기록표용은 정렬과 상관없이 첫 응시 점수(84)");
  // 동시 제출로 잠금을 못 얻으면 'busy'로 돌려준다(앱이 잠시 뒤 다시 보냄)
  lockFree = false;
  ok(post({ kind: "exam", round: "12회차", name: "대기", sid: "busy000001", marks: half }).error === "busy" && subRow("busy000001").length === 0, "잠금 대기 초과는 busy");
  lockFree = true;
  // 기록표용 탭에 다시 쓰는 이름도 수식으로 읽히지 않게
  post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "13회차", minutes: 40 });
  post({ kind: "exam", round: "13회차", name: "=1+1", sid: "formula001", marks: half });
  subRow("formula001")[0][col("이름")] = "=1+1";   // 실제 시트는 읽을 때 앞의 ' 를 떼고 돌려준다
  post({ kind: "admin", pw: "test-pw-0000", action: "record", round: "13회차" });
  ok(sheets["기록표용"].d[1][0] === "'=1+1", "기록표용 이름 수식 방지");
  { const save = sheets["설정"].cell(1, 2); sheets["설정"].put(1, 2, "연습");
    ok(JSON.parse(ctx.doGet({ parameter: { action: "config" } }).s).open === false, "설정 탭에 '연습'을 직접 적어도 열리지 않음");
    sheets["설정"].put(1, 2, save); ctx.doGet({ parameter: { action: "config" } }); }
  ok(post({ kind: "admin", pw: "test-pw-0000", action: "open", round: "연습", minutes: 40 }).error === "demo", "'연습'은 회차 이름으로 열 수 없음");
  // 비밀번호: 맞게 들어오면 틀린 횟수를 지운다
  for (let i = 0; i < 9; i++) post({ kind: "admin", pw: "1", action: "status" });
  ok(post({ kind: "admin", pw: "test-pw-0000", action: "status" }).ok, "9번 틀린 뒤 맞으면 들어감");
  ok(post({ kind: "admin", pw: "1", action: "status" }).error === "pw" && post({ kind: "admin", pw: "test-pw-0000", action: "status" }).ok, "맞게 들어온 뒤에는 한 번 틀려도 잠기지 않음");
}
for (let i = 0; i < 10; i++) post({ kind: "admin", pw: "1", action: "status" });
ok(post({ kind: "admin", pw: "test-pw-0000", action: "status" }).error === "locked", "10번 틀리면 잠금");
console.log(fails ? `실패 ${fails}건` : "Apps Script 가짜 시트 시험 모두 통과");
process.exit(fails ? 1 : 0);
