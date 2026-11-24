// 앱 엔진 시험 (SPEC Testing Decisions 2·3): node quiz_plus/tools/test_engine.js
// docs/index.html 의 ENGINE-START~ENGINE-END 구간을 떼어 실행한다(앱과 같은 코드).
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const P = path.dirname(__dirname);
const html = fs.readFileSync(path.join(P, "docs", "index.html"), "utf8");
const code = html.split("/* ===== ENGINE-START")[1].split("/* ===== ENGINE-END")[0].replace(/^[^\n]*\n/, "");
const ctx = { CIRC: "①②③④⑤⑥", console, Math };
vm.createContext(ctx);
vm.runInContext(code + "\nthis.E={norm,FORMULAS,fillT,pickVals,makeInst,view,calcOk,shortOk,buildExam,scoreExam,examResult,tagKey,EXAM_PLAN,pointsOf,selfMarkable,selfMark,examMarks};", ctx);
const E = ctx.E;
const DB = JSON.parse(fs.readFileSync(path.join(P, "docs", "data", "questions.json"), "utf8"));
const BY = {}; DB.questions.forEach(q => BY[q.id] = q);
let fail = 0;
const bad = (...a) => { fail++; console.log("실패:", ...a); };

// ---------- 계산형 ----------
function combos(vars) {
  let out = [{}];
  for (const key in vars) {
    const next = [];
    for (const base of out) for (const o of vars[key]) {
      const v = Object.assign({}, base);
      if (key.includes(",")) key.split(",").forEach((k, i) => v[k] = o[i]); else v[key] = o;
      next.push(v);
    }
    out = next;
  }
  return out;
}
let nCalc = 0;
for (const q of DB.questions.filter(q => q.calc)) {
  nCalc++;
  const c = q.calc;
  if (!E.FORMULAS[c.f]) { bad(q.id, "공식 없음", c.f); continue; }
  const all = combos(c.vars);
  const inRange = all.filter(v => { const a = E.FORMULAS[c.f](v); return a >= c.range[0] && a <= c.range[1]; });
  if (inRange.length / all.length < 0.5) bad(q.id, `범위 안 조합 ${inRange.length}/${all.length}`);
  // 원래 문항의 정답이 어떤 조합으로든 나와야 한다(공식이 원래 문항과 같다는 확인)
  if (q.value != null && !all.some(v => Math.abs(E.FORMULAS[c.f](v) - q.value) <= Math.max(Math.abs(q.value) * 0.01, 0.5 * Math.pow(10, -c.round))))
    bad(q.id, "원래 정답", q.value, "을 만드는 조합이 없음");
  for (let k = 0; k < 30; k++) {
    const it = E.makeInst(q), v = E.view(q, it);
    const left = [v.stem, ...(v.steps || [])].join(" ").match(/\{[^}]*\}/g);
    if (left && !/\^\{|_\{/.test(v.stem)) bad(q.id, "안 바뀐 자리", left);
    if (!E.calcOk(String(v.value), v.value, v.round)) bad(q.id, "자기 정답 채점 실패");
    if (!E.calcOk(v.ansText, v.value, v.round)) bad(q.id, "화면 정답(반올림)이 틀림으로 채점됨", v.ansText, v.value);
    if (v.value < c.range[0] || v.value > c.range[1]) bad(q.id, "범위 밖 답", v.value);
  }
}
console.log(`계산형 숫자 바꾸기 ${nCalc}문항 검사`);

// ---------- 보기 섞기·해설 번호 ----------
for (const q of DB.questions.filter(q => q.t === "4지선다" && q.choices)) {
  for (let k = 0; k < 5; k++) {
    const it = E.makeInst(q), v = E.view(q, it);
    if (v.choices[v.ansPos] !== q.choices[q.ans]) bad(q.id, "섞은 뒤 정답 위치 틀림");
    if (q.noShuffle && it.o.some((x, i) => x !== i)) bad(q.id, "섞지 않음인데 섞임");
  }
}
const sample = BY["g1|6"], vv = E.view(sample, { o: [3, 2, 1, 0] });
if (!vv.ansText.startsWith("①")) bad("g1|6", "정답 번호 다시 붙이기", vv.ansText);
if (vv.remap("④ 바깥지름") !== "① 바깥지름") bad("remap", vv.remap("④ 바깥지름"));

// ---------- 주관식 채점 ----------
if (!E.shortOk("크레이터 마모", ["크레이터마모"])) bad("띄어쓰기 무시");
if (!E.shortOk("g71", ["G71"])) bad("대소문자 무시");
if (E.shortOk("", ["G71"])) bad("빈 답이 맞음");
if (!E.calcOk("0.27", 0.26667, 2)) bad("반올림 답 0.27 인정");
if (E.calcOk("0.3", 0.26667, 2)) bad("0.3 은 틀려야 함");

// ---------- 스스로 맞음 처리 (학습, SPEC_1124 D) ----------
const qS = { id: "s1", t: "단답형" }, qD = { id: "s2", t: "서술형" }, qC = { id: "s3", t: "계산형" },
  qM = { id: "s4", t: "4지선다", open: ["G71"] }, qO = { id: "s5", t: "진위형" };
if (!E.selfMarkable(qS, { g: "x", mine: "크레이터" })) bad("단답형 오답은 대상");
if (!E.selfMarkable(qD, { g: "m", mine: "공구 마모" })) bad("서술형 일부 맞음은 대상");
if (!E.selfMarkable(qM, { g: "x", mine: "g70", open: true })) bad("주관식 모드 4지선다 오답은 대상");
if (E.selfMarkable(qM, { g: "x", mine: "g70", open: false })) bad("보기로 푼 4지선다는 대상 아님");
if (E.selfMarkable(qC, { g: "x", mine: "12.5" })) bad("계산형은 대상 아님");
if (E.selfMarkable(qO, { g: "x", mine: "O" })) bad("진위형은 대상 아님");
if (E.selfMarkable(qS, { g: "o", mine: "G71" })) bad("이미 맞힌 문항은 대상 아님");
if (E.selfMarkable(qD, { g: "x", mine: "" })) bad("답을 쓰지 않은 서술형은 대상 아님");
{
  const st = { res: { s1: "x", s9: "o" }, retry: [{ id: "s1", due: 30 }], self: {}, count: 20 };
  E.selfMark(st, "s1", true);
  if (st.res.s1 !== "o" || !st.self.s1 || st.retry.some(r => r.id === "s1")) bad("맞음 표시 후 맞힘·오답 노트 제외", JSON.stringify(st));
  E.selfMark(st, "s1", false);
  if (st.res.s1 !== "x" || st.self.s1 || !st.retry.some(r => r.id === "s1")) bad("되돌린 뒤 원래 오답으로", JSON.stringify(st));
  const st2 = { res: { s2: "m" }, retry: [] };
  E.selfMark(st2, "s2", true); E.selfMark(st2, "s2", true); E.selfMark(st2, "s2", false);
  if (st2.res.s2 !== "m") bad("두 번 눌러도 원래 결과(일부 맞음)로 되돌아감", st2.res.s2);
  E.selfMark(st2, "s2", false);
  if (st2.res.s2 !== "m") bad("표시 없는데 되돌리기는 아무 일 없음");
}

// ---------- CBT 시험지 1,000번 ----------
const want = Object.fromEntries(E.EXAM_PLAN.map(([t, n]) => [t, n]));
const newCnt = {}, typeNew = {};
for (let k = 0; k < 1000; k++) {
  const items = E.buildExam(DB.questions);
  if (items.length !== 40) { bad("시험지 문항 수", items.length); break; }
  const qs = items.map(it => BY[it.id]);
  // 유형 순서와 개수
  const order = E.EXAM_PLAN.flatMap(([t, n]) => Array(n).fill(t));
  qs.forEach((q, i) => { if (q.t !== order[i]) bad("유형 순서", i + 1, q.t); });
  if (new Set(items.map(i => i.id)).size !== 40) bad("같은 문항 두 번");
  const tags = qs.map(E.tagKey);
  if (new Set(tags).size !== 40) bad("꼬리표 중복", tags.filter((t, i) => tags.indexOf(t) !== i));
  const ids = new Set(items.map(i => i.id));
  qs.forEach(q => { if (q.from && ids.has(q.from)) bad("원본과 변형 동시 출제", q.id); });
  if (qs.some(q => !q.cbt || q.t === "서술형")) bad("CBT 대상 아닌 문항");
  const n = qs.filter(q => q.src === "new").length;
  newCnt[n] = (newCnt[n] || 0) + 1;
  qs.forEach(q => { if (q.src === "new") typeNew[q.t] = (typeNew[q.t] || 0) + 1; });
  // 채점: 모두 맞힘 100, 모두 비움 0
  if (k < 200) {
    const right = items.map(it => { const q = BY[it.id], v = E.view(q, it);
      return q.t === "진위형" ? q.ans : q.t === "4지선다" ? v.ansPos : q.t === "연결형" ? q.ans.slice() : q.t === "단답형" ? q.accept[0].toUpperCase().replace(/ /g, "  ") : v.ansText; });
    const s = E.scoreExam(BY, items, right).score;
    if (s !== 100) bad("모두 맞혔는데", s, items.filter((it, i) => !E.scoreExam(BY, [it], [right[i]]).ok[0]).map(i => i.id));
    if (E.scoreExam(BY, items, []).score !== 0) bad("모두 비웠는데 0점이 아님");
    const oneWrong = right.slice(); const mi = qs.findIndex(q => q.t === "연결형"); const a = oneWrong[mi].slice(); [a[0], a[1]] = [a[1], a[0]]; oneWrong[mi] = a;
    if (E.scoreExam(BY, items, oneWrong).score !== 98) bad("연결형 한 짝 틀림은 0점이어야 함");
  }
}
// ---------- 결과 다시 보기(SPEC_1124 D): 기기에 남긴 시험지·답으로 같은 결과를 다시 만든다 ----------
for (let k = 0; k < 200; k++) {
  const items = E.buildExam(DB.questions);
  const a = {};
  items.forEach((it, i) => { const q = BY[it.id], v = E.view(q, it), r = Math.random();
    if (r < 0.2) return;   // 비움
    a[i] = r < 0.6 ? (q.t === "진위형" ? q.ans : q.t === "4지선다" ? v.ansPos : q.t === "연결형" ? q.ans.slice() : q.t === "단답형" ? q.accept[0] : v.ansText)
      : (q.t === "진위형" ? (q.ans === "O" ? "X" : "O") : q.t === "4지선다" ? (v.ansPos + 1) % v.choices.length : q.t === "연결형" ? q.ans.map(() => 0) : "엉뚱한 답"); });
  const rec = { items, a };
  const first = E.examResult(BY, rec);
  if (first.score !== E.scoreExam(BY, items, items.map((_, i) => a[i])).score) bad("제출 점수와 결과 점수가 다름");
  const again = E.examResult(BY, JSON.parse(JSON.stringify(rec)));   // 기기에 저장했다가 다시 읽은 기록
  if (again.score !== first.score || again.ok.join() !== first.ok.join()) bad("다시 연 결과가 제출 때와 다름", first.score, again.score);
  if (first.rows.some((x, i) => x.pts !== (x.ok ? E.pointsOf(BY[items[i].id].t) : 0))) bad("문항별 얻은 점수");
  const back = JSON.parse(JSON.stringify(rec));
  if (items.some((it, i) => { const q = BY[it.id]; return E.view(q, it).ansText !== E.view(q, back.items[i]).ansText; })) bad("다시 연 시험지의 정답 표시가 다름");
}
// ---------- 시험 '맞음으로 표시'(SPEC_1124 D): 화면 점수 = 시트가 문항 채점으로 다시 계산한 점수 ----------
{
  const PTS = { T: 2, M: 2, C: 2, S: 4, N: 4, D: 4 };   // 시트 스크립트 배점(apps-script)
  const sheetScore = (m, nums) => { let s = 0; for (let i = 0; i < m.length / 2; i++) if (m[2 * i + 1] === "o" || nums.includes(i + 1)) s += PTS[m[2 * i]]; return s; };
  let tried = 0;
  for (let k = 0; k < 300; k++) {
    const items = E.buildExam(DB.questions), a = {};
    items.forEach((it, i) => { const q = BY[it.id], v = E.view(q, it);
      a[i] = Math.random() < 0.5 ? (q.t === "진위형" ? q.ans : q.t === "4지선다" ? v.ansPos : q.t === "연결형" ? q.ans.slice() : q.t === "단답형" ? q.accept[0] : v.ansText)
        : (q.t === "진위형" ? (q.ans === "O" ? "X" : "O") : q.t === "4지선다" ? (v.ansPos + 1) % v.choices.length : q.t === "연결형" ? q.ans.map(() => 0) : "뜻은 같은 답"); });
    const rec = { items, a }, base = E.examResult(BY, rec), m = E.examMarks(BY, rec);
    if (m.length !== 80 || sheetScore(m, []) !== base.score) bad("문항 채점으로 시트가 계산한 점수가 화면 점수와 다름", m, base.score);
    const can = base.rows.map((x, i) => x.selfable ? i : -1).filter(i => i >= 0);
    if (can.some(i => BY[items[i].id].t !== "단답형") || base.rows.some((x, i) => !x.ok && BY[items[i].id].t === "단답형" && !x.selfable)) bad("시험 대상 문항: 틀린 단답형만");
    if (!can.length) continue;
    tried++;
    const pick = can.filter(() => Math.random() < 0.6), calcI = items.findIndex((it, i) => BY[it.id].t === "계산형" && !base.ok[i]);
    rec.self = pick.concat(calcI >= 0 ? [calcI] : []);   // 계산형 번호가 섞여 와도 무시
    const r2 = E.examResult(BY, rec);
    if (r2.score !== sheetScore(m, pick.map(i => i + 1))) bad("맞음 표시 뒤 화면 점수가 시트 점수와 다름", r2.score);
    if (r2.score !== base.score + 4 * pick.length) bad("단답형 하나에 4점씩 늘어야 함", base.score, r2.score, pick.length);
    if (pick.some(i => !r2.rows[i].self || !r2.rows[i].ok || r2.rows[i].pts !== 4)) bad("맞음 표시한 문항 표시·점수");
    if (calcI >= 0 && (r2.rows[calcI].ok || r2.rows[calcI].self)) bad("계산형은 맞음 처리 안 됨");
    if (E.examMarks(BY, rec) !== m) bad("맞음 표시가 원래 채점(문항 채점)을 바꾸면 안 됨");
    rec.self = [];
    if (E.examResult(BY, rec).score !== base.score) bad("되돌리면 원래 점수");
  }
  if (tried < 100) bad("맞음 표시 시험 표본 부족", tried);
}
// ---------- 결과 다시 보기는 제출 때 시트에 보낸 채점(marks)을 따른다(작업표 13) ----------
// 맞음 표시한 답을 다음 배포에서 인정 답안에 넣거나 문항이 없어져도, 화면 점수·맞음 표시가 시트와 어긋나지 않아야 한다
{
  let done = 0;
  for (let k = 0; k < 60 && done < 20; k++) {
    const items = E.buildExam(DB.questions), a = {};
    items.forEach((it, i) => { const q = BY[it.id], v = E.view(q, it);
      a[i] = q.t === "단답형" ? "새로 인정될 답" : q.t === "진위형" ? q.ans : q.t === "4지선다" ? v.ansPos : q.t === "연결형" ? q.ans.slice() : v.ansText; });
    const rec = { items, a }; rec.marks = E.examMarks(BY, rec);
    const i = items.findIndex(it => BY[it.id].t === "단답형"); if (i < 0) continue;
    rec.self = [i];
    const before = E.examResult(BY, rec);
    if (before.score !== 100 - 4 * 8 + 4) bad("맞음 표시 하나 반영 점수", before.score);
    const q = BY[items[i].id], BY2 = Object.assign({}, BY, { [q.id]: Object.assign({}, q, { accept: (q.accept || []).concat(["새로 인정될 답"]) }) });
    const after = E.examResult(BY2, rec);
    if (after.score !== before.score || !after.rows[i].self || !after.rows[i].selfable || after.rows[i].graded) bad("인정 답안이 바뀐 뒤 다시 연 결과가 제출 때와 다름", q.id);
    if (!E.examResult(BY2, Object.assign({}, rec, { marks: null })).rows[i].graded) bad("marks 없이는 지금 데이터로 다시 채점");
    if (E.examMarks(BY2, rec) === rec.marks) bad("examMarks 는 저장된 채점이 아니라 지금 데이터로 채점해야 함");
    const old = E.examResult(BY2, { items, a, self: [i], payload: { marks: rec.marks } });
    if (old.score !== before.score) bad("예전 기록(payload.marks)도 제출 때 채점을 따름");
    const BY3 = Object.assign({}, BY); delete BY3[items[0].id];
    if (E.examResult(BY3, rec).score !== before.score) bad("없어진 문항도 제출 때 점수 유지");
    const BY4 = Object.assign({}, BY); delete BY4[items[i].id];   // 맞음 표시한 단답형 문항이 없어져도
    const r4 = E.examResult(BY4, rec);
    if (r4.score !== before.score || !r4.rows[i].self || !r4.rows[i].selfable) bad("없어진 단답형의 맞음 표시·되돌리기 유지", r4.score);
    done++;
  }
  if (done < 10) bad("marks 시험 표본 부족", done);
}
if (!E.calcOk("−10", -10, 0)) bad("유니코드 마이너스(−) 입력 인정");
if (E.examResult(BY, { items: [{ id: "없는 문항" }], a: { 0: "x" } }).score !== 0) bad("사라진 문항은 0점");
if (E.examResult(BY, { items: [{ id: "g1|6", o: [0, 1, 2, 3] }], a: {} }).rows[0].mine !== null) bad("비운 답은 null");

console.log("시험지 1,000번: 새 문항 수 분포", JSON.stringify(newCnt), "· 유형별 새 문항 누계", JSON.stringify(typeNew));
console.log(fail ? `실패 ${fail}건` : "모두 통과");
process.exit(fail ? 1 : 0);
