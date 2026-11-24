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
const props = {}, cache = {};
const ctx = {
  SpreadsheetApp: { openById: () => ss, getActive: () => ss, create: () => ss,
    newDataValidation: () => ({ requireValueInList() { return this; }, build() { return {}; } }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] ?? null, setProperty: (k, v) => { props[k] = v; } }) },
  CacheService: { getScriptCache: () => ({ get: k => cache[k] ?? null, put: (k, v) => { cache[k] = v; } }) },
  LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
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
for (let i = 0; i < 10; i++) post({ kind: "admin", pw: "1", action: "status" });
ok(post({ kind: "admin", pw: "test-pw-0000", action: "status" }).error === "locked", "10번 틀리면 잠금");
console.log(fails ? `실패 ${fails}건` : "Apps Script 가짜 시트 시험 모두 통과");
process.exit(fails ? 1 : 0);
