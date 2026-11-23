// 앱 엔진 시험 (SPEC Testing Decisions 2·3): node quiz_plus/tools/test_engine.js
// docs/index.html 의 ENGINE-START~ENGINE-END 구간을 떼어 실행한다(앱과 같은 코드).
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const P = path.dirname(__dirname);
const html = fs.readFileSync(path.join(P, "docs", "index.html"), "utf8");
const code = html.split("/* ===== ENGINE-START")[1].split("/* ===== ENGINE-END")[0].replace(/^[^\n]*\n/, "");
const ctx = { CIRC: "①②③④⑤⑥", console, Math };
vm.createContext(ctx);
vm.runInContext(code + "\nthis.E={norm,FORMULAS,fillT,pickVals,makeInst,view,calcOk,shortOk,buildExam,scoreExam,tagKey,EXAM_PLAN,pointsOf};", ctx);
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
console.log("시험지 1,000번: 새 문항 수 분포", JSON.stringify(newCnt), "· 유형별 새 문항 누계", JSON.stringify(typeNew));
console.log(fail ? `실패 ${fail}건` : "모두 통과");
process.exit(fail ? 1 : 0);
