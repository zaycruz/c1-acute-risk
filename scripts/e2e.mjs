#!/usr/bin/env node
// E2E check for C1 Care Team Risk: hits every endpoint of the deployed Worker, checks the contract,
// validates the held-out prediction file, and saves everything under runs/ as a repeatable artifact.
// Usage: node scripts/e2e.mjs [baseUrl]   (default: the workers.dev deploy)
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const BASE = (process.argv[2] || "https://c1-acute-risk.zay-259.workers.dev").replace(/\/$/, "");
const checks = [];
const responses = {};
const check = (name, ok, info) => { checks.push({ name, ok: !!ok, ...(info ? { info } : {}) }); };

async function get(path) {
  const t0 = Date.now();
  const res = await fetch(BASE + path);
  const text = await res.text();
  let body = text;
  try { body = JSON.parse(text); } catch {}
  return { status: res.status, ms: Date.now() - t0, headers: Object.fromEntries(res.headers), body };
}
const STATUSES = ["alert", "watch", "ok"];
const AUDIENCES = ["coach", "care-team", "survivor"];

// 1. Held-out prediction file (local, the file we submit)
const csv = readFileSync(new URL("../submission/heldout_predictions.csv", import.meta.url), "utf8").trim().split(/\r?\n/);
const tmpl = readFileSync(new URL("../data/meps/heldout_ids.csv", import.meta.url), "utf8").trim().split(/\r?\n/);
const devIds = new Set(readFileSync(new URL("../data/meps/meps2018_followup_dev.csv", import.meta.url), "utf8").trim().split(/\r?\n/).slice(1).map((l) => l.split(",")[0]));
check("submission header is exactly ID,predicted_risk", csv[0] === "ID,predicted_risk", { header: csv[0] });
const rows = csv.slice(1).map((l) => l.split(","));
const tIds = tmpl.slice(1).map((l) => l.split(",")[0]);
check("submission has one row per template ID, in template order", rows.length === tIds.length && rows.every((r, i) => r[0] === tIds[i]), { rows: rows.length, template: tIds.length });
check("submission IDs unique", new Set(rows.map((r) => r[0])).size === rows.length);
const vals = rows.map((r) => Number(r[1]));
check("predicted_risk all numeric in [0,1], no blanks", rows.every((r) => r.length === 2 && r[1] !== "") && vals.every((v) => Number.isFinite(v) && v >= 0 && v <= 1),
  { min: Math.min(...vals), max: Math.max(...vals), mean: vals.reduce((a, b) => a + b, 0) / vals.length });
check("no held-out ID is in the development set", rows.every((r) => !devIds.has(r[0])));

// 2. GET /
const home = await get("/");
check("GET / returns 200 HTML demo page", home.status === 200 && /<title>Care Team Risk<\/title>/.test(home.body));
responses["/"] = { status: home.status, ms: home.ms, bytes: home.body.length };

// 3. Roster
const roster = await get("/api/c1/survivors");
responses["/api/c1/survivors"] = roster;
const list = Array.isArray(roster.body) ? roster.body : [];
check("roster 200, one tile per held-out survivor", roster.status === 200 && list.length === tIds.length, { count: list.length });
check("roster CORS header", roster.headers["access-control-allow-origin"] === "*");
const keys = ["survivorId", "displayName", "status", "headline", "updatedAt", "fairnessFlags", "humanCheck", "tags"];
check("roster tiles have the contract keys plus fairnessFlags, humanCheck and tags", list.every((r) => JSON.stringify(Object.keys(r).sort()) === JSON.stringify([...keys].sort())));
check("roster ids are c1-<MEPS ID>", list.every((r) => /^c1-S[0-9A-F]{8}$/.test(r.survivorId)));
check("roster status in ok|watch|alert", list.every((r) => STATUSES.includes(r.status)));
check("roster sorted alert > watch > ok", list.every((r, i) => i === 0 || STATUSES.indexOf(list[i - 1].status) <= STATUSES.indexOf(r.status)));
check("updatedAt is ISO time", list.every((r) => !Number.isNaN(Date.parse(r.updatedAt))));
const mix = Object.fromEntries(STATUSES.map((s) => [s, list.filter((r) => r.status === s).length]));
check("roster has alert, watch and ok survivors", mix.alert > 0 && mix.watch > 0 && mix.ok > 0, mix);

// 4. Every survivor panel; risk must match the submission file and the tier thresholds
const subRisk = Object.fromEntries(rows.map((r) => [`c1-${r[0]}`, Number(r[1])]));
let ok = 0;
const failures = [];
const panels = {};
for (const r of list) {
  const d = await get(`/api/c1/survivors/${r.survivorId}`);
  const b = d.body;
  panels[r.survivorId] = b;
  const t = b?.thresholds;
  const good = d.status === 200 && b.survivorId === r.survivorId && b.status === r.status && b.headline === r.headline &&
    typeof b.summary === "string" && b.summary.length > 0 &&
    Array.isArray(b.evidence) && b.evidence.length > 0 && b.evidence.every((e) => typeof e.kind === "string" && typeof e.text === "string" && e.text) &&
    Array.isArray(b.recommendations) && b.recommendations.length > 0 && b.recommendations.every((x) => AUDIENCES.includes(x.audience) && typeof x.text === "string" && x.text) &&
    b.charts && typeof b.charts === "object" && b.profile && typeof b.profile === "object" &&
    (b.caveat === undefined || typeof b.caveat === "string") &&
    Math.abs(b.risk - subRisk[r.survivorId]) < 1e-4 &&
    b.status === (b.risk >= t.alert ? "alert" : b.risk >= t.watch ? "watch" : "ok");
  if (good) ok++; else failures.push(r.survivorId);
  if (r === list[0]) responses[`/api/c1/survivors/${r.survivorId}`] = d;
}
const LIM = { riskWords: 60, forEllie: 160, headline: 90, evidence: 120 };
const over = [];
for (const r of list) {
  const b = panels[r.survivorId];
  if (!b) continue;
  if (!(typeof b.riskWords === "string" && b.riskWords.length <= LIM.riskWords)) over.push([r.survivorId, "riskWords"]);
  if (!(typeof b.forEllie === "string" && b.forEllie.length <= LIM.forEllie && /not cause/i.test(b.forEllie))) over.push([r.survivorId, "forEllie"]);
  if (b.headline.length > LIM.headline) over.push([r.survivorId, "headline"]);
  if (b.evidence.some((e) => e.text.length > LIM.evidence)) over.push([r.survivorId, "evidence"]);
  const rf = b.redFlags;
  if (!(rf && typeof rf.careTeamToday === "boolean" && typeof rf.banner === "string" && rf.banner.length <= 120 && rf.callTodayIf?.length === 5 &&
        Array.isArray(rf.fromSurvey) && rf.fromSurvey.every((f) => ["today", "this-week"].includes(f.urgency) && f.text.length <= 120) &&
        rf.careTeamToday === rf.fromSurvey.some((f) => f.urgency === "today") && typeof rf.socialNeeds?.text === "string" && rf.socialNeeds.text.length <= 160)) over.push([r.survivorId, "redFlags"]);
  if (!Array.isArray(b.fairnessFlags) || b.fairnessFlags.some((f) => !f.flag || f.flag === "ok" || !f.text)) over.push([r.survivorId, "fairnessFlags"]);
  const hc = b.humanCheck;
  const weakRace = (b.fairnessFlags || []).some((f) => f.attribute === "race_ethnicity" && f.flag === "weak-ranking");
  if (!(hc && typeof hc.required === "boolean" && hc.required === (weakRace && b.status !== "ok") &&
        (hc.required ? typeof hc.reason === "string" && hc.reason.length <= 120 : hc.reason === null))) over.push([r.survivorId, "humanCheck"]);
}
check("roster fairness fields agree with each survivor panel (flags, humanCheck, tags at most 40 characters)", list.every((r) => {
  const b = panels[r.survivorId];
  return b && Array.isArray(r.fairnessFlags) && JSON.stringify(r.fairnessFlags) === JSON.stringify((b.fairnessFlags || []).map((f) => ({ attribute: f.attribute, group: f.group, flag: f.flag }))) &&
    r.humanCheck === b.humanCheck?.required && Array.isArray(r.tags) && r.tags.length === r.fairnessFlags.length + (r.humanCheck ? 1 : 0) &&
    r.tags.every((t) => typeof t.label === "string" && t.label.length <= 40 && typeof t.kind === "string");
}), { humanCheck: list.filter((r) => r.humanCheck).length, flagged: list.filter((r) => r.fairnessFlags?.length).length });
check("console display fields within agreed lengths (riskWords 60, forEllie 160 with caveat, headline 90, evidence 120), redFlags well formed, humanCheck set exactly for weak-ranking groups off the ok tier", over.length === 0 && Object.keys(panels).length === list.length, { over: over.slice(0, 10) });
check("every survivor panel matches the contract, the submission risk and its tier", ok === list.length, { ok, failures: failures.slice(0, 10) });
const missing = await get("/api/c1/survivors/c1-nope");
check("unknown survivor returns 404 JSON", missing.status === 404 && missing.body?.error);
responses["/api/c1/survivors/c1-nope"] = missing;
const post = await fetch(BASE + "/api/c1/survivors", { method: "POST" });
check("POST is rejected with 405", post.status === 405);

// 5. Metrics / model card
const met = await get("/api/c1/metrics");
responses["/api/c1/metrics"] = met;
const M = met.body;
const F = M.finalModel?.key;
check("metrics 200 with final model and baseline", met.status === 200 && F && M.metrics?.[F] && M.metrics?.baseline, { finalModel: F });
if (M.metrics) {
  const m = M.metrics, d = M.deltaVsBaseline[F];
  const s = { aurocModel: m[F].auroc.value, aurocBaseline: m.baseline.auroc.value, dAuroc: d.auroc.value, dAurocCi: d.auroc.ci95,
    brierModel: m[F].brier.value, brierBaseline: m.baseline.brier.value, dBrierCi: d.brier.ci95,
    slopeModel: m[F].cal_slope.value, slopeBaseline: m.baseline.cal_slope.value };
  check("every metric has a 95% CI", ["auroc", "auprc", "brier", "cal_slope", "cal_intercept"].every((k) => Array.isArray(m[F][k].ci95) && m[F][k].ci95.length === 2));
  check("model is not worse than baseline on AUROC and Brier (point estimates)", s.aurocModel >= s.aurocBaseline && s.brierModel <= s.brierBaseline, s);
  check("model calibration slope closer to 1 than baseline", Math.abs(s.slopeModel - 1) < Math.abs(s.slopeBaseline - 1), s);
  check("calibration curves for model and baseline", M.calibrationCurve?.[F]?.length >= 4 && M.calibrationCurve?.baseline?.length >= 4);
  const attrs = new Set((M.fairness || []).map((r) => r.attribute));
  check("fairness table covers age, sex, race/ethnicity, insurance, cancer type", ["age", "sex", "race_ethnicity", "insurance", "cancer_type"].every((a) => attrs.has(a)));
  check("fairness flags small subgroups", (M.fairness || []).some((r) => r.tooSmall) && (M.fairness || []).every((r) => r.tooSmall === (r.n < 30 || r.positives < 10)),
    { tooSmall: (M.fairness || []).filter((r) => r.tooSmall).map((r) => `${r.attribute}:${r.group}`) });
  check("clinical-records verdict present (not pending)", M.clinicalRecords?.verdict && M.clinicalRecords.verdict !== "pending", { verdict: M.clinicalRecords?.verdict });
  check("tiers cover all dev survivors and rise in observed rate", M.tiers.tiers.reduce((a, t) => a + t.n, 0) === M.data.devSurvivors &&
    M.tiers.tiers[0].observedRate > M.tiers.tiers[1].observedRate && M.tiers.tiers[1].observedRate > M.tiers.tiers[2].observedRate,
    M.tiers.tiers.map((t) => ({ status: t.status, n: t.n, rate: t.observedRate })));
  check("roster status mix matches metrics.heldoutStatusMix", JSON.stringify(M.heldoutStatusMix) === JSON.stringify(mix), { metrics: M.heldoutStatusMix, roster: mix });
  const S = M.modelSearch, FE = M.firstEvent;
  check("nested-CV estimate present: log loss significantly better than baseline", S?.outerFolds === 10 && S.vsBaseline.dLogLossCi95[1] < 0,
    { dAuroc: S?.vsBaseline.dAuroc, dAurocCi: S?.vsBaseline.dAurocCi95, dLogLoss: S?.vsBaseline.dLogLoss, dLogLossCi: S?.vsBaseline.dLogLossCi95, picks: S?.picks });
  check("final model is not worse than the previous submission on log loss (paired CI)", M.deltaVsPrevious?.log_loss?.ci95?.[1] < 0, M.deltaVsPrevious?.log_loss);
  check("first-event analysis covers the survivors without 2017 acute care", FE?.n > 0 && FE.n < M.data.devSurvivors && FE.events > 0 && Array.isArray(FE.deltaCi95), FE && { n: FE.n, events: FE.events, model: FE.aurocModel, baseline: FE.aurocBaseline });
  check("SHAP factors have impact and direction", (M.factors || []).length >= 10 && M.factors.every((f) => f.meanAbsLogit >= 0 && ["raises", "lowers"].includes(f.direction)));
  const D = M.display;
  check("display block is ready to render (plain text, no raw objects)", D && typeof D.headline === "string" && D.keyNumbers?.length >= 3 && D.keyNumbers.every((k) => typeof k.value === "string" && typeof k.label === "string") &&
    D.howSure?.length && D.limits?.length && M.plainFactors.every((r) => typeof r.text === "string") && M.tiers.tiers.every((t) => typeof t.text === "string") &&
    M.fairness.every((g) => typeof g.text === "string" && ["ok", "too-small", "weak-ranking", "under-predicted", "over-predicted"].includes(g.flag)), D && { headline: D.headline, keyNumbers: D.keyNumbers });
  check("display block within agreed lengths (headline 140, KPI value 9 / label 60 / sub 50, lines 200)", D && D.headline.length <= 140 &&
    D.keyNumbers.every((k) => k.value.length <= 9 && k.label.length <= 60 && k.sub.length <= 50) &&
    [...D.howSure, ...D.limits, D.nextQuestion].every((x) => x.length <= 200), D && { headline: D.headline.length, keyNumbers: D.keyNumbers.map((k) => [k.value.length, k.label.length, k.sub.length]) });
  const SM = M.servedModel;
  const csvSha = createHash("sha256").update(readFileSync(new URL("../submission/heldout_predictions.csv", import.meta.url))).digest("hex");
  check("served model: its own 50%+ calls with CIs, expected held-out AUROC range, and the API's submission hash equals the committed CSV",
    SM && SM.callsAt50?.forest?.cameTrueCi95?.length === 2 && SM.callsAt50.forest.n > 0 && SM.callsAt50.differenceCi95?.length === 2 &&
    SM.expectedHeldout?.aurocRange95?.[0] < SM.expectedHeldout.aurocRange95[1] && SM.provenance?.submissionSha256 === csvSha &&
    Number.isInteger(SM.provenance.inputRangeCheck?.total) && M.display.keyNumbers.some((k) => k.value === `${Math.round(SM.callsAt50.forest.cameTrue * 100)}%`),
    SM && { calls: SM.callsAt50.forest, sha: SM.provenance?.submissionSha256?.slice(0, 12), outOfRange: SM.provenance?.inputRangeCheck?.total });
  const FMt = M.fairnessMitigation;
  check("fairness mitigation: pre-registered variants with CIs, a decision, and the language gap stated", FMt && FMt.variants?.length === 5 &&
    FMt.variants.every((v) => v.nhBlackAurocCi95?.length === 2 && Number.isFinite(v.overallLogLoss)) &&
    FMt.variants.filter((v) => v.variant !== "current").every((v) => typeof v.passes === "boolean" && v.vsCurrent?.groupDeltaAurocCi95?.length === 2) &&
    Array.isArray(FMt.passed) && typeof FMt.decision === "string" && FMt.language?.available === false &&
    FMt.extraSubgroups?.length === 2 && FMt.whoThisDoesNotServeYet?.length >= 3 && FMt.whoThisDoesNotServeYet.every((x) => x.length <= 200),
    FMt && { decision: FMt.decision, passed: FMt.passed });
  const AB = M.alertBudget;
  check("alert budget: 5 cut-offs, weekly load per 100 survivors, and the alert tier's held-out count matches the roster", AB && AB.cutoffs?.length === 5 &&
    AB.cutoffs.every((c, i) => c.per100SurvivorsPerWeek > 0 && (i === 0 || c.topShare > AB.cutoffs[i - 1].topShare)) &&
    AB.current?.heldoutFlagged === mix.alert && typeof AB.justification === "string", AB && { current: AB.current });
  responses.summary = { ...s, nested: S && { auroc: S.auroc, dAuroc: S.vsBaseline.dAuroc, dLogLoss: S.vsBaseline.dLogLoss }, firstEvent: FE && { model: FE.aurocModel, baseline: FE.aurocBaseline } };
}

const passed = checks.filter((c) => c.ok).length;
const at = new Date().toISOString();
const report = { at, base: BASE, passed, total: checks.length, checks, responses };
mkdirSync(new URL("../runs/", import.meta.url), { recursive: true });
const stamp = at.replace(/[:.]/g, "-");
writeFileSync(new URL(`../runs/e2e-${stamp}.json`, import.meta.url), JSON.stringify(report, null, 1));
writeFileSync(new URL("../runs/e2e-latest.json", import.meta.url), JSON.stringify(report, null, 1));
for (const c of checks) console.log(`${c.ok ? "PASS" : "FAIL"}  ${c.name}${c.ok || !c.info ? "" : "  " + JSON.stringify(c.info)}`);
console.log(`\n${passed}/${checks.length} checks passed against ${BASE}; saved runs/e2e-${stamp}.json`);
process.exit(passed === checks.length ? 0 : 1);
