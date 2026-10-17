// c1-reproduce: rerun scripts/reproduce.sh --full from a fresh GitHub clone on Cloudflare Containers.
//
// Where it runs: a Durable Object (`Reproducer`) starts one Cloudflare Container (Cloudflare-managed image
// `cloudflare/debian-trixie`, instance standard-4) with Internet access. No local Docker is needed. Inside the container:
//   apt-get install git curl unzip → uv 0.12.15 (astral installer, pinned) → git clone https://github.com/zaycruz/c1-acute-risk
//   → git checkout <sha> → fetch meps.zip + synthea.zip from this Worker (private R2, bearer token) → check their sha256
//   → unzip into data/ → scripts/reproduce.sh --full → record versions, git status and the diff against the commit.
// The sponsor data never enters git or the image; it sits in R2 only for the run.
//
// How to run (from scripts/reproduce-cf/; full steps in REPRODUCE.md):
//   npm ci && npx wrangler r2 bucket create c1-reproduce-data
//   npx wrangler r2 object put c1-reproduce-data/meps.zip --file <Challenge_1>/meps.zip --remote   (same for synthea.zip)
//   npx wrangler deploy && echo "<long random string>" | npx wrangler secret put RUN_TOKEN
//   RUN_TOKEN=<same> URL=https://c1-reproduce.<subdomain>.workers.dev SHA=<commit> sh run.sh
//   then delete the objects, the bucket and the Worker (`npx wrangler delete c1-reproduce`) and check `npx wrangler containers list`.
//
// HTTP API (all need `authorization: Bearer $RUN_TOKEN`):
//   POST /run?sha=<commit>   start the container and the job (idempotent while a job is running)
//   GET  /status             {done, exit, phases, tail}; when done also the check table, times, versions and git diff
//   GET  /data/<name>.zip    the sponsor zip from R2 (used by the container)
//   POST /destroy            stop the container

import { DurableObject } from "cloudflare:workers";

const REPO = "https://github.com/zaycruz/c1-acute-risk";
const ZIPS = {
  "meps.zip": "1a5da0e18b3b2f0bc1adf0141c7173a2ba83393673a2e5b221d4cb44f8526d2e",
  "synthea.zip": "d6fd85c48b3116d48d7dc6260e64bfc20f65b4aae54dc35d178a3064f5c0a2c4",
};

// Each phase is timed. The exit code and DONE marker are written even when a step fails.
const job = (sha, base) => `
export HOME=/root DEBIAN_FRONTEND=noninteractive CI=1 PATH=/usr/local/bin:$PATH
W=/work; mkdir -p $W; cd $W
ph() { echo "$1 $(date -u +%s)" >> $W/phases; echo "=== $1 $(date -u +%FT%TZ)"; }
finish() { echo "\${REPRO_EXIT:-none}" > $W/exit; ph done; touch $W/DONE; }
trap finish EXIT
ph start
ph apt
apt-get update -qq && apt-get install -y -qq --no-install-recommends git ca-certificates curl unzip >/dev/null || exit 1
curl -fsS https://1.1.1.1/cdn-cgi/trace > $W/trace || true
ph uv-install
curl -LsSf https://astral.sh/uv/0.12.15/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh || exit 1
ph clone
git clone ${REPO} $W/repo || exit 1
cd $W/repo && git checkout -q ${sha} || exit 1
git rev-parse HEAD > $W/sha
ph data
mkdir -p $W/zips
for z in meps.zip synthea.zip; do curl -fsS -H "authorization: Bearer $RUN_TOKEN" ${base}/data/$z -o $W/zips/$z || exit 1; done
(cd $W/zips && printf '%s  meps.zip\\n%s  synthea.zip\\n' ${ZIPS["meps.zip"]} ${ZIPS["synthea.zip"]} | sha256sum -c) > $W/zipcheck 2>&1 || exit 1
unzip -q $W/zips/meps.zip -d data && unzip -q $W/zips/synthea.zip -d data || exit 1
ph reproduce
scripts/reproduce.sh --full 2>&1 | tee $W/reproduce.out
REPRO_EXIT=\${PIPESTATUS[0]}
ph collect
{ echo "uv: $(uv --version)"; echo "python: $(uv run --frozen python -I -c 'import sys,platform;print(sys.version.split()[0], platform.platform())')";
  echo "cpu: $(nproc) x $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs)"; echo "mem: $(free -g | awk '/Mem/{print $2}') GB";
  echo "git: $(git --version)"; echo "os: $(. /etc/os-release; echo $PRETTY_NAME)"; } > $W/versions
uv export --frozen --no-hashes --no-header > $W/freeze 2>&1 || true
git status --porcelain > $W/porcelain
git diff --stat > $W/diffstat
git diff -I '"seconds"' --stat > $W/diffstat-ignoring-seconds
git diff -I '"seconds"' -- . ':(exclude)runs/autoresearch/log.md' | head -c 60000 > $W/diff
`;

const sh = async (c, cmd) => {
  const p = await c.exec(["bash", "-c", cmd], { env: { HOME: "/root" } });
  const o = await p.output();
  const d = new TextDecoder();
  return { code: o.exitCode, out: d.decode(o.stdout), err: d.decode(o.stderr) };
};

export class Reproducer extends DurableObject {
  async fetch(req) {
    const c = this.ctx.container;
    const url = new URL(req.url);
    if (url.pathname === "/run") {
      const sha = url.searchParams.get("sha") || "";
      if (!/^[0-9a-f]{7,40}$/.test(sha)) return Response.json({ error: "sha must be a commit hash" }, { status: 400 });
      if (!c.running) {
        c.start({ image: "cloudflare/debian-trixie", instance: "standard-4", enableInternet: true, entrypoint: ["sleep", "infinity"] });
      }
      const already = await sh(c, "test -f /work/job.sh && echo yes || echo no");
      if (already.out.trim() === "yes") return Response.json({ started: false, note: "job already started" });
      const r = await c.exec(
        ["bash", "-c", 'mkdir -p /work && printf "%s" "$1" > /work/job.sh && (setsid nohup bash /work/job.sh > /work/log.txt 2>&1 &) ; echo started', "_", job(sha, url.origin)],
        { env: { HOME: "/root", RUN_TOKEN: this.env.RUN_TOKEN } },
      );
      const o = await r.output();
      return Response.json({ started: true, out: new TextDecoder().decode(o.stdout) });
    }
    if (url.pathname === "/status") {
      if (!c.running) return Response.json({ running: false });
      const read = async (f) => (await sh(c, `cat ${f} 2>/dev/null`)).out;
      const done = (await read("/work/DONE")) !== "" || (await sh(c, "test -f /work/DONE && echo 1")).out.trim() === "1";
      const res = { running: true, done, phases: await read("/work/phases"), exit: (await read("/work/exit")).trim(),
                    tail: (await sh(c, "tail -n 20 /work/log.txt 2>/dev/null")).out };
      if (done) {
        for (const k of ["sha", "trace", "zipcheck", "versions", "freeze", "porcelain", "diffstat", "diffstat-ignoring-seconds", "diff", "reproduce.out"]) res[k] = await read(`/work/${k}`);
        res.check = await read("/work/repo/runs/reproduce-check.md");
        res.times = await read("/work/repo/runs/reproduce-times.md");
        res.log = (await sh(c, "tail -c 100000 /work/log.txt")).out;
      }
      return Response.json(res);
    }
    if (url.pathname === "/destroy") {
      if (c.running) await c.destroy();
      return Response.json({ destroyed: true });
    }
    return new Response("not found", { status: 404 });
  }
}

export default {
  async fetch(req, env) {
    if (!env.RUN_TOKEN || req.headers.get("authorization") !== `Bearer ${env.RUN_TOKEN}`) {
      return new Response("unauthorized", { status: 401 });
    }
    const url = new URL(req.url);
    const m = url.pathname.match(/^\/data\/(meps|synthea)\.zip$/);
    if (m) {
      const obj = await env.DATA.get(`${m[1]}.zip`);
      return obj ? new Response(obj.body, { headers: { "content-type": "application/zip" } }) : new Response("missing", { status: 404 });
    }
    return env.REPRODUCER.getByName("c1-reproduce").fetch(req);
  },
};
