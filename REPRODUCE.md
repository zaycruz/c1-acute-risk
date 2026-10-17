# Reproduce C1

Everything that produced a number in [README.md](README.md) is in this repo: data prep (`analysis/features.py`), training and 10×5 CV
(`analysis/train.py`), the model search and its nested CV (`analysis/autoresearch.py`), the stratified check (`analysis/stratified.py`),
Synthea (`analysis/synthea.py`), explanations (`analysis/explain.py`), the API data (`analysis/export.py`), the number check
(`scripts/check_numbers.py`) and the E2E (`scripts/e2e.mjs`). Seeds are fixed (`SEED = 20261017`; the model search, bootstrap and stratified check use fixed seeds too).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) 0.12 or later. It installs Python 3.14.7 and the pinned packages from `uv.lock` (`pyproject.toml`: numpy 2.5.4, pandas 3.0.6,
  pyarrow 26.0.0, scikit-learn 1.9.1, scipy 1.18.1, shap 0.54.1, joblib 1.6.0, threadpoolctl 3.7.0). No compiler is needed on macOS arm64 or Linux x86_64.
- git, unzip, and `shasum` or `sha256sum`.
- A laptop CPU is enough: 4+ cores and 4 GB RAM. The model search uses every core.
- For the E2E only: Node 20+ (`npm ci`).

## 1. Data

The challenge data is sponsor data and is not committed. [`data/README.md`](data/README.md) gives the source, the sha256 of each release zip and the layout.

```bash
git clone https://github.com/zaycruz/c1-acute-risk && cd c1-acute-risk
unzip -q path/to/Challenge_1/meps.zip -d data && unzip -q path/to/Challenge_1/synthea.zip -d data
(cd data && shasum -a 256 -c SHA256SUMS)      # 13 files, all OK
```

## 2. One command

```bash
scripts/reproduce.sh          # training, Synthea, nested CV, stratified check, export, number check
scripts/reproduce.sh --full   # also re-runs model-search rounds 1-3 (48 candidates)
```

It checks the data hashes, runs `uv sync --frozen`, runs each step with `uv run --frozen python -I`, and prints how long each one took
(`runs/reproduce-times.md`). It ends with `scripts/check_numbers.py`, which writes `runs/reproduce-check.md`, and exits 1 if this run differs from the committed outputs.

Expected runtime (measured; see the latest `runs/reproduce-*.md`):

RUNTIME_TABLE

The script overwrites the committed outputs in place (`analysis/out/`, `runs/autoresearch/`, `src/data/metrics.json`, `submission/`), so `git diff` shows any difference.
Only the `"seconds"` fields and the appended sections of `runs/autoresearch/log.md` should change: `git diff -I '"seconds"' --stat -- . ':(exclude)runs/autoresearch/log.md'` should be empty.

## 3. README numbers and where they come from

`scripts/check_numbers.py` holds this table as code and compares each number with the file and key it comes from.
"Expected value" is what the committed outputs give, rounded the way the README prints it.

| README number | file → key | expected value |
|---|---|---|
| Nested AUROC, search | `runs/autoresearch/round-nested.json` → `procedure/auroc` | 0.711 |
| Nested AUROC, baseline | `runs/autoresearch/round-nested.json` → `baseline/auroc` | 0.672 |
| Nested ΔAUROC vs baseline | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dAuroc` | +0.039 |
| Nested ΔAUROC CI | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dAurocCi95` | [-0.015, +0.091] |
| Nested P(AUROC better) | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/pAurocBetter` | 0.93 |
| Nested log loss, search | `runs/autoresearch/round-nested.json` → `procedure/logLoss` | 0.539 |
| Nested log loss, baseline | `runs/autoresearch/round-nested.json` → `baseline/logLoss` | 0.606 |
| Nested Δlog loss vs baseline | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dLogLoss` | -0.067 |
| Nested Δlog loss CI | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dLogLossCi95` | [-0.115, -0.020] |
| Nested candidates | `runs/autoresearch/round-nested.json` → `len(candidatePool)` | 37 |
| Nested folds won by the forest | `runs/autoresearch/round-nested.json` → `picks/rf | 6 |
| Top-fifth events, search | `src/data/metrics.json` → `modelSearch/top20Events/procedure` | 52 |
| Top-fifth events, baseline | `src/data/metrics.json` → `modelSearch/top20Events/baseline` | 45 |
| 50%+ calls that came true, search | `src/data/metrics.json` → `modelSearch/callsAt50/procedure/cameTrue` | 67% |
| 50%+ calls, search (n) | `src/data/metrics.json` → `modelSearch/callsAt50/procedure/n` | 55 |
| 50%+ calls that came true, baseline | `src/data/metrics.json` → `modelSearch/callsAt50/baseline/cameTrue` | 49% |
| 50%+ calls, baseline (n) | `src/data/metrics.json` → `modelSearch/callsAt50/baseline/n` | 73 |
| Nested ΔAUROC vs first submission | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dAuroc` | +0.034 |
| Nested ΔAUROC vs first submission CI | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dAurocCi95` | [-0.001, +0.066] |
| Nested Δlog loss vs first submission | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dLogLoss` | -0.027 |
| Nested Δlog loss vs first submission CI | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dLogLossCi95` | [-0.043, -0.009] |
| 10×5 AUROC, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/auroc/value` | 0.659 |
| 10×5 AUROC CI, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/auroc/ci95` | [0.603, 0.718] |
| 10×5 AUROC, logistic | `analysis/out/metrics_meps.json` → `metrics/logistic/auroc/value` | 0.666 |
| 10×5 AUROC, forest | `analysis/out/metrics_meps.json` → `metrics/forest/auroc/value` | 0.713 |
| 10×5 AUROC CI, forest | `analysis/out/metrics_meps.json` → `metrics/forest/auroc/ci95` | [0.662, 0.764] |
| 10×5 ΔAUROC forest vs baseline | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auroc/value` | +0.053 |
| 10×5 ΔAUROC CI | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auroc/ci95` | [-0.001, +0.105] |
| 10×5 AUPRC, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/auprc/value` | 0.423 |
| 10×5 AUPRC, logistic | `analysis/out/metrics_meps.json` → `metrics/logistic/auprc/value` | 0.438 |
| 10×5 AUPRC, forest | `analysis/out/metrics_meps.json` → `metrics/forest/auprc/value` | 0.508 |
| 10×5 ΔAUPRC | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auprc/value` | +0.085 |
| 10×5 ΔAUPRC CI | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auprc/ci95` | [+0.017, +0.146] |
| 10×5 Brier, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/brier/value` | 0.2008 |
| 10×5 Brier, logistic | `analysis/out/metrics_meps.json` → `metrics/logistic/brier/value` | 0.1921 |
| 10×5 Brier, forest | `analysis/out/metrics_meps.json` → `metrics/forest/brier/value` | 0.1796 |
| 10×5 ΔBrier | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/brier/value` | -0.021 |
| 10×5 ΔBrier CI | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/brier/ci95` | [-0.035, -0.007] |
| 10×5 log loss, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/log_loss/value` | 0.606 |
| 10×5 log loss, logistic | `analysis/out/metrics_meps.json` → `metrics/logistic/log_loss/value` | 0.570 |
| 10×5 log loss, forest | `analysis/out/metrics_meps.json` → `metrics/forest/log_loss/value` | 0.539 |
| 10×5 Δlog loss | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/log_loss/value` | -0.067 |
| 10×5 Δlog loss CI | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/log_loss/ci95` | [-0.107, -0.026] |
| Calibration slope, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/cal_slope/value` | 0.45 |
| Calibration slope CI, baseline | `analysis/out/metrics_meps.json` → `metrics/baseline/cal_slope/ci95` | [0.25, 0.69] |
| Calibration slope, logistic | `analysis/out/metrics_meps.json` → `metrics/logistic/cal_slope/value` | 1.09 |
| Calibration slope, forest | `analysis/out/metrics_meps.json` → `metrics/forest/cal_slope/value` | 1.10 |
| Calibration slope CI, forest | `analysis/out/metrics_meps.json` → `metrics/forest/cal_slope/ci95` | [0.82, 1.44] |
| Alert cut-off | `src/data/metrics.json` → `tiers/alert` | 43% |
| Alert tier observed rate | `src/data/metrics.json` → `tiers/tiers/0/observedRate` | 57% |
| Alert tier share of events | `src/data/metrics.json` → `tiers/tiers/0/shareOfAllPositives` | 39% |
| Watch cut-off | `src/data/metrics.json` → `tiers/watch` | 29% |
| Watch tier observed rate | `src/data/metrics.json` → `tiers/tiers/1/observedRate` | 30% |
| Ok tier observed rate | `src/data/metrics.json` → `tiers/tiers/2/observedRate` | 19% |
| Held-out alert | `src/data/metrics.json` → `heldoutStatusMix/alert` | 40 |
| Held-out watch | `src/data/metrics.json` → `heldoutStatusMix/watch` | 43 |
| Held-out ok | `src/data/metrics.json` → `heldoutStatusMix/ok` | 116 |
| Six prior-use features alone | `runs/autoresearch/round-1.json` → `results[candidate="lr_l2 | 0.697 |
| Within prior-use group ΔAUROC | `runs/autoresearch/stratified.json` → `prior/search/delta` | +0.094 |
| Within prior-use group CI | `runs/autoresearch/stratified.json` → `prior/search/ci95` | [-0.002, +0.206] |
| First event n | `src/data/metrics.json` → `firstEvent/n` | 326 |
| First event events | `src/data/metrics.json` → `firstEvent/events` | 70 |
| First event AUROC, search | `src/data/metrics.json` → `firstEvent/aurocModel` | 0.653 |
| First event AUROC, baseline | `src/data/metrics.json` → `firstEvent/aurocBaseline` | 0.634 |
| First event ΔAUROC | `src/data/metrics.json` → `firstEvent/deltaAuroc` | +0.019 |
| First event ΔAUROC CI | `src/data/metrics.json` → `firstEvent/deltaCi95` | [-0.065, +0.103] |
| Prior acute care rate with | `src/data/metrics.json` → `plainFactors/0/withFactor/rate` | 46% |
| Prior acute care rate without | `src/data/metrics.json` → `plainFactors/0/without/rate` | 21% |
| Prior acute care ratio | `src/data/metrics.json` → `plainFactors/0/rateRatio` | 2.1× |
| Age 75+ rate with | `src/data/metrics.json` → `plainFactors/1/withFactor/rate` | 44% |
| Age 75+ rate without | `src/data/metrics.json` → `plainFactors/1/without/rate` | 24% |
| Fairness AUROC, female | `src/data/metrics.json` → `fairness[group="Female"]/auroc` | 0.72 |
| Fairness AUROC, male | `src/data/metrics.json` → `fairness[group="Male"]/auroc` | 0.70 |
| Fairness AUROC, any private | `src/data/metrics.json` → `fairness[group="Any private"]/auroc` | 0.68 |
| Fairness AUROC, public only | `src/data/metrics.json` → `fairness[group="Public only"]/auroc` | 0.75 |
| Age 75+ O/E | `src/data/metrics.json` → `fairness[group="75+ (85 = top-coded)"]/oe` | 1.15 |
| Age 75+ O/E CI | `src/data/metrics.json` → `fairness[group="75+ (85 = top-coded)"]/oeCi95` | [0.91, 1.37] |
| NH Black AUROC | `src/data/metrics.json` → `fairness[group="NH Black"]/auroc` | 0.48 |
| NH Black AUROC CI | `src/data/metrics.json` → `fairness[group="NH Black"]/aurocCi95` | [0.25, 0.70] |
| NH Black n | `src/data/metrics.json` → `fairness[group="NH Black"]/n` | 47 |
| Synthea Q1 AUROC shared | `analysis/out/synthea.json` → `q1WithinSynthea/aurocShared` | 0.671 |
| Synthea Q1 AUROC shared + clinical | `analysis/out/synthea.json` → `q1WithinSynthea/aurocSharedPlusClinical` | 0.670 |
| Synthea Q1 Δ | `analysis/out/synthea.json` → `q1WithinSynthea/deltaAuroc` | -0.001 |
| Synthea Q1 Δ CI | `analysis/out/synthea.json` → `q1WithinSynthea/deltaAurocCi95` | [-0.008, +0.007] |
| Synthea stage missing | `analysis/out/synthea.json` → `q1WithinSynthea/stageMissingShare` | 86% |
| Synthea Q2 transport AUROC | `analysis/out/synthea.json` → `q2Transport/aurocInMeps` | 0.686 |
| Synthea Q2 transport CI | `analysis/out/synthea.json` → `q2Transport/ci95` | [0.634, 0.740] |
| Synthea Q2 O/E | `analysis/out/synthea.json` → `q2Transport/oe` | 1.02 |
| Synthea Q2 Δ vs forest | `analysis/out/synthea.json` → `q2Transport/vsMepsModel/deltaAuroc` | -0.026 |
| Synthea Q2 Δ CI | `analysis/out/synthea.json` → `q2Transport/vsMepsModel/ci95` | [-0.068, +0.013] |
| Synthea Q3 burden ΔAUROC | `analysis/out/synthea.json` → `q3Increment/transfer_clinical_burden/delta/auroc/value` | +0.004 |
| Synthea Q3 burden ΔAUROC CI | `analysis/out/synthea.json` → `q3Increment/transfer_clinical_burden/delta/auroc/ci95` | [-0.003, +0.012] |
| Synthea Q3 prior ΔAUROC | `analysis/out/synthea.json` → `q3Increment/transfer_prior_logit/delta/auroc/value` | +0.004 |
| Synthea Q3 prior ΔAUROC CI | `analysis/out/synthea.json` → `q3Increment/transfer_prior_logit/delta/auroc/ci95` | [-0.002, +0.010] |
| Synthea Q3 MEPS-only reference | `analysis/out/synthea.json` → `q3Increment/baseline/auroc/value` | 0.663 |
| Synthea-prior candidate (round 3) | `runs/autoresearch/round-3.json` → `results[candidate="synthea_prior | 0.692 |
| Submission (199 rows) | `submission/heldout_predictions.csv` | identical to the committed file (max \|Δ\| < 1e-9) |

Four README strings disagree with the committed outputs in the last digit (they are README typos, not reproduction differences); the check lists them as
"README differs from the committed output too": the 10×5 Δ log loss CI upper bound (README -0.027, output -0.026), the male AUROC (README 0.71, output 0.70),
and the two Synthea Q3 ΔAUROC CIs (README [-0.002, +0.011] and [-0.003, +0.010]; output [-0.003, +0.012] and [-0.002, +0.010]).

## 4. E2E against the live Worker

```bash
npm ci
npm run e2e        # every endpoint of https://c1-acute-risk.zay-259.workers.dev, the submission format, the API contract and display limits
```

It writes `runs/e2e-<UTC time>.json` and `runs/e2e-latest.json` (each check with pass/fail, plus the captured responses). `npm run contract` turns that file into CONTRACT.md.
To test a Worker built from your own run, `npm run deploy` to your own account and pass its URL: `node scripts/e2e.mjs https://<your-worker>.workers.dev`.

## 5. Fresh-clone proof

`runs/reproduce-<UTC stamp>.md` records a run of `scripts/reproduce.sh --full` from a fresh clone: where it ran, the commit, the tool versions, the per-step times,
the number table and the git diff against the commit. `scripts/reproduce-cf/` is the Cloudflare Container runner used for it.
