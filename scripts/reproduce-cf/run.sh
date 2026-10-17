#!/bin/sh
# Trigger the Cloudflare-hosted reproduction and wait for it. Needs URL, RUN_TOKEN and SHA (see src/index.js).
# Writes the final /status JSON to ${OUT:-result.json}. Only short curl calls run on this machine.
set -eu
: "${URL:?set URL to the deployed worker URL}" "${RUN_TOKEN:?set RUN_TOKEN}" "${SHA:?set SHA to the commit to reproduce}"
OUT=${OUT:-result.json}
H="authorization: Bearer $RUN_TOKEN"
curl -fsS -X POST -H "$H" "$URL/run?sha=$SHA"; echo
while :; do
  sleep 30
  curl -fsS -H "$H" "$URL/status" > "$OUT.tmp" || continue
  node -e 'const s=JSON.parse(require("fs").readFileSync(process.argv[1]));console.log(new Date().toISOString(),(s.phases||"").trim().split("\n").pop()||"booting");process.exit(s.done?0:1)' "$OUT.tmp" && break || true
done
mv "$OUT.tmp" "$OUT"
node -e 'const s=JSON.parse(require("fs").readFileSync(process.argv[1]));console.log("exit",s.exit,s.sha);console.log((s.check||"").split("\n").filter(l=>/^\*\*/.test(l)).join("\n"))' "$OUT"
curl -fsS -X POST -H "$H" "$URL/destroy"; echo
