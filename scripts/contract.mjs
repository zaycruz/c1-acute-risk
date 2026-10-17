#!/usr/bin/env node
// Turns the real responses captured by `npm run e2e` (runs/e2e-latest.json) into CONTRACT.md.
import { readFileSync, writeFileSync } from "node:fs";
const R = JSON.parse(readFileSync(new URL("../runs/e2e-latest.json", import.meta.url), "utf8"));
const r = R.responses;
const roster = r["/api/c1/survivors"].body;
const detailKey = Object.keys(r).find((k) => /^\/api\/c1\/survivors\/c1-S/.test(k));
const detail = r[detailKey].body;
const M = r["/api/c1/metrics"].body;
const j = (x) => "```json\n" + JSON.stringify(x, null, 2) + "\n```";
const pick = (o, ks) => Object.fromEntries(ks.map((k) => [k, o[k]]));
const md = `# C1 Care Team Risk: API contract

Base URL (deployed): \`${R.base}\`. All responses are JSON with \`access-control-allow-origin: *\`; only \`GET\` (and \`OPTIONS\`) are accepted, anything else is \`405\`.
The examples below are real responses, captured by \`npm run e2e\` on ${R.at} (${R.passed}/${R.total} checks passed) and turned into this file by \`npm run contract\`.

Predictions are for the **199 held-out MEPS survivors** (\`meps/heldout_ids.csv\`): real people, forward predictions, outcome unknown to us.
\`survivorId\` = \`c1-\` + the challenge's MEPS \`ID\`. \`updatedAt\` is the as-of date of the data (end of 2017), not the build time.

## \`GET /api/c1/survivors\`: roster tiles

Sorted by \`status\` (alert, then watch, then ok), then by risk. Status comes from calibrated risk tiers set on out-of-fold development predictions:
\`alert\` = predicted risk >= ${M.tiers.alert} (top fifth; ${Math.round(M.tiers.tiers[0].observedRate * 100)}% of development survivors in this tier had acute care),
\`watch\` = >= ${M.tiers.watch} (the base rate; ${Math.round(M.tiers.tiers[1].observedRate * 100)}% had it), \`ok\` = below (${Math.round(M.tiers.tiers[2].observedRate * 100)}%).
${roster.length} survivors (${M.heldoutStatusMix.alert} alert, ${M.heldoutStatusMix.watch} watch, ${M.heldoutStatusMix.ok} ok), showing 3:

${j(roster.slice(0, 3))}

## \`GET /api/c1/survivors/:id\`: survivor panel

Contract fields: \`survivorId, status, headline, summary, evidence, recommendations, charts, profile, caveat\`. Extra fields: \`displayName\`, \`risk\` (0..1, identical to the submitted \`predicted_risk\`), \`thresholds\`.

- \`evidence[]\`: \`{kind, text}\`. The first item (\`kind: "model"\`) states the risk and what the tier meant on development data. Then up to 4 factors that raise this person's risk and up to 2 that lower it, biggest first. Extra keys: \`feature\`, \`logitContribution\` (TreeSHAP contribution on the calibrated log-odds scale, relative to an average survivor; see analysis/explain.py). \`kind\` is one of \`prior-acute-care, medications, care-intensity, physical-function, symptoms, distress, financial-toxicity, access, treatment, support, demographic\`.
- \`recommendations[]\`: \`{audience: "coach" | "care-team" | "survivor", text}\`. Tier action first, then one per actionable driver. The coach does not diagnose; clinical items go to \`care-team\`.
- \`charts\`: \`risk\` (value, base rate, tier cut-offs), \`drivers\` (bar chart of logit contributions), \`scores\` (2017 survey scores, \`null\` = not answered), \`use2017\` (counts).
- \`caveat\`: always present: association not cause, plus a warning when the questionnaire was skipped or the person belongs to a subgroup too small to judge.

${j(detail)}

Unknown id: \`404 {"error":"survivor not found"}\`.

## \`GET /api/c1/metrics\`: model card

Top-level keys: ${Object.keys(M).map((k) => "`" + k + "`").join(", ")}.

- \`finalModel\`: \`{key, name, chosenBy, explanations, previous}\`. \`finalModel.key\` (\`forest\`) names the final model in \`metrics\`, \`deltaVsBaseline\` and \`calibrationCurve\`.
- \`metrics.{baseline,logistic,gbm_calibrated,forest}\`: \`auroc, auprc, brier, log_loss, cal_intercept, cal_slope, mean_pred\`, each \`{value, ci95}\`, out-of-fold on the 466 development survivors. \`logistic\` is the previous submission.
- \`modelSearch\`: the unbiased nested-CV estimate of the model search (the 10x5 CV numbers for \`forest\` are post-selection). \`deltaVsPrevious\`: forest vs the previous logistic model, paired.
- \`firstEvent\`: ranking among survivors with no 2017 ER visit or hospital stay (the proposed prevention target).
- \`deltaVsBaseline\`: paired bootstrap differences (auroc, auprc, brier, log_loss) with \`ci95\` and \`p_better\`.
- \`calibrationCurve\`: 5 equal-size bins per model, with Wilson 95% CIs on the observed rate.
- \`fairness[]\` / \`fairnessBaseline[]\`: per subgroup \`n, positives, observedRate, meanPredicted, oe, brier, auroc, tooSmall\` (n < 30 or < 10 events).
- \`factors[]\`: TreeSHAP global importance (\`meanAbsLogit\`, mean absolute calibrated log-odds contribution) and \`direction\` of a higher value; \`plainFactors[]\`: observed 2018 rates with vs without a 2017 factor.
- \`clinicalRecords\`: \`{verdict, detail}\`; \`clinicalRecordsDetail\`: the full Synthea analysis (Q1 within Synthea, Q2 transport, Q3 increment, stratum sizes, population shift).

Excerpt:

${j({ ...pick(M, ["asOf", "outcome", "data", "validation", "finalModel"]), metrics: { [M.finalModel.key]: M.metrics[M.finalModel.key], baseline: M.metrics.baseline }, deltaVsBaseline: { [M.finalModel.key]: M.deltaVsBaseline[M.finalModel.key] }, deltaVsPrevious: M.deltaVsPrevious, modelSearch: M.modelSearch, firstEvent: M.firstEvent, factors: M.factors.slice(0, 3), tiers: M.tiers, fairness: M.fairness.slice(0, 2), plainFactors: M.plainFactors.slice(0, 2), clinicalRecords: M.clinicalRecords, heldoutStatusMix: M.heldoutStatusMix })}

## \`GET /\`

Standalone demo page: model card, roster, one survivor panel. Same data as the API.
`;
writeFileSync(new URL("../CONTRACT.md", import.meta.url), md);
console.log("wrote CONTRACT.md", md.length, "bytes");
