// 가짜 시트로 apps-script/기우제플러스.gs 시험(교사용 명령·시험 제출·기록표용). 실행: node tools/mock_gas.js
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
r = post({ kind: "admin", pw: "test-pw-0000", action: "close", round: "8회차" });
ok(r.ok && r.cfg.state === "닫힘" && r.rows.length === 2, "닫기·결과 2건");
ok(post({ kind: "exam", round: "8회차", name: "라마바", score: 70, leaves: 0, browser: "크롬" }).status.includes("마감 후"), "닫은 뒤 제출은 마감 후");
r = post({ kind: "admin", pw: "test-pw-0000", action: "record", round: "8회차" });
ok(r.ok && sheets["기록표용"].getLastRow() === 3, "기록표용 만들기(첫 응시 2명)");
for (let i = 0; i < 10; i++) post({ kind: "admin", pw: "1", action: "status" });
ok(post({ kind: "admin", pw: "test-pw-0000", action: "status" }).error === "locked", "10번 틀리면 잠금");
console.log(fails ? `실패 ${fails}건` : "Apps Script 가짜 시트 시험 모두 통과");
process.exit(fails ? 1 : 0);
