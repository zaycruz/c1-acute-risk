# C1 Care Team Risk: who may need acute care in 2018?

eMerge Hackathon Challenge 1. From 2017 MEPS survey answers by real cancer survivors, predict who will have an
**ER visit or hospital stay in 2018**. Name the factors linked to that risk. Test honestly whether the synthetic
clinical records (Synthea, different people, no shared key) add anything. The results are served as the C1 module of the Coach Console.

- Live: https://c1-acute-risk.zay-259.workers.dev (demo page) · API contract: [CONTRACT.md](CONTRACT.md)
- Submission: [`submission/heldout_predictions.csv`](submission/heldout_predictions.csv) (`ID,predicted_risk`, 199 rows in template order)
- Latest E2E artifact: `runs/e2e-latest.json` (27/27 checks), `runs/page-check-latest.json`, `runs/demo-page-*.png`

## Results (out-of-fold, 466 development survivors, 134 events)

| | Baseline (organisers') | Our model | Difference (paired bootstrap) |
|---|---|---|---|
| AUROC | 0.659 [0.603, 0.718] | **0.666** [0.610, 0.725] | +0.007 [-0.038, +0.050] |
| AUPRC | 0.423 | 0.438 | |
| Brier | 0.2008 | **0.1921** | -0.0087 [-0.0205, +0.0029], better in 92% of resamples |
| Calibration slope (1 = ideal) | 0.45 [0.25, 0.69] (over-confident) | **1.09** [0.68, 1.63] | baseline CI excludes 1 |

The honest summary: **ranking is about the same as the baseline. Calibration is much better.** The baseline's top fifth
predicts 61% risk, but only 47% of those survivors had acute care. Ours predicts 45% and 46% had it. With about 57 events in the
held-out set, a gain of a few AUROC points cannot be told apart from chance, so we did not chase it. A calibrated gradient-boosting comparator scored
AUROC 0.644 with Brier 0.192, so it is not better.

**Risk tiers** (out-of-fold): alert is 36% or more (top fifth; 46% had acute care, 34% of all events). Watch is 29–36% (38%). Ok is below 29% (20%).

**Factors.** The observed 2018 rate with the 2017 factor vs without it:
prior ER visit or hospital stay 46% vs 21% (2.1×). Age 75+ 44% vs 24%. Positive depression screen 47% vs 27%.
Physical health score under 40: 40% vs 23%. 20+ prescription fills: 37% vs 22%. Fair or poor self-rated health: 42% vs 26%.
Distress (K6 5+): 36% vs 27%. **Financial hardship and cost-related delays showed no association (about 1.0×)**, and neither did current treatment.
These are associations. Prior acute care and poor physical function mark need; they are not levers. The care team can act on
symptoms, distress and depression, medication burden and care coordination, and these become the per-survivor recommendations.

**Fairness** (out-of-fold, `/api/c1/metrics` → `fairness`):
- Performance is similar by sex (AUROC 0.68 F, 0.64 M) and insurance (0.64 private, 0.68 public-only).
- **Under-prediction at 75+** (observed/expected 1.27 [1.00, 1.53]).
  The survivor panel warns about this, and about the NH Black result below.
- **Weak ranking for NH Black survivors**: AUROC 0.43 [0.22, 0.65], n = 47, 11 events. The CI includes chance, but this is a flag, not a pass.
- Prostate cancer AUROC 0.55 [0.38, 0.72]. Every subgroup AUROC and observed/expected ratio has a 500-draw bootstrap CI in the API and on the page.
- **Too small to judge** (n < 30 or < 10 events): Hispanic (28), NH Asian (6), NH other (14), uninsured (7), colon (23), lung (20).

## Do the clinical records add anything? No meaningful gain, but the shared risk pattern transports

There is no key, so we never match individuals. A join on age, sex, race and cancer type would mostly match the wrong people.
In MEPS 7% of survivors are Hispanic; in Synthea 54% are. We asked three questions and set pass criteria before running them (`analysis/synthea.py`):

1. **Inside Synthea** (660 synthetic patients, 4,033 person-years; predictors to Dec 31 of year Y, outcome = emergency/inpatient
   encounter in Y+1; CV grouped by patient): do clinical-only features add AUROC over the variables both sources share?
   The clinical-only features are stage, metastasis, comorbidities, opioids, kidney function, obesity and years since diagnosis.
   **No: 0.671 → 0.670, Δ -0.001 [-0.008, +0.007].** Stage is missing in 86% of person-years.
2. **Transport:** we fitted a Synthea model on shared variables only and applied it unchanged to the real MEPS development survivors.
   **AUROC 0.686 [0.634, 0.740], observed/expected 1.02.** Paired against the MEPS model's out-of-fold 0.666: Δ +0.020 [-0.021, +0.063], a tie.
   This is our strongest integration result. A risk pattern on shared variables (prior acute care, age, insurance), learned from synthetic Miami records,
   ranks real national survivors as well as a model fitted on the survey itself, and is calibrated.
3. **Increment in MEPS** (same repeated CV, paired against MEPS-only):
   - The clinical-burden score is the clinical part of the Synthea model, projected onto shared variables. ΔAUROC +0.004 [-0.002, +0.011], ΔBrier -0.0012 [-0.0022, -0.0002].
   - The Synthea prior gives ΔAUROC +0.004 [-0.003, +0.010].
   - The MEPS-only reference in Q3 is 0.663, not 0.666, because it uses a wider C grid.
   - Shrunken stratum features (age band × sex × cancer type; with and without Hispanic; cancer type only) give ΔAUROC -0.006 to -0.003.
     Sensitivity: the finer strata get worse, and 7–8 aligned development survivors fall in strata with fewer than 10 Synthea person-years.

**What this can show:** the simulation adds no clinical-detail signal, even about itself, and adds no clear predictive value to the survey.
**What it cannot show:** whether *real* stage or comorbidity data would help these patients. Every Synthea-derived feature
is a function of variables MEPS already has, so at best it acts as a prior. **We did not align** MEPS survivors who have only skin,
melanoma, uterine, cervical, bladder, lymphoma or "other" cancers (269 of 466 in the development set), because Synthea has only breast, colon, lung and prostate cancer.
The submission uses the MEPS-only model. We chose it before looking at the Synthea results; switching afterwards would be selection.

## Method

- **Features** (`analysis/features.py`): 34 survey-domain features with missing indicators. MEPS `-1` (skip) on a yes/no item
  means the gate answer was "no". `-7/-8/-9` are missing. The financial-toxicity and cost-delay items are counts.
  Utilisation is log-transformed. Only the 2017 file feeds the model. From the 2018 file we read only `ID` and the outcome,
  because it reuses names such as `VPCS42` and `K6SUM42` for 2018 measures. An assert guards against 2018 columns.
- **Model:** L2 logistic regression. Its regularisation is tuned on log loss *inside* each training fold, which is why the shrinkage is strong (C ≈ 0.005).
- **Validation:** 10× repeated stratified 5-fold CV, one row per survivor. The baseline and every comparator run on the same folds.
  Out-of-fold predictions are averaged over repeats. 95% CIs come from a 2,000-sample patient bootstrap, and differences are paired.
- **Held-out:** the model is refitted on all 466 development survivors and predicts the 199 held-out IDs. The E2E checks the file format.

## Run it

Use short-lived commands only; nothing stays running. The data is not committed: copy it in first.

```bash
mkdir -p data && cp -R ~/Downloads/Challenge_1/meps data/ && cp -R ~/Downloads/Challenge_1/synthea data/
uv venv .venv && uv pip install --python .venv/bin/python pandas scikit-learn numpy pyarrow
npm install
npm run build:data      # train.py (about 3 min) -> synthea.py (about 1 min) -> export.py; writes submission/ and src/data/
npm run typecheck && npm run deploy
npm run e2e             # hits every endpoint and validates the submission; writes runs/e2e-<time>.json
npm run e2e:page        # headless browser check (desktop and phone); writes runs/demo-page-*.png
npm run contract        # regenerates CONTRACT.md from the latest E2E responses
```

The seeds are fixed (`SEED = 20261017`), so a rerun gives the same numbers.

## 2-minute demo story

1. **Problem (15 s).** Care teams want to call survivors *before* the ER. We have only last year's survey.
2. **Roster (30 s).** Open the page. The 199 held-out survivors are sorted: 41 alert, 41 watch, 117 ok. Click the top alert
   (S2480BBDE: 11 ER visits and 12 hospital stays in 2017). The evidence lists the drivers. The recommendations split into
   care team (outreach, medication review), coach and survivor ("call the team first").
3. **Can we trust the numbers? (40 s)** Look at the model card. Ranking equals the baseline, and the CIs overlap; we say so.
   Calibration is where we win: a slope of 1.09 [0.68, 1.63] vs 0.45 [0.25, 0.69], and the curve sits on the diagonal. In the alert tier, 46% really had acute care.
4. **Fairness (15 s).** It holds by sex and insurance. Older survivors are under-predicted, and NH Black ranking is weak. We do not pretend about
   the small groups.
5. **Clinical records (20 s).** We did not fake a join. Clinical detail adds nothing even inside Synthea. A Synthea model on shared
   variables does transport to real survivors (0.686), but it gives no clear increment. That is a legitimate finding.

## Caveats

- These are associations, not causes. Nothing here shows that acting on a factor prevents acute care.
- The data is small: 466 development survivors and 134 events. The judges' held-out set has about 57 events.
- MEPS is a national sample; the sample weights are not used, so the results describe this sample, not the US population. Age is top-coded at 85.
- Synthea is synthetic. Nothing from it is evidence about real patients. The Synthea year (Y → Y+1, 2015–2025) is simulated time, not 2017–18.
- In `factors[]`, `ci95` is on the coefficient (log-odds per SD) scale. `oddsRatioPerSd` is its exponential.
