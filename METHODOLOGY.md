# Methodology — C1 Care Team Risk (acute-risk random forest)

This module predicts, for each adult cancer survivor in the MEPS 2017 survey, the chance of an ER visit or a hospital stay in 2018.
It ranks the 199 held-out survivors into alert, watch and ok tiers for a care team's call list.
It explains each risk with TreeSHAP drivers and serves the results as the C1 module of the Coach Console (`src/index.ts`, contract in `CONTRACT.md`).
The served model is a sigmoid-calibrated random forest. A 48-candidate model search chose it, and a nested cross-validation of that search gives the honest estimate.

**Where the numbers live**

- `README.md`: the headline results, fairness, Synthea, caveats.
- `REPRODUCE.md`: the reproduce command, the seeds, the pinned dependencies, and a table that maps each README number to a file and key.
- `runs/autoresearch/log.md`, `runs/autoresearch/round-{1,2,3}.json`: the model search, round by round.
- `runs/autoresearch/round-nested.json`, `runs/autoresearch/round-nested-interpretable.json`: nested CV of the search.
- `runs/autoresearch/stratified.json`: the within-prior-use-group check.
- `analysis/out/metrics_meps.json`: the 10×5 CV metrics with CIs (baseline, first submission, final forest).
- `analysis/out/fairness_mitigation.json`: the pre-registered fairness mitigation test.
- `analysis/out/synthea.json`: the Synthea questions Q1–Q3.
- `src/data/metrics.json`: what `/api/c1/metrics` serves (`servedModel`, `modelSearch`, `tiers`, `fairness`, `subgroupAt50`, `firstEvent`, `alertBudget`).
- `runs/reproduce-check.md`, `runs/reproduce-2026-10-17T18-25-37Z.md`, `runs/reproduce-2026-10-17T17-16-07Z.md`: the number check and the fresh-clone runs.

---

## 1. Question and target

- Question: from a survivor's 2017 MEPS answers, what is the chance of acute care in 2018?
- Target: `outcome_acute_care_2018` = any ER visit or hospital stay in 2018. The horizon is one calendar year (2018), predicted from data up to the end of 2017.
- The API's `updatedAt` is the as-of date of the data (end of 2017), not the build time.
- The model predicts a whole year. An alert means one outreach call within that year, not a same-day emergency. Same-day needs come from fixed red-flag rules (`analysis/export.py`, `red_flags`), not from the model.
- The task also asks for the factors linked to risk, and for an honest test of whether the synthetic Synthea records add anything (section 8).

Source: `README.md`, `analysis/train.py` (module docstring and `out["outcome"]`), `CONTRACT.md`.

## 2. Data

| Item | Value | Source |
|---|---|---|
| Data source | Organisers' Challenge 1 release: an MEPS extract built from the public AHRQ MEPS 2017 and 2018 full-year files, filtered and recoded by the organisers, plus Synthea CSVs | `data/README.md` |
| Real or synthetic | MEPS: real survey respondents. Synthea: synthetic patients, used only in the Synthea analysis and one search candidate | `data/README.md`, `README.md` |
| Unit | One row per survivor (person). Synthea analysis: person-years | `analysis/train.py` docstring, `README.md` |
| Development set | 466 survivors, 134 events | `README.md`, `analysis/out/metrics_meps.json` (`n_dev`, `positives_dev`) |
| Held-out set | 199 survivors (outcome unknown to us), about 57 expected events | `README.md`, `src/data/metrics.json` (`servedModel.expectedHeldout`) |
| Files that feed the model | `meps/meps2017_survivors.csv` only. From `meps/meps2018_followup_dev.csv` the code reads `ID` and the outcome | `data/README.md` |
| Data integrity | `data/SHA256SUMS` lists the 13 files the code reads; `scripts/reproduce.sh` stops if a hash differs | `data/README.md`, `scripts/reproduce.sh` |

Exclusions and scope:

- The organisers' release defines the survivor population and the dev / held-out split. The code drops no development survivor. `analysis/train.py` (`main`) asserts that held-out and dev IDs do not overlap.
- MEPS sample weights are not used. The results describe this sample, not the US population. Age is top-coded at 85.
- The Synthea panel (`analysis/synthea.py`, `build_panel`) keeps only patients with a cancer diagnosis. It keeps person-years from the diagnosis year (2015 at the earliest) to 2024, with the outcome in Y+1. It drops person-years with no encounter in Y and in Y+1 ("no way to observe them"), and person-years with age under 18.
- In the Synthea alignment, MEPS survivors with only skin, melanoma, uterine, cervical, bladder, lymphoma or "other" cancers (269 of 466 in the development set) are not aligned to strata, because Synthea has only breast, colon, lung and prostate cancer.
- The data is sponsor data and is not committed. Per-person out-of-fold files are keyed by MEPS public-use IDs; no re-identification is made or allowed.

Source: `data/README.md`, `README.md`, `REPRODUCE.md`, `analysis/synthea.py`, `analysis/out/synthea.json` (`strata`).

## 3. Features

Code: `analysis/features.py`.

| Feature set | Function | Content | Used by |
|---|---|---|---|
| Baseline | `baseline_features` | The organisers' `baseline_model.py` features, verbatim | Baseline |
| Domain (34 features) | `domain_features` | Demographics, insurance, income, 2017 care use, VR-12, K6, PHQ-2, symptoms, treatment, financial toxicity and cost-delay counts, cancer types, "no questionnaire" flag | First submission (L2 logistic) and most search candidates |
| Final (16 features) | `final_features` | `COMPACT` (11) + 5 raw 2017 use items in `RAW_USE` (log1p) | Served forest |

The 16 final features: 2017 care use (ER visits, hospital stays and nights, office visits, outpatient visits, home health, prescription fills, total spending, missed work days), age, physical and mental health scores, distress (K6), depression screen (PHQ-2) and self-rated physical health. The pipeline adds missing indicators (`SimpleImputer(add_indicator=True)`).

Coding rules (`analysis/features.py` docstring, `num`, `yes`, `count_yes`):

- MEPS `-1` (skip) on a yes/no item means the gate answer was "no", so it counts as "no".
- `-7`, `-8`, `-9` are missing.
- Financial-toxicity and cost-delay items are counts. Utilisation is log-transformed.

Leakage controls:

- Only the 2017 file feeds the model. The 2018 file reuses names such as `VPCS42` and `K6SUM42` for 2018 measures, so the code reads only `ID` and the outcome from it.
- `analysis/train.py` (`main`) asserts that no feature column ends in `18` or `18X`.
- `analysis/autoresearch.py` (`load`) reads the 2018 counts (`ERTOT18`, `IPDIS18`, `IPNGTD18`, `TOTEXP18`) only as auxiliary training targets for the count and auxiliary-target candidates (`Count`, `AuxTarget`). They are never predictors. An assert checks that the count target matches the outcome.
- Fairness groups come from 2017 values only (`subgroups`).
- One exception to note: the factor-analysis feature sets (`prior_fa`, `compact_fa` in `autoresearch.py`, `featuresets`) fit the factor analysis on the 2017 answers of all 717 survivors, held-out included, with no outcomes. These sets are only in round-3 candidates. The served model does not use them.

Source: `README.md` (Method), `analysis/features.py`, `analysis/train.py`, `analysis/autoresearch.py`.

## 4. Split

- Validation is 10× repeated stratified 5-fold CV on the 466 development survivors, one row per survivor (`analysis/train.py`, `RepeatedStratifiedKFold`, `N_SPLITS, N_REPEATS = 5, 10`). Each survivor appears once per repeat, so no person is in train and test of the same fold.
- Every model, including the organisers' baseline, runs on the same folds. Out-of-fold predictions are averaged over the 10 repeats.
- The search rounds use 5×5-fold CV (`analysis/autoresearch.py`, `score_candidate`).
- Nested CV (`analysis/autoresearch.py`, `nested`): 5 outer folds × 2 repeats = 10 outer folds. Inside each outer training set, every candidate gets a 5-fold CV score on log loss. The best candidate is refitted and predicts the outer fold.
- Inner tuning: logistic penalties are chosen by `LogisticRegressionCV` inside each training fold. Sigmoid calibration uses its own 5-fold CV inside each training fold (`CalibratedClassifierCV(cv=5)`). Nothing is tuned on the scored fold.
- There is no temporal holdout inside the development set: predictors are from 2017 and the outcome is from 2018 for every survivor. The held-out 199 survivors have no labels for us. The final model is refitted on all 466 survivors and predicts them.
- Synthea Q1 uses CV grouped by patient (`StratifiedGroupKFold`), so person-years of one patient never split across train and test.

**How tuning was protected, and where it was not.**
Hyperparameters and calibration are fitted inside training folds only. The forest's settings (300 trees, min leaf 10) are the fixed defaults of the `rf` factory in `analysis/autoresearch.py`; they were not tuned. The held-out labels were never seen.
But the search was not blind. The round-2 candidates were "chosen after reading round 1" and round 3 came "after round 2 plateaued", all on the same 466 survivors (`analysis/autoresearch.py` comments, `runs/autoresearch/log.md`). The 10×5 CV numbers for the forest are therefore after selection and "slightly optimistic" (`README.md`). The nested CV puts the rounds 1–2 selection (37 candidates) inside the evaluation. It cannot remove the human choice of which round-2 candidates to write. Round 3 (11 new candidates) is not inside the nested run: it "was scored afterwards against its winner (rf|compact_raw_use) and did not beat it" (`analysis/autoresearch.py`, `main`).
The README says to quote the nested-CV numbers as the estimate for new survivors.

Source: `README.md`, `analysis/train.py`, `analysis/autoresearch.py`, `analysis/synthea.py`.

## 5. Model and selection

### 5.1 The 48-candidate search

Code: `analysis/autoresearch.py` (`ROUND1`, `ROUND2`, `ROUND3`, `run_round`). Log: `runs/autoresearch/log.md`.

| Round | Candidates | CV | Content | Source |
|---|---|---|---|---|
| 1 (broad) | 24 | 5×5-fold | L1/L2/elastic-net logistic, spline logistic, gradient boosting (depth 1–3), random forest, extra trees, Poisson GLM and GBM, averages; baseline included as reference | `runs/autoresearch/log.md` |
| 2 (refine) | 15 | 5×5-fold | Small feature sets around round 1's winners, incl. `rf\|compact_raw_use` | `runs/autoresearch/log.md` |
| 3 ("outside the box") | 14 | 5×5-fold | Synthea prior, auxiliary 2018 targets, factor-analysis features, monotone boosting, bagging, stacking | `runs/autoresearch/log.md` |
| All | 48 candidates in 3 rounds | | | `README.md` |

Each round includes the baseline and the first submission as references, so round counts overlap. Candidates are ranked by log loss.

Best per round (`runs/autoresearch/log.md`):

| Round | Best candidate | AUROC | Log loss | ΔAUROC vs baseline [95% CI] | ΔLog loss vs baseline [95% CI] |
|---|---|---|---|---|---|
| 1 | `spline_lr\|compact` | 0.700 | 0.5464 | +0.044 [-0.003, +0.091] | -0.0656 [-0.1058, -0.0294] |
| 2 | `rf\|compact_raw_use` | 0.711 | 0.5400 | +0.054 [+0.000, +0.106] | -0.0719 [-0.1124, -0.0318] |
| 3 | `rf\|compact_raw_use` (carried over) | 0.711 | 0.5400 | +0.054 [-0.003, +0.104] | -0.0719 [-0.1133, -0.0295] |

The log's conclusion: the ceiling is "about AUROC 0.70-0.71 out-of-sample. Six prior-use features alone reach 0.697; survey PROs, factor scores, richer 2018 targets, a Synthea prior, monotone boosting, bagging and stacking do not move it."

### 5.2 Nested CV of the search

Code: `analysis/autoresearch.py` (`nested`); output `runs/autoresearch/round-nested.json`.

- Pool: the 37 candidates of rounds 1–2.
- Picks per outer fold: `rf|compact_raw_use` 6, `spline_lr|prior_use` 3, `poisson_glm|compact` 1.
- The scored "search procedure" is the pick of each outer fold, so it is not one fixed model.

| Nested CV, 466 survivors, 134 events | Search procedure | Baseline | Difference [95% CI] |
|---|---|---|---|
| AUROC | 0.711 | 0.672 | +0.039 [-0.015, +0.091], not significant (P(better) 0.93) |
| Log loss (lower = better) | 0.539 | 0.606 | -0.067 [-0.115, -0.020], significant |
| Events caught in the top fifth (of 134) | 52 | 45 | |
| Risk called ≥ 50% that came true | 67% of 55 calls | 49% of 73 calls | |

Against the first submission (L2 logistic on 34 domain features): AUROC +0.034 [-0.001, +0.066], log loss -0.027 [-0.043, -0.009].

A second nested run kept only interpretable models (linear and spline GLMs, a restriction stated before the run): AUROC 0.692; vs baseline dAUROC +0.020 [-0.030, +0.070], d log loss -0.0523 [-0.0975, -0.0052].

Source: `README.md`, `runs/autoresearch/log.md`, `runs/autoresearch/round-nested.json`, `src/data/metrics.json` (`modelSearch`).

### 5.3 The served model

- Sigmoid-calibrated random forest: 300 trees, `min_samples_leaf=10`, `max_features="sqrt"`, `random_state=0`, after a median imputer with missing indicators (`analysis/train.py`, `make_models()["forest"]`).
- Inputs: the 16 features of `final_features()` (the search's `compact_raw_use` set).
- It replaces the first submission, an L2 logistic regression on 34 domain features.

### 5.4 Calibration

- Method: `CalibratedClassifierCV(method="sigmoid", cv=5)` inside each training fold (`analysis/train.py`, `make_models`).
- Calibration slope (1 = ideal) is the coefficient of a logistic regression of the outcome on logit(p) (`analysis/train.py`, `cal_intercept_slope`). Its CI comes from the same 2,000-sample bootstrap.
- 10×5 CV: forest 1.10 [0.82, 1.44]; baseline 0.45 [0.25, 0.69]; first submission 1.09. The README reads the baseline's slope as over-confident.
- The baseline's top fifth predicts 61% risk and 47% of those survivors had acute care. The forest's top fifth predicts 54% and 56% had it.
- Calibration curves: 5 quantile bins, observed rate with a Wilson 95% interval (`analysis/train.py`, `calibration_curve`; `src/data/metrics.json` → `calibrationCurve`).

Source: `README.md`, `analysis/out/metrics_meps.json`, `analysis/train.py`.

### 5.5 Explanations

TreeSHAP on each of the 5 calibration folds' forests, multiplied by that fold's sigmoid slope, gives exact contributions on that fold's calibrated log-odds; the mean over folds is reported (`analysis/explain.py`, `contributions`). Contributions rank drivers; they do not reconstruct the risk to the decimal, and `meanAbsLogit` is not an effect size.

Source: `README.md`, `analysis/explain.py`.

## 6. Baseline

- The baseline is the organisers' `baseline_model.py` pipeline, unchanged: median imputer, standard scaler, `LogisticRegression(C=0.3)` on the organisers' features. `analysis/baseline_reference.py` is the release file byte for byte; `analysis/features.py` (`baseline_features`) and `analysis/autoresearch.py` (`baseline_model`) reproduce it.
- Same data, same folds: the baseline runs on the same 10×5 folds in `train.py`, the same 5×5 folds in each search round, and the same 10 outer folds in the nested CV. All differences are paired.
- The baseline has no tuning step of its own (its C is fixed by the organisers). The candidates tune penalties inside training folds. So the comparison is equal in data and folds; it is not an equal tuning budget.

Source: `README.md`, `data/README.md`, `analysis/train.py`, `analysis/autoresearch.py`.

## 7. Metrics with 95% CIs

### 7.1 Headline: calls at 50%+

| Served forest, 10×5 out-of-fold | Forest | Baseline | Difference [95% CI] |
|---|---|---|---|
| Risk called ≥ 50% that came true | 59% [46%, 71%] of 59 calls | 48% of 69 calls | +11 points [-0.2, +23], just short of significant |

The README words the three percentages like this: "59% is how often the served model's 50%+ calls came true. 67% is the same cut for the nested model search. 57% is the acute-care rate in the alert tier (risk 43% or more, the top fifth)."
59% is from the served forest's 10×5 CV after selection. 67% (of 55 calls, baseline 49% of 73) is from the nested search procedure. 57% is a tier rate, not a 50% cut.

Source: `README.md`, `src/data/metrics.json` (`servedModel.callsAt50`, `modelSearch.callsAt50`, `tiers`).

### 7.2 10×5 CV (after selection; slightly optimistic)

| 10×5 CV | Baseline | First submission (logistic) | Final (forest) | Forest vs baseline (paired) |
|---|---|---|---|---|
| AUROC | 0.659 [0.603, 0.718] | 0.666 | 0.713 [0.662, 0.764] | +0.053 [-0.001, +0.105], not significant |
| AUPRC | 0.423 | 0.438 | 0.508 | +0.085 [+0.017, +0.146] |
| Brier | 0.2008 | 0.1921 | 0.1796 | -0.021 [-0.035, -0.007] |
| Log loss | 0.606 | 0.570 | 0.539 | -0.067 [-0.107, -0.026] (nested: [-0.115, -0.020]) |
| Calibration slope (1 = ideal) | 0.45 [0.25, 0.69] | 1.09 | 1.10 [0.82, 1.44] | |

Source: `README.md`, `analysis/out/metrics_meps.json`.

### 7.3 Risk tiers (out-of-fold)

- Alert: risk 43% or more (top fifth of OOF risk); 57% had acute care; 39% of all events.
- Watch: 29–43% (29% is the base rate); 30% had acute care.
- Ok: below 29%; 19% had acute care.
- Held-out roster: 40 alert, 43 watch, 116 ok.
- Code: `analysis/train.py` (`tiers_from_oof`): watch = base rate, alert = 80th percentile of OOF risk.

Source: `README.md`, `src/data/metrics.json` (`tiers`, `heldoutStatusMix`).

### 7.4 How the CIs were computed

| Number | Method | Code |
|---|---|---|
| 10×5 metrics and differences | 2,000-sample patient bootstrap of the averaged OOF predictions; percentile 95% CI; differences paired (same resample for both models) | `analysis/train.py` (`bootstrap`) |
| Search rounds and nested CV differences | 2,000-draw paired bootstrap of ΔAUROC and Δlog loss; P(better) = share of draws in favour | `analysis/autoresearch.py` (`paired`) |
| Calls at 50% (served forest) | 2,000 resamples; the difference uses the same resamples for both models | `analysis/export.py` (`served_model`) |
| Expected held-out AUROC range | 2,000 resamples of 199 development survivors | `analysis/export.py` (`served_model`) |
| Subgroup AUROC and O/E (fairness table) | 500-draw bootstrap within the subgroup | `analysis/train.py` (`fairness`) |
| Fairness mitigation | Paired bootstrap, 2,000 draws, resampled within the group | `analysis/fairness_mitigation.py` (`group_metrics`, `paired`) |
| Sensitivity and PPV at 50% by group | 2,000 resamples within the group; no CI when n < 30 or < 10 events | `analysis/export.py` (`subgroup_thresholds`) |
| Within-prior-use-group ΔAUROC | Paired bootstrap resampled within each group, 2,000 draws, seed 7 | `analysis/stratified.py` |
| First-event ΔAUROC | 2,000-draw bootstrap on the nested OOF | `analysis/export.py` (`first_event`, `_boot_ci`) |
| Synthea Q1 ΔAUROC | Cluster bootstrap by patient, 1,000 draws | `analysis/synthea.py` (`cluster_boot_delta`) |
| Calibration-bin observed rates | Wilson interval | `analysis/train.py` (`calibration_curve`) |

### 7.5 Significant and not significant (the repo's own wording)

- Significant: nested log loss vs baseline, -0.067 [-0.115, -0.020]. 10×5 Brier, log loss and AUPRC vs baseline: CIs exclude zero.
- Not significant: nested AUROC vs baseline, +0.039 [-0.015, +0.091]. 10×5 AUROC vs baseline, +0.053 [-0.001, +0.105].
- Just short of significant: the 50%+ calls gain, +11 points [-0.2, +23].
- Why the ranking gain is not significant: "at n = 466 with 134 events an AUROC gain must be about +0.056 to clear a 95% CI." The README's summary: "Same-or-better ranking, significantly better probabilities."
- On the 199 held-out survivors (about 57 events), expect an AUROC anywhere from 0.63 to 0.79 from chance alone. The held-out AUROC standard error is about 0.04, so a better model can still score lower there by chance.

Source: `README.md`, `src/data/metrics.json` (`servedModel.expectedHeldout`, `modelSearch.powerNote`).

## 8. Robustness and falsification

### 8.1 Real-data checks

- All model training and scoring uses real MEPS survivors. There is no second real dataset: no external MEPS panel, no temporal validation, and no held-out labels. A temporal or external validation is listed as future work.
- The one cross-source test on real data is the Synthea transport (Q2, 8.4): a model fitted only on synthetic records is applied to the real MEPS survivors.
- Held-out input check: each held-out input is compared with the development min–max range; 11 values in total fall outside it (`src/data/metrics.json` → `servedModel.provenance.inputRangeCheck`).

Source: `README.md`, `src/data/metrics.json`.

### 8.2 Is it only prior use? (stratified check)

Code: `analysis/stratified.py`; output `runs/autoresearch/stratified.json`.

| Nested OOF vs baseline | No prior acute care (n = 326, 70 events) | Prior acute care (n = 140, 64 events) | Mean within-group |
|---|---|---|---|
| Search procedure | +0.019 [-0.065, +0.103] | +0.094 [-0.002, +0.206] | +0.056 [-0.008, +0.126] |
| Interpretable procedure | -0.003 [-0.080, +0.079] | +0.058 [-0.036, +0.149] | +0.028 [-0.032, +0.087] |

- No CI excludes zero. Within the prior-use group the CI "just touches 0".
- First acute events (the no-prior group as a target): AUROC 0.653 vs baseline 0.634, +0.019 [-0.065, +0.103], not significant (`src/data/metrics.json` → `firstEvent`).
- The README's reading: "The baseline mostly separates 'had acute care in 2017' from 'did not'." Prior care use marks need; it is not a lever.

Source: `README.md`, `runs/autoresearch/log.md`, `runs/autoresearch/stratified.json`.

### 8.3 Fairness and its mitigation

Subgroups (served forest, out-of-fold; `src/data/metrics.json` → `fairness`; code `analysis/train.py`, `fairness`):

- Similar by sex (AUROC 0.72 F, 0.70 M) and insurance (0.68 private, 0.75 public-only).
- Age 75+: observed/expected 1.15 [0.91, 1.37]. With the logistic model it was 1.27 [1.00, 1.53].
- NH Black: AUROC 0.48 [0.25, 0.70], n = 47, 11 events. "This is a flag, not a pass."
- All survivors other than NH White, pooled: AUROC 0.56 [0.41, 0.71], n = 95, 21 events; observed/expected 0.72 [0.46, 1.01]. NH White: 0.75.
- Hispanic: AUROC 0.64 [0.38, 0.86], n = 28, 7 events: too few to judge.
- Too small to judge (n < 30 or < 10 events): Hispanic (28), NH Asian (6), NH other (14), uninsured (7), colon (23), lung (20).
- Language: the MEPS extract has no interview-language or birthplace field, so Spanish- or Creole-speaking survivors cannot be tested. "That is a gap, not a pass."

Sensitivity and PPV at the 50% cut (`src/data/metrics.json` → `subgroupAt50`; code `analysis/export.py`, `subgroup_thresholds`): all survivors sensitivity 26% [19, 34], PPV 59% [46, 71]. NH Black PPV 20% [0, 50] (2 of 10 flagged had acute care) vs NH White 72% [57, 85]. Age 50–64 PPV 33% [8, 62]. The full table is in `README.md`.

Pre-registered mitigation (`analysis/fairness_mitigation.py`, output `analysis/out/fairness_mitigation.json`):

- The variants and the pass rule were written before running (module docstring). Pass = NH Black AUROC ≥ 0.60, a paired within-group ΔAUROC CI above 0, and overall log loss no more than 0.005 worse.
- The ×3 weight for NH Black survivors was "fixed in advance, not tuned" (`W_BLACK = 3.0`).
- All variants ran on the same 10×5 folds; the code asserts that the "current" variant reproduces `oof.csv`.

| Variant | NH Black AUROC [95% CI, 2,000 draws] | NH Black O/E | Δ within-group AUROC vs current | Overall log loss |
|---|---|---|---|---|
| Current forest | 0.48 [0.25, 0.71] | 0.73 | | 0.539 |
| Group-aware recalibration (cross-fitted) | 0.44 [0.23, 0.67] | 1.00 | -0.040 [-0.079, -0.011] | 0.542 |
| Refit, NH Black weighted ×3 | 0.46 [0.24, 0.69] | 0.79 | -0.018 [-0.068, +0.029] | 0.546 |
| Refit, race/ethnicity as features | 0.47 [0.24, 0.70] | 0.74 | -0.008 [-0.039, +0.016] | 0.539 |
| Both | 0.46 [0.24, 0.69] | 0.81 | -0.020 [-0.077, +0.026] | 0.545 |

- No variant passes. Recalibration fixes the over-prediction (O/E 0.73 → 1.00) but cannot fix ranking.
- The NH Black AUROC CI is [0.25, 0.70] in the fairness table (500 draws, `train.py`) and [0.25, 0.71] in the mitigation table (2,000 draws).
- Decision: keep the model and add a safeguard. An NH Black survivor on the alert or watch list carries `humanCheck.required = true`, and a care-team member reviews the case before outreach. This applies to 4 of 199 held-out survivors. The API lists who the model does not serve yet (`fairnessMitigation.whoThisDoesNotServeYet`).

Source: `README.md`, `analysis/out/fairness_mitigation.json`, `src/data/metrics.json`.

### 8.4 Synthetic vs real data (Synthea)

Code: `analysis/synthea.py`; output `analysis/out/synthea.json`. There is no key between MEPS and Synthea, so no individual is matched. The three questions and their pass rules were set before running (module docstring).

| Question | Result | Pass? |
|---|---|---|
| Q1 Inside Synthea (660 synthetic patients, 4,033 person-years, CV grouped by patient): do clinical-only features add AUROC over the shared variables? | 0.671 → 0.670, Δ -0.001 [-0.008, +0.007]. Stage is missing in 86% of person-years | No |
| Q2 Transport: Synthea model on shared variables only, applied unchanged to the real MEPS development survivors | AUROC 0.686 [0.634, 0.740], O/E 1.02. Paired vs the forest's OOF 0.713: Δ -0.026 [-0.068, +0.013], a tie | AUROC CI above 0.5 |
| Q3 Increment in MEPS (paired against the MEPS-only logistic, same repeated CV) | Clinical-burden score ΔAUROC +0.004 [-0.003, +0.012], ΔBrier -0.0012 [-0.0022, -0.0002]. Synthea prior ΔAUROC +0.004 [-0.002, +0.010]. Shrunken stratum features ΔAUROC -0.006 to -0.003 | No clear AUROC gain; tiny Brier gain |

- The MEPS-only reference in Q3 is 0.663, not 0.666, because it uses a wider C grid.
- Population shift: in MEPS 7% of survivors are Hispanic; in Synthea 54% are.
- A Synthea-prior candidate was tried in the model search (round 3, AUROC 0.692) and lost to the forest. The submission uses a MEPS-only model.
- What this can show: the simulation adds no clinical-detail signal, even about itself. What it cannot show: whether real stage or comorbidity data would help these patients. Every Synthea-derived feature is a function of variables MEPS already has, so at best it acts as a prior.
- Synthea is synthetic. Nothing from it is evidence about real patients. The Synthea year (Y → Y+1, 2015–2025) is simulated time, not 2017–18.

Source: `README.md`, `analysis/out/synthea.json`, `runs/autoresearch/log.md`.

### 8.5 Stress sets and negative controls

No dedicated negative-control or stress set is reported. The closest checks are the stratified and first-event analyses (8.2), the interpretable-only nested run (5.2), and the held-out input range check (8.1).

## 9. Limits

Copied from `README.md` (Caveats and Results):

- These are associations, not causes. Nothing here shows that acting on a factor prevents acute care.
- The data is small: 466 development survivors and 134 events. The judges' held-out set has about 57 events.
- MEPS is a national sample; the sample weights are not used, so the results describe this sample, not the US population. Age is top-coded at 85.
- Synthea is synthetic. Nothing from it is evidence about real patients.
- In `factors[]`, `meanAbsLogit` ranks drivers; it is not an effect size.
- The 10×5 CV numbers for the forest are after selection. Quote the nested-CV numbers as the estimate for new survivors.
- The ranking gain over the baseline is never significant. "No model we tried finds first events much better than the baseline."
- Weak ranking for NH Black survivors; no mitigation worked. The pooled non-NH-White group also ranks weaker (0.56). Hispanic and other small groups are too small to judge. Language cannot be tested.
- Not built (future work in `README.md`): decision-curve / net-benefit analysis, `humanCheck` for every group whose AUROC CI includes 0.5, a subgroup monitoring protocol, a Miami-Dade reweighting check, temporal or external validation, and a first-event call list.

## 10. Reproduce

```bash
git clone https://github.com/zaycruz/c1-acute-risk && cd c1-acute-risk
unzip -q path/to/Challenge_1/meps.zip -d data && unzip -q path/to/Challenge_1/synthea.zip -d data
(cd data && shasum -a 256 -c SHA256SUMS)   # 13 files, all OK
scripts/reproduce.sh          # training, Synthea, nested CV, stratified check, fairness mitigation, export, number check
scripts/reproduce.sh --full   # also re-runs model-search rounds 1-3 (48 candidates)
```

- Dependencies: `uv sync --frozen` from `pyproject.toml` + `uv.lock`, Python 3.14.7 (numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, scipy 1.18.1, shap 0.54.1, and others listed in `REPRODUCE.md`). Every step runs with `uv run --frozen python -I`.
- Seeds: `SEED = 20261017` in `analysis/train.py` and `analysis/autoresearch.py` (the nested outer folds use `SEED + 7`, the inner folds `SEED + 1`); forests use `random_state=0`; `analysis/stratified.py` uses seed 7; `analysis/export.py` bootstraps use seed 20261017.
- Number check: `scripts/check_numbers.py` compares each README number with its file and key, writes `runs/reproduce-check.md`, and exits 1 on a difference. `REPRODUCE.md` section 3 is the table of where each number lives. All 122 README numbers match the committed outputs.
- Fresh-clone runs: `runs/reproduce-2026-10-17T18-25-37Z.md` (commit d84a24f) and `runs/reproduce-2026-10-17T17-16-07Z.md` (commit 4cba328), both on Cloudflare x86_64 Linux. They are a FAIL by the strict rule: 120 of 122 numbers rerun identically; the within-prior-use-group ΔAUROC and its CI differ in the third decimal, and the submission differs by at most 0.001 in predicted risk. On macOS arm64 reruns are exact. The likely cause is BLAS and SIMD floating point; no conclusion changes.
- Runtime: about 43 min with `--full`, about 22 min without (measured on a Cloudflare Container).
- E2E against the live Worker: `npm ci && npm run e2e` writes `runs/e2e-latest.json` (latest: 41 of 41 checks passed, 2026-10-17T18:51:04.812Z). `npm run contract` regenerates `CONTRACT.md`.

Source: `REPRODUCE.md`, `scripts/reproduce.sh`, `runs/reproduce-*.md`, `runs/e2e-latest.json`.

## Generative AI

This module uses no generative model (no LLM, no speech-to-text). All text the API returns (headlines, `evidence`, `recommendations`, `riskWords`, `forAssistant`, `redFlags`) is built from fixed templates in `analysis/export.py`. The `forAssistant` line is written for a separate care-team assistant to use verbatim; that assistant is outside this repo and is not evaluated here.

## Code map

| Step | File (function) |
|---|---|
| Data check and pipeline | `scripts/reproduce.sh` |
| Features | `analysis/features.py` (`baseline_features`, `domain_features`, `final_features`, `subgroups`) |
| Leakage guards | `analysis/train.py` (`main`: 2018-column assert, dev/held-out overlap assert); `analysis/autoresearch.py` (`load`) |
| Baseline | `analysis/baseline_reference.py` (organisers' file); `analysis/train.py` (`make_models`); `analysis/autoresearch.py` (`baseline_model`) |
| Split and 10×5 CV, final fit, submission | `analysis/train.py` (`main`, `make_models`) |
| Model search rounds 1–3 | `analysis/autoresearch.py` (`featuresets`, `ROUND1`, `ROUND2`, `ROUND3`, `run_round`, `score_candidate`) |
| Nested CV | `analysis/autoresearch.py` (`nested`) |
| Calibration and calibration metrics | `analysis/train.py` (`make_models`, `cal_intercept_slope`, `calibration_curve`) |
| Metrics and bootstrap CIs | `analysis/train.py` (`metric_block`, `bootstrap`); `analysis/autoresearch.py` (`paired`) |
| Risk tiers | `analysis/train.py` (`tiers_from_oof`) |
| Explanations | `analysis/explain.py` (`contributions`) |
| Stratified check | `analysis/stratified.py` (`main`, `strat_auc`) |
| Fairness | `analysis/train.py` (`fairness`); `analysis/export.py` (`flag_fairness`, `subgroup_thresholds`) |
| Fairness mitigation | `analysis/fairness_mitigation.py` (`main`, `recalibrate`, `group_metrics`, `paired`) |
| Synthea Q1–Q3 | `analysis/synthea.py` (`build_panel`, `q1_within_synthea`, `cluster_boot_delta`, `main`) |
| API data (served model, nested summary, first event, alert budget, red flags) | `analysis/export.py` (`served_model`, `model_search`, `first_event`, `alert_budget`, `red_flags`, `main`) |
| Number check | `scripts/check_numbers.py` |
| E2E and contract | `scripts/e2e.mjs`, `scripts/contract.mjs` |
