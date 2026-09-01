#!/usr/bin/env node
/*
 * 자동 화이트리스트 재생성 스크립트 (오프라인 배치)
 *
 * 목적: 부분문자열 매칭 오탐(예: '시발' 등록 → '시발점' 차단)을 줄이기 위해,
 *       국어사전 명사 중 "블랙리스트 표준형(canon, 5자모 이상)을 부분문자열로 포함하되
 *       그 자체가 슬러가 아닌" 정상어만 뽑아 자동 화이트리스트로 생성한다.
 *
 * 데이터 출처(전부 공개):
 *   - 블랙리스트: lisuugi/korean-profanity-filter (Apache-2.0) + hlog2e/bad_word_list
 *     → index.html 런타임과 동일한 목록/병합 규칙
 *   - 정상어 명사: pd-korean-noun-list-for-wordles (Public Domain, 표준국어대사전 표제어)
 *
 * 정규화 로직: index.html의 normalize()를 그대로 추출해 사용(런타임과 100% 동일 의미).
 *
 * 실행: node scripts/gen_whitelist.mjs   (Node 18+ 필요, 네트워크 접속 필요)
 * 결과: whitelist_auto.json 갱신
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// ── 1) index.html에서 normalize() 블록 추출 ──
const HTML = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const script = HTML.split("<script>")[1].split("</script>")[0];
const nb = script.slice(script.indexOf("const CHO="), script.indexOf("/* ── 블랙리스트"));
const { normalize } = new Function(nb + "\nreturn {normalize};")();

// ── 2) 블랙리스트 로드(런타임 loadDicts와 동일) ──
const LIS = "https://raw.githubusercontent.com/lisuugi/korean-profanity-filter/master/src/main/resources/dictionary";
const LIS_FILES = [
  "profanity/profanity.level-1.exact", "profanity/profanity.level-2.common",
  "sexuality/sexuality.level-1.exact", "sexuality/sexuality.level-2.common",
  "harmful/harmful.level-1.exact", "harmful/harmful.level-2.common",
];
const parseWords = (t) => t.split(/\r?\n/).map((s) => s.trim()).filter((s) => s && !s.startsWith("#"));
async function loadBlacklist() {
  const bag = [];
  for (const f of LIS_FILES) {
    const r = await fetch(`${LIS}/${f}.txt`);
    if (r.ok) for (const w of parseWords(await r.text())) bag.push(w);
  }
  const r = await fetch("https://raw.githubusercontent.com/hlog2e/bad_word_list/master/word_list.json");
  const j = await r.json();
  for (const w of Array.isArray(j) ? j : j.words || []) bag.push(w);
  const seen = new Set(), bl = [];
  for (const w of bag) if (w && !seen.has(w)) { seen.add(w); bl.push(w); }
  return bl;
}

// ── 3) 정상어 명사 로드 ──
async function loadNouns() {
  const r = await fetch("https://cdn.jsdelivr.net/npm/pd-korean-noun-list-for-wordles/src/AllNouns.js");
  const t = await r.text();
  return [...t.matchAll(/'([가-힣]+)'/g)].map((m) => m[1]);
}

// ── 4) Aho-Corasick (canon 다중 패턴 동시 스캔) ──
function buildAC(patterns) {
  const next = [{}], fail = [0], out = [[]];
  for (const p of patterns) {
    let s = 0;
    for (const ch of p) {
      if (next[s][ch] === undefined) { next.push({}); fail.push(0); out.push([]); next[s][ch] = next.length - 1; }
      s = next[s][ch];
    }
    out[s].push(1);
  }
  const q = [];
  for (const ch in next[0]) { fail[next[0][ch]] = 0; q.push(next[0][ch]); }
  while (q.length) {
    const r = q.shift();
    for (const ch in next[r]) {
      const u = next[r][ch]; q.push(u);
      let f = fail[r];
      while (f && next[f][ch] === undefined) f = fail[f];
      fail[u] = next[f][ch] !== undefined && next[f][ch] !== u ? next[f][ch] : 0;
      out[u] = out[u].concat(out[fail[u]]);
    }
  }
  const has = (text) => {
    let s = 0;
    for (const ch of text) {
      while (s && next[s][ch] === undefined) s = fail[s];
      s = next[s][ch] !== undefined ? next[s][ch] : 0;
      if (out[s].length) return true;
    }
    return false;
  };
  return { has };
}

async function main() {
  const BL = await loadBlacklist();
  const BL_SET = new Set(BL);
  const CANON_MIN = 4;   // index.html의 CANON_MIN과 동일하게 유지
  const canonSet = new Set();
  for (const w of BL) { const c = normalize(w); if (c.length >= CANON_MIN) canonSet.add(c); }
  const ac = buildAC([...canonSet]);
  const nouns = await loadNouns();

  const auto = [];
  for (const w of nouns) {
    if (BL_SET.has(w)) continue;
    const c = normalize(w);
    if (c.length < CANON_MIN) continue;  // 부분매칭 최소 길이 미만은 대상 아님
    if (canonSet.has(c)) continue;       // 그 자체가 슬러 표준형 → 계속 차단(예: 맨 '시발')
    if (ac.has(c)) auto.push(w);
  }
  const words = [...new Set(auto)].sort((a, b) => a.localeCompare(b, "ko"));

  const out = {
    _comment: `AUTO-GENERATED. 국어사전 명사(pd-korean-noun-list-for-wordles, PD) ∩ 블랙리스트(lisuugi+hlog2e) canon(len>=${CANON_MIN}). 재생성: node scripts/gen_whitelist.mjs`,
    generatedAt: new Date().toISOString().slice(0, 10),
    canonMin: CANON_MIN,
    blacklistCount: BL.length,
    count: words.length,
    words,
  };
  fs.writeFileSync(path.join(ROOT, "whitelist_auto.json"), JSON.stringify(out));
  console.log(`블랙리스트 ${BL.length} · canon(len>=5) ${canonSet.size} · 명사 ${nouns.length} → 자동 화이트리스트 ${words.length}개 생성`);
}
main().catch((e) => { console.error(e); process.exit(1); });
