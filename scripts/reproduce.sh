#!/usr/bin/env bash
# One command from a fresh clone to the README's numbers: data check -> deps -> training -> evaluation -> number check.
#
#   scripts/reproduce.sh          # about 9 min on a 4-8 core laptop CPU (see REPRODUCE.md for per-step times)
#   scripts/reproduce.sh --full   # also re-runs model-search rounds 1-3 (about 10 more min)
#
# Needs: uv (https://docs.astral.sh/uv/), git, and the challenge data in data/ (see data/README.md).
# Seeds are fixed (SEED = 20261017 in train.py; autoresearch and stratified checks use fixed seeds), so reruns are identical.
# Writes analysis/out/*, src/data/metrics.json, src/data/survivors.json, submission/heldout_predictions.csv,
# runs/autoresearch/*, and runs/reproduce-check.md (the README number table). Exit 1 if any README number differs.
set -euo pipefail
cd "$(dirname "$0")/.."
FULL=0; [[ "${1:-}" == "--full" ]] && FULL=1
PY=(uv run --frozen python -I)
T0=$SECONDS
step() {  # step <name> <command...>: run it and print how long it took
  local name=$1 t=$SECONDS; shift
  echo "==> $name"
  "$@"
  echo "    $name: $((SECONDS - t)) s"
  echo "| $name | $((SECONDS - t)) s |" >> runs/reproduce-times.md
}

[[ -f data/SHA256SUMS ]] || { echo "data/SHA256SUMS missing"; exit 2; }
if command -v sha256sum >/dev/null; then SUM=(sha256sum); else SUM=(shasum -a 256); fi
(cd data && "${SUM[@]}" -c --quiet SHA256SUMS) || { echo "data/ does not match data/SHA256SUMS: see data/README.md"; exit 2; }
printf '| step | time |\n|---|---|\n' > runs/reproduce-times.md

step "uv sync (Python 3.14.7 + pinned deps)" uv sync --frozen --quiet
if [[ $FULL == 1 ]]; then
  step "model search round 1" "${PY[@]}" analysis/autoresearch.py 1
  step "model search round 2" "${PY[@]}" analysis/autoresearch.py 2
  step "model search round 3" "${PY[@]}" analysis/autoresearch.py 3
fi
step "train.py (10x5 CV, final forest, SHAP, submission)" "${PY[@]}" analysis/train.py data/meps
step "synthea.py (Q1-Q3)" "${PY[@]}" analysis/synthea.py data
step "autoresearch nested (37 candidates x 10 outer folds)" "${PY[@]}" analysis/autoresearch.py nested
step "autoresearch nested-interpretable" "${PY[@]}" analysis/autoresearch.py nested-interpretable
step "stratified.py (within prior-use groups)" "${PY[@]}" analysis/stratified.py data/meps
step "fairness_mitigation.py (pre-registered NH Black test)" "${PY[@]}" analysis/fairness_mitigation.py data/meps
step "export.py (API data, tiers, fairness, first event)" "${PY[@]}" analysis/export.py data/meps
echo "| total | $((SECONDS - T0)) s |" >> runs/reproduce-times.md
echo "==> check README numbers"
"${PY[@]}" scripts/check_numbers.py --out runs/reproduce-check.md
