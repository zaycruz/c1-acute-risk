#!/bin/sh
# Deploy (or upload a preview of) the Worker with the commit it was built from, served as x-c1-commit and /api/c1/metrics -> build.gitSha.
#   scripts/deploy.sh                 wrangler deploy
#   scripts/deploy.sh versions upload  preview version (promote with wrangler versions deploy <id>@100%)
set -eu
cd "$(dirname "$0")/.."
SHA=$(git rev-parse HEAD)
[ -z "$(git status --porcelain -- src public analysis submission wrangler.jsonc)" ] || SHA="$SHA-dirty"
[ $# -gt 0 ] || set -- deploy
exec npx wrangler "$@" --var "GIT_SHA:$SHA"
