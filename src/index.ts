/**
 * C1 Care Team Risk API (Coach Console module).
 *   GET /api/c1/survivors       roster tiles, sorted alert > watch > ok, then by risk
 *   GET /api/c1/survivors/:id   survivor panel: status, evidence, recommendations, charts, profile, caveat
 *   GET /api/c1/metrics         model card: CV metrics vs baseline, calibration, fairness, clinical-records verdict
 *   GET /                       standalone demo page (public/index.html)
 * Predictions are computed offline (analysis/train.py, analysis/synthea.py, analysis/export.py) and baked into src/data.
 */
import S from "./data/survivors.json";
import M from "./data/metrics.json";

interface Env {
  ASSETS: { fetch(req: Request): Promise<Response> };
  GIT_SHA?: string; // set at deploy: npm run deploy (wrangler deploy --var GIT_SHA:<commit>)
}

const SUBMISSION_SHA256 = (M as { servedModel: { provenance: { submissionSha256: string } } }).servedModel.provenance.submissionSha256;

const details = S.details as Record<string, unknown>;

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, OPTIONS",
  "access-control-allow-headers": "content-type",
};

const json = (body: unknown, env: Env, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=60", ...CORS,
      // provenance on every API response: the commit this Worker was deployed from and the hash of the submission it serves
      "x-c1-commit": env.GIT_SHA || "unknown", "x-c1-artifact": `sha256:${SUBMISSION_SHA256}`,
      "access-control-expose-headers": "x-c1-commit, x-c1-artifact",
    },
  });

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (!path.startsWith("/api/")) return env.ASSETS.fetch(req);
    if (req.method !== "GET") return json({ error: "method not allowed" }, env, 405);

    if (path === "/api/c1/survivors") return json(S.roster, env);
    const m = path.match(/^\/api\/c1\/survivors\/([^/]+)$/);
    if (m) {
      const d = details[decodeURIComponent(m[1])];
      return d ? json(d, env) : json({ error: "survivor not found" }, env, 404);
    }
    if (path === "/api/c1/metrics")
      return json({ build: { gitSha: env.GIT_SHA || "unknown", submissionSha256: SUBMISSION_SHA256,
                             note: "gitSha is the commit deployed; submissionSha256 is the served predictions file, the same hash scripts/check_numbers.py prints on any reproduce run" }, ...M }, env);
    return json({ error: "not found" }, env, 404);
  },
};
