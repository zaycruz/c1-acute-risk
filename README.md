# C1 Care Team Risk: who may need acute care in 2018?

eMerge Hackathon Challenge 1. From 2017 MEPS survey answers by real cancer survivors, predict who will have an
**ER visit or hospital stay in 2018**. Name the factors linked to that risk. Test honestly whether the synthetic
clinical records (Synthea, different people, no shared key) add anything. The results are served as the C1 module of the Coach Console.

- Live: https://c1-acute-risk.zay-259.workers.dev (demo page) · API contract: [CONTRACT.md](CONTRACT.md)
- Submission: [`submission/heldout_predictions.csv`](submission/heldout_predictions.csv) (`ID,predicted_risk`, 199 rows in template order)
- Latest E2E artifact: `runs/e2e-latest.json` (31/31 checks), `runs/page-check-latest.json`, `runs/demo-page-*.png`

## Results (out-of-fold, 466 development survivors, 134 events)

**Same-or-better ranking, significantly better probabilities.** The final model is a sigmoid-calibrated random forest
(300 trees, min leaf 10) on 16 features: 2017 care use (ER, hospital stays and nights, office, outpatient, home health,
prescriptions, total spending, missed work days), age, physical and mental health scores, distress, depression screen and
self-rated health. A model search over 48 candidates (`analysis/autoresearch.py`, log in `runs/autoresearch/log.md`)
chose it. It replaces our first submission, an L2 logistic regression on 34 domain features.

**The honest estimate is the nested one.** We re-ran the whole search inside each of 10 outer folds, so the scored model never saw its test fold:

| Nested CV (10 outer folds) | Search procedure (picked the forest in 6 of 10 folds) | Baseline (organisers') | Difference [95% CI] |
|---|---|---|---|
| AUROC | **0.711** | 0.672 | +0.039 [-0.015, +0.091], not significant (P(better) 0.93) |
| Log loss (lower = better) | **0.539** | 0.606 | -0.067 [-0.115, -0.020], **significant** |
| Events caught in the top fifth (of 134) | **52** | 45 | |
| Risk called ≥ 50% that came true | **67%** of 55 calls | 49% of 73 calls | |

Against our first submission: AUROC +0.034 [-0.001, +0.066], log loss -0.027 [-0.043, -0.009].

The same 10×5 repeated CV as before scores the final model after selection, which is slightly optimistic:

| 10×5 CV | Baseline | Previous (logistic) | **Final (forest)** | Forest vs baseline (paired) |
|---|---|---|---|---|
| AUROC | 0.659 [0.603, 0.718] | 0.666 | **0.713** [0.662, 0.764] | +0.053 [-0.001, +0.105] |
| AUPRC | 0.423 | 0.438 | **0.508** | +0.085 [+0.017, +0.146] |
| Brier | 0.2008 | 0.1921 | **0.1796** | -0.021 [-0.035, -0.007] |
| Log loss | 0.606 | 0.570 | **0.539** | -0.067 [-0.107, -0.027] |
| Calibration slope (1 = ideal) | 0.45 [0.25, 0.69] | 1.09 | **1.10** [0.82, 1.44] | |

Why the ranking gain is not significant: at n = 466 with 134 events an AUROC gain must be about +0.056 to clear a 95% CI.
The held-out set (about 57 events) has an AUROC standard error of about 0.04, so a better model can still score lower there by chance.
The probability gain is the part we can prove. The baseline's top fifth predicts 61% risk and 47% of those survivors had acute care. Ours predicts 54% and 56% had it.

**Risk tiers** (out-of-fold): alert is 43% or more (top fifth; 57% had acute care, 39% of all events). Watch is 29–43% (30%). Ok is below 29% (19%).
The held-out roster has 40 alert, 43 watch and 116 ok.

**The clinical insight: prior care use dominates.** Six prior-use features (ER visits, hospital stays, prescriptions, office visits,
home health and age) alone reach AUROC 0.697. Survey symptoms, factor scores, a Synthea prior, monotone boosting, bagging and stacking
do not move the ceiling past about 0.71. The best predictor of acute care next year is heavy care this year.
That marks need; it is not a lever. Within the prior-use group the search procedure ranks better than the baseline
(+0.094 [-0.002, +0.206]). The baseline mostly separates "had acute care in 2017" from "did not".

**Proposed alternative target: the first acute event.** Finding last year's repeat users is easy. Prevention needs the *first* event.
Among the 326 survivors with no ER visit or hospital stay in 2017 (70 had a first one in 2018), the forest ranks at AUROC 0.662
vs the baseline's 0.616: +0.046 [-0.036, +0.123] (`/api/c1/metrics` → `firstEvent`). We suggest the care team uses this as the target for outreach.

**Factors.** TreeSHAP on the forest gives each survivor's drivers on the calibrated log-odds scale (`analysis/explain.py`).
Mean impact, largest first: spending, age, hospital nights, prescription fills, office visits, ER visits, mental health score (low raises risk),
hospital stays, physical health score (low raises risk) and outpatient visits. The observed 2018 rate with the 2017 factor vs without it:
prior ER visit or hospital stay 46% vs 21% (2.1×). Age 75+ 44% vs 24%. Positive depression screen 47% vs 27%.
Physical health score under 40: 40% vs 23%. 20+ prescription fills: 37% vs 22%. Fair or poor self-rated health: 42% vs 26%.
Distress (K6 5+): 36% vs 27%. **Financial hardship and cost-related delays showed no association (about 1.0×)**, and neither did current treatment.
These are associations. The care team can act on symptoms, distress and depression, medication burden and care coordination.
These become the per-survivor recommendations, one per kind of driver.

**Fairness** (out-of-fold, `/api/c1/metrics` → `fairness`):
- Similar by sex (AUROC 0.72 F, 0.71 M) and insurance (0.68 private, 0.75 public-only).
- Age 75+ is no longer clearly under-predicted: observed/expected 1.15 [0.91, 1.37]. With the logistic model it was 1.27 [1.00, 1.53].
- **Weak ranking for NH Black survivors**: AUROC 0.48 [0.25, 0.70], n = 47, 11 events. This is a flag, not a pass, and the survivor panel warns about it.
- **Too small to judge** (n < 30 or < 10 events): Hispanic (28), NH Asian (6), NH other (14), uninsured (7), colon (23), lung (20).

## Do the clinical records add anything? No meaningful gain, but the shared risk pattern transports

There is no key, so we never match individuals. A join on age, sex, race and cancer type would mostly match the wrong people.
In MEPS 7% of survivors are Hispanic; in Synthea 54% are. We asked three questions and set pass criteria before running them (`analysis/synthea.py`):

1. **Inside Synthea** (660 synthetic patients, 4,033 person-years; predictors to Dec 31 of year Y, outcome = emergency/inpatient
   encounter in Y+1; CV grouped by patient): do clinical-only features add AUROC over the variables both sources share?
   The clinical-only features are stage, metastasis, comorbidities, opioids, kidney function, obesity and years since diagnosis.
   **No: 0.671 → 0.670, Δ -0.001 [-0.008, +0.007].** Stage is missing in 86% of person-years.
2. **Transport:** we fitted a Synthea model on shared variables only and applied it unchanged to the real MEPS development survivors.
   **AUROC 0.686 [0.634, 0.740], observed/expected 1.02.** Paired against the final MEPS model's out-of-fold 0.713: Δ -0.026 [-0.068, +0.013], a tie.
   This is our strongest integration result. A risk pattern on shared variables (prior acute care, age, insurance), learned from synthetic Miami records,
   ranks real national survivors as well as a model fitted on the survey itself, and is calibrated.
3. **Increment in MEPS** (same repeated CV, paired against the MEPS-only logistic, because a linear model takes a Synthea score as one feature):
   - The clinical-burden score is the clinical part of the Synthea model, projected onto shared variables. ΔAUROC +0.004 [-0.002, +0.011], ΔBrier -0.0012 [-0.0022, -0.0002].
   - The Synthea prior gives ΔAUROC +0.004 [-0.003, +0.010].
   - The MEPS-only reference in Q3 is 0.663, not 0.666, because it uses a wider C grid.
   - Shrunken stratum features (age band × sex × cancer type; with and without Hispanic; cancer type only) give ΔAUROC -0.006 to -0.003.
     Sensitivity: the finer strata get worse, and 7–8 aligned development survivors fall in strata with fewer than 10 Synthea person-years.

**What this can show:** the simulation adds no clinical-detail signal, even about itself, and adds no clear predictive value to the survey.
**What it cannot show:** whether *real* stage or comorbidity data would help these patients. Every Synthea-derived feature
is a function of variables MEPS already has, so at best it acts as a prior. **We did not align** MEPS survivors who have only skin,
melanoma, uterine, cervical, bladder, lymphoma or "other" cancers (269 of 466 in the development set), because Synthea has only breast, colon, lung and prostate cancer.
The submission uses a MEPS-only model. A Synthea-prior candidate was tried in the model search (AUROC 0.692) and lost to the forest.

## Method

- **Features** (`analysis/features.py`): 34 survey-domain features with missing indicators. MEPS `-1` (skip) on a yes/no item
  means the gate answer was "no". `-7/-8/-9` are missing. The financial-toxicity and cost-delay items are counts.
  Utilisation is log-transformed. Only the 2017 file feeds the model. From the 2018 file we read only `ID` and the outcome,
  because it reuses names such as `VPCS42` and `K6SUM42` for 2018 measures. An assert guards against 2018 columns.
- **Model:** sigmoid-calibrated random forest on the 16 features in `final_features()` (`analysis/features.py`), with missing indicators.
  The model search and its nested CV are in `analysis/autoresearch.py` (`--round nested`). Explanations: TreeSHAP per calibration fold,
  multiplied by the fold's sigmoid slope, so each contribution is exact on that fold's calibrated log-odds; we report the mean over folds.
- **Validation:** 10× repeated stratified 5-fold CV, one row per survivor. The baseline and every comparator run on the same folds.
  Out-of-fold predictions are averaged over repeats. 95% CIs come from a 2,000-sample patient bootstrap, and differences are paired.
- **Held-out:** the model is refitted on all 466 development survivors and predicts the 199 held-out IDs. The E2E checks the file format.

## Run it

Use short-lived commands only; nothing stays running. The data is not committed: copy it in first.

```bash
mkdir -p data && cp -R ~/Downloads/Challenge_1/meps data/ && cp -R ~/Downloads/Challenge_1/synthea data/
uv venv .venv && uv pip install --python .venv/bin/python pandas scikit-learn numpy pyarrow shap
npm install
npm run build:data      # train.py (about 4 min) -> synthea.py (about 1 min) -> export.py; writes submission/ and src/data/
npm run typecheck && npm run deploy
npm run e2e             # hits every endpoint and validates the submission; writes runs/e2e-<time>.json
npm run e2e:page        # headless browser check (desktop and phone); writes runs/demo-page-*.png
npm run contract        # regenerates CONTRACT.md from the latest E2E responses
```

The seeds are fixed (`SEED = 20261017`), so a rerun gives the same numbers.

## 2-minute demo story

1. **Problem (15 s).** Care teams want to call survivors *before* the ER. We have only last year's survey.
2. **Roster (30 s).** Open the page. The 199 held-out survivors are sorted: 40 alert, 43 watch, 116 ok. Click the top alert
   (S71188550: 85, 26 nights in hospital in 2017). The evidence lists this person's SHAP drivers. The recommendations split into
   care team, coach and survivor ("call the team first").
3. **Can we trust the numbers? (40 s)** Look at the model card: "same-or-better ranking, significantly better probabilities".
   Nested CV says AUROC 0.711 vs 0.672 (not significant) and log loss significantly better. When the model says 50%+, it is right 67% of the time; the baseline is right 49%.
4. **The insight (20 s).** Heavy care this year predicts acute care next year; nothing else moves the ceiling. So we propose the harder target: the *first* acute event (0.662 vs 0.616).
5. **Fairness and clinical records (15 s).** It holds by sex and insurance; NH Black ranking is weak and flagged. We did not fake a join: clinical detail adds nothing even inside Synthea.

## Caveats

- These are associations, not causes. Nothing here shows that acting on a factor prevents acute care.
- The data is small: 466 development survivors and 134 events. The judges' held-out set has about 57 events.
- MEPS is a national sample; the sample weights are not used, so the results describe this sample, not the US population. Age is top-coded at 85.
- Synthea is synthetic. Nothing from it is evidence about real patients. The Synthea year (Y → Y+1, 2015–2025) is simulated time, not 2017–18.
- In `factors[]`, `meanAbsLogit` is the mean absolute TreeSHAP contribution on the calibrated log-odds scale. It ranks drivers; it is not an effect size.
- The 10×5 CV numbers for the forest are after selection. Quote the nested-CV numbers as the estimate for new survivors.
