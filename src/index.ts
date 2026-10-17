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
}

const details = S.details as Record<string, unknown>;

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, OPTIONS",
  "access-control-allow-headers": "content-type",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=60", ...CORS },
  });

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (!path.startsWith("/api/")) return env.ASSETS.fetch(req);
    if (req.method !== "GET") return json({ error: "method not allowed" }, 405);

    if (path === "/api/c1/survivors") return json(S.roster);
    const m = path.match(/^\/api\/c1\/survivors\/([^/]+)$/);
    if (m) {
      const d = details[decodeURIComponent(m[1])];
      return d ? json(d) : json({ error: "survivor not found" }, 404);
    }
    if (path === "/api/c1/metrics") return json(M);
    return json({ error: "not found" }, 404);
  },
};
