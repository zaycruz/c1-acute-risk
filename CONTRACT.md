# C1 Care Team Risk: API contract

Base URL (deployed): `https://c1-acute-risk.zay-259.workers.dev`. All responses are JSON with `access-control-allow-origin: *`; only `GET` (and `OPTIONS`) are accepted, anything else is `405`.
The examples below are real responses, captured by `npm run e2e` on 2026-10-17T15:49:00.245Z (31/31 checks passed) and turned into this file by `npm run contract`.

Predictions are for the **199 held-out MEPS survivors** (`meps/heldout_ids.csv`): real people, forward predictions, outcome unknown to us.
`survivorId` = `c1-` + the challenge's MEPS `ID`. `updatedAt` is the as-of date of the data (end of 2017), not the build time.

## `GET /api/c1/survivors`: roster tiles

Sorted by `status` (alert, then watch, then ok), then by risk. Status comes from calibrated risk tiers set on out-of-fold development predictions:
`alert` = predicted risk >= 0.43 (top fifth; 57% of development survivors in this tier had acute care),
`watch` = >= 0.29 (the base rate; 30% had it), `ok` = below (19%).
199 survivors (40 alert, 43 watch, 116 ok), showing 3:

```json
[
  {
    "survivorId": "c1-S71188550",
    "displayName": "S71188550 · 85M · prostate",
    "status": "alert",
    "headline": "Acute care risk 70% for 2018 (high), driven by nights in hospital last year",
    "updatedAt": "2017-12-31T00:00:00Z"
  },
  {
    "survivorId": "c1-S13BA2BCD",
    "displayName": "S13BA2BCD · 67F · other",
    "status": "alert",
    "headline": "Acute care risk 65% for 2018 (high), driven by nights in hospital last year",
    "updatedAt": "2017-12-31T00:00:00Z"
  },
  {
    "survivorId": "c1-S9707145E",
    "displayName": "S9707145E · 74F · breast",
    "status": "alert",
    "headline": "Acute care risk 65% for 2018 (high), driven by nights in hospital last year",
    "updatedAt": "2017-12-31T00:00:00Z"
  }
]
```

## `GET /api/c1/survivors/:id`: survivor panel

Contract fields: `survivorId, status, headline, summary, evidence, recommendations, charts, profile, caveat`. Extra fields: `displayName`, `risk` (0..1, identical to the submitted `predicted_risk`), `thresholds`.

- `evidence[]`: `{kind, text}`. The first item (`kind: "model"`) states the risk and what the tier meant on development data. Then up to 4 factors that raise this person's risk and up to 2 that lower it, biggest first. Extra keys: `feature`, `logitContribution` (TreeSHAP contribution on the calibrated log-odds scale, relative to an average survivor; see analysis/explain.py). `kind` is one of `prior-acute-care, medications, care-intensity, physical-function, symptoms, distress, financial-toxicity, access, treatment, support, demographic`.
- `recommendations[]`: `{audience: "coach" | "care-team" | "survivor", text}`. Tier action first, then one per actionable driver. The coach does not diagnose; clinical items go to `care-team`.
- `charts`: `risk` (value, base rate, tier cut-offs), `drivers` (bar chart of logit contributions), `scores` (2017 survey scores, `null` = not answered), `use2017` (counts).
- `caveat`: always present: association not cause, plus a warning when the questionnaire was skipped or the person belongs to a subgroup too small to judge.

```json
{
  "survivorId": "c1-S71188550",
  "displayName": "S71188550 · 85M · prostate",
  "status": "alert",
  "headline": "Acute care risk 70% for 2018 (high), driven by nights in hospital last year",
  "summary": "70% predicted chance of an ER visit or hospital stay in 2018 (average survivor 29%). Status alert: alert from 43%, watch from 29%. Main drivers: $44,900 total health spending in 2017 (median survivor about $6,700); 26 night(s) in hospital in 2017; Age 85 or older (top-coded).",
  "risk": 0.6984,
  "thresholds": {
    "alert": 0.43,
    "watch": 0.29
  },
  "evidence": [
    {
      "kind": "model",
      "text": "Predicted chance of an ER visit or hospital stay in 2018: 70%. Among development survivors in the alert tier, 57% had one."
    },
    {
      "kind": "care-intensity",
      "text": "$44,900 total health spending in 2017 (median survivor about $6,700) (raises risk)",
      "feature": "spending_17",
      "logitContribution": 0.474
    },
    {
      "kind": "prior-acute-care",
      "text": "26 night(s) in hospital in 2017 (raises risk)",
      "feature": "hosp_nights_17",
      "logitContribution": 0.393
    },
    {
      "kind": "demographic",
      "text": "Age 85 or older (top-coded) (raises risk)",
      "feature": "age",
      "logitContribution": 0.369
    },
    {
      "kind": "prior-acute-care",
      "text": "4 hospital stay(s) in 2017 (raises risk)",
      "feature": "hosp_stays_17",
      "logitContribution": 0.227
    }
  ],
  "recommendations": [
    {
      "audience": "care-team",
      "text": "Add to the proactive outreach list: a nurse call in the next 2 weeks and a clear same-day contact route instead of the ER."
    },
    {
      "audience": "care-team",
      "text": "High care use last year: review what drove it and whether one team owns the plan."
    },
    {
      "audience": "care-team",
      "text": "Nights in hospital last year: confirm a discharge follow-up plan and who to call first."
    },
    {
      "audience": "care-team",
      "text": "Older age: a lower bar for proactive check-ins is reasonable."
    },
    {
      "audience": "survivor",
      "text": "If a symptom is getting worse, call your cancer care team first: they can often help the same day without an ER visit."
    }
  ],
  "charts": {
    "risk": {
      "value": 0.6984,
      "baseRate": 0.2876,
      "watchFrom": 0.29,
      "alertFrom": 0.43
    },
    "drivers": [
      {
        "label": "Total health spending in 2017",
        "logitContribution": 0.474
      },
      {
        "label": "Hospital nights in 2017",
        "logitContribution": 0.393
      },
      {
        "label": "Age",
        "logitContribution": 0.369
      },
      {
        "label": "Hospital stays in 2017",
        "logitContribution": 0.227
      }
    ],
    "scores": {
      "physical_score": 35.8,
      "mental_score": 60.9,
      "distress_k6": 0,
      "depression_phq2": 0,
      "pain": 2,
      "fatigue": 1,
      "financial_toxicity": 1,
      "cost_delay": 0
    },
    "use2017": {
      "erVisits": 3,
      "hospitalStays": 4,
      "officeVisits": 17,
      "rxFills": 18
    }
  },
  "profile": {
    "age": 85,
    "sex": "male",
    "raceEthnicity": "NH White",
    "insurance2017": "Any private",
    "cancerTypes": [
      "prostate"
    ],
    "currentTreatment": "no",
    "region": "Midwest",
    "dataSource": "MEPS 2017 survey (real survivor, ID reassigned by organisers)"
  },
  "caveat": "Association, not cause: these factors flag who may need help; changing one is not proven to prevent an ER visit. Risk is from survey answers only (clinical records did not improve it)."
}
```

Unknown id: `404 {"error":"survivor not found"}`.

## `GET /api/c1/metrics`: model card

Top-level keys: `asOf`, `outcome`, `data`, `validation`, `finalModel`, `metrics`, `deltaVsBaseline`, `deltaVsPrevious`, `modelSearch`, `firstEvent`, `calibrationCurve`, `tiers`, `fairness`, `fairnessBaseline`, `factors`, `plainFactors`, `clinicalRecords`, `clinicalRecordsDetail`, `heldoutStatusMix`, `caveats`.

- `finalModel`: `{key, name, chosenBy, explanations, previous}`. `finalModel.key` (`forest`) names the final model in `metrics`, `deltaVsBaseline` and `calibrationCurve`.
- `metrics.{baseline,logistic,gbm_calibrated,forest}`: `auroc, auprc, brier, log_loss, cal_intercept, cal_slope, mean_pred`, each `{value, ci95}`, out-of-fold on the 466 development survivors. `logistic` is the previous submission.
- `modelSearch`: the unbiased nested-CV estimate of the model search (the 10x5 CV numbers for `forest` are post-selection). `deltaVsPrevious`: forest vs the previous logistic model, paired.
- `firstEvent`: ranking among survivors with no 2017 ER visit or hospital stay (the proposed prevention target).
- `deltaVsBaseline`: paired bootstrap differences (auroc, auprc, brier, log_loss) with `ci95` and `p_better`.
- `calibrationCurve`: 5 equal-size bins per model, with Wilson 95% CIs on the observed rate.
- `fairness[]` / `fairnessBaseline[]`: per subgroup `n, positives, observedRate, meanPredicted, oe, brier, auroc, tooSmall` (n < 30 or < 10 events).
- `factors[]`: TreeSHAP global importance (`meanAbsLogit`, mean absolute calibrated log-odds contribution) and `direction` of a higher value; `plainFactors[]`: observed 2018 rates with vs without a 2017 factor.
- `clinicalRecords`: `{verdict, detail}`; `clinicalRecordsDetail`: the full Synthea analysis (Q1 within Synthea, Q2 transport, Q3 increment, stratum sizes, population shift).

Excerpt:

```json
{
  "asOf": "2017-12-31T00:00:00Z",
  "outcome": "Any ER visit or hospital stay in 2018 (outcome_acute_care_2018)",
  "data": {
    "devSurvivors": 466,
    "devPositives": 134,
    "heldoutSurvivors": 199,
    "predictorsFrom": "2017 MEPS only (2018 file used for the outcome column only)"
  },
  "validation": "10x repeated stratified 5-fold CV on the development set, one row per survivor; OOF predictions averaged over repeats; 2000-sample patient bootstrap for 95% CIs; paired bootstrap for differences.",
  "finalModel": {
    "key": "forest",
    "name": "Random forest (300 trees, min leaf 10) with sigmoid calibration, on 16 features: 2017 care use (ER, hospital stays and nights, office, outpatient, home health, prescriptions, spending), age, physical and mental health scores, distress, depression screen, self-rated health, missed work days",
    "chosenBy": "nested cross-validation of a 37-candidate model search (runs/autoresearch): it won 6 of 10 outer folds",
    "explanations": "TreeSHAP per survivor, converted to calibrated log-odds (analysis/explain.py)",
    "previous": "L2 logistic regression on 34 survey-domain features (the first submission)"
  },
  "metrics": {
    "forest": {
      "auroc": {
        "value": 0.7127989570221184,
        "ci95": [
          0.662325942116102,
          0.7638970658004742
        ]
      },
      "auprc": {
        "value": 0.5078127975600191,
        "ci95": [
          0.42293901907376646,
          0.5981872372571008
        ]
      },
      "brier": {
        "value": 0.17959085396966648,
        "ci95": [
          0.16152185125206428,
          0.19824151669787296
        ]
      },
      "log_loss": {
        "value": 0.5389066734044685,
        "ci95": [
          0.497439126224133,
          0.5819725309620033
        ]
      },
      "cal_intercept": {
        "value": -0.011889850165572478,
        "ci95": [
          -0.22941104568252368,
          0.1900415297060868
        ]
      },
      "cal_slope": {
        "value": 1.1027281437453391,
        "ci95": [
          0.8222359309856233,
          1.4350184930267165
        ]
      },
      "mean_pred": {
        "value": 0.28973767813124646,
        "ci95": [
          0.27663508665099035,
          0.30301795153371447
        ]
      },
      "auroc_per_repeat": {
        "mean": 0.7108995684229455,
        "sd": 0.007710391507419087
      }
    },
    "baseline": {
      "auroc": {
        "value": 0.6593463405862255,
        "ci95": [
          0.6025372827387513,
          0.7180033339033569
        ]
      },
      "auprc": {
        "value": 0.42264841486447235,
        "ci95": [
          0.35602526986661986,
          0.5171181223936807
        ]
      },
      "brier": {
        "value": 0.20076214529615172,
        "ci95": [
          0.17854780373247575,
          0.22241324230065246
        ]
      },
      "log_loss": {
        "value": 0.6061798072022498,
        "ci95": [
          0.5458486069072257,
          0.6669952479932213
        ]
      },
      "cal_intercept": {
        "value": -0.004893078249502067,
        "ci95": [
          -0.25396237737998567,
          0.2322263259073171
        ]
      },
      "cal_slope": {
        "value": 0.44605594589114866,
        "ci95": [
          0.24817686681625262,
          0.6949211576173276
        ]
      },
      "mean_pred": {
        "value": 0.2883706966173635,
        "ci95": [
          0.27141169287645445,
          0.30583014352847154
        ]
      },
      "auroc_per_repeat": {
        "mean": 0.6462102139902896,
        "sd": 0.012053828559189763
      }
    }
  },
  "deltaVsBaseline": {
    "forest": {
      "auroc": {
        "value": 0.05345261643589283,
        "ci95": [
          -0.0012418160695974814,
          0.10476714204627115
        ],
        "p_better": 0.971
      },
      "auprc": {
        "value": 0.08516438269554671,
        "ci95": [
          0.01700177209696026,
          0.14581679516717885
        ],
        "p_better": 0.9955
      },
      "brier": {
        "value": -0.021171291326485236,
        "ci95": [
          -0.03460302573122142,
          -0.007139706666116317
        ],
        "p_better": 0.9985
      },
      "log_loss": {
        "value": -0.06727313379778133,
        "ci95": [
          -0.10675429744275372,
          -0.02649696634551372
        ],
        "p_better": 1
      }
    }
  },
  "deltaVsPrevious": {
    "previous": "logistic",
    "auroc": {
      "value": 0.04664179104477617,
      "ci95": [
        0.0115008755143862,
        0.082881824421289
      ],
      "p_better": 0.996
    },
    "auprc": {
      "value": 0.06966057611936843,
      "ci95": [
        0.01999974381303008,
        0.11139944593235392
      ],
      "p_better": 0.997
    },
    "brier": {
      "value": -0.012512798294451344,
      "ci95": [
        -0.02000459450035459,
        -0.005252871831616131
      ],
      "p_better": 0.9995
    },
    "log_loss": {
      "value": -0.030623814992775333,
      "ci95": [
        -0.04831748175433283,
        -0.012863468226682799
      ],
      "p_better": 1
    }
  },
  "modelSearch": {
    "note": "Nested CV: the whole 37-candidate search re-run inside each of 10 outer folds, so the scored model never saw its test fold. This is the unbiased estimate of what the chosen model does on new survivors.",
    "candidates": 37,
    "outerFolds": 10,
    "picks": {
      "rf|compact_raw_use": 6,
      "spline_lr|prior_use": 3,
      "poisson_glm|compact": 1
    },
    "auroc": {
      "search": 0.7107309836360366,
      "baseline": 0.6720014385901817,
      "previous": 0.6768342024815681
    },
    "logLoss": {
      "search": 0.5386771694669781,
      "baseline": 0.6057688558831227,
      "previous": 0.5654719445416405
    },
    "vsBaseline": {
      "dAuroc": 0.03872954504585491,
      "dAurocCi95": [
        -0.014892280050238701,
        0.09117944028303074
      ],
      "pAurocBetter": 0.9305,
      "dLogLoss": -0.0670916864161446,
      "dLogLossCi95": [
        -0.11475191094922225,
        -0.019910800615196244
      ],
      "pLogLossBetter": 0.9985
    },
    "vsPrevious": {
      "dAuroc": 0.03389678115446848,
      "dAurocCi95": [
        -0.0008339056776556769,
        0.06637186941818159
      ],
      "pAurocBetter": 0.972,
      "dLogLoss": -0.026794775074662436,
      "dLogLossCi95": [
        -0.04330429151725538,
        -0.009189825416749932
      ],
      "pLogLossBetter": 0.9975
    },
    "top20Events": {
      "of": 134,
      "flagged": 93,
      "procedure": 52,
      "baseline": 45,
      "submitted": 46
    },
    "callsAt50": {
      "procedure": {
        "n": 55,
        "cameTrue": 0.6727272727272727
      },
      "baseline": {
        "n": 73,
        "cameTrue": 0.4931506849315068
      },
      "submitted": {
        "n": 22,
        "cameTrue": 0.5
      }
    },
    "powerNote": "With 466 survivors and 134 events an AUROC gain needs to be about +0.056 to clear a 95% CI; the held-out set (199, about 57 events) has an AUROC standard error of about 0.04."
  },
  "firstEvent": {
    "definition": "Survivors with no ER visit or hospital stay in 2017; outcome = first acute care in 2018",
    "n": 326,
    "events": 70,
    "rate": 0.2147239263803681,
    "aurocModel": 0.6623325892857141,
    "aurocBaseline": 0.616015625,
    "deltaAuroc": 0.04631696428571419,
    "deltaCi95": [
      -0.03576313550639042,
      0.12344240905821781
    ],
    "pBetter": 0.868,
    "why": "Prior acute care explains most of the ranking on the full target (the 2017 repeat users are easy to find). Finding the first event is the harder, more useful job for prevention."
  },
  "factors": [
    {
      "feature": "spending_17",
      "label": "Total health spending in 2017 (log $)",
      "meanAbsLogit": 0.2783725919110866,
      "direction": "raises",
      "spearman": 0.7737790438466745
    },
    {
      "feature": "age",
      "label": "Age (years)",
      "meanAbsLogit": 0.13522347521903647,
      "direction": "raises",
      "spearman": 0.8748709653027853
    },
    {
      "feature": "hosp_nights_17",
      "label": "Hospital nights in 2017 (log)",
      "meanAbsLogit": 0.09971406242997714,
      "direction": "raises",
      "spearman": 0.6344178263760762
    }
  ],
  "tiers": {
    "watch": 0.29,
    "alert": 0.43,
    "tiers": [
      {
        "status": "alert",
        "riskFrom": 0.43,
        "riskTo": 1,
        "n": 92,
        "positives": 52,
        "observedRate": 0.5652173913043478,
        "shareOfAllPositives": 0.3880597014925373
      },
      {
        "status": "watch",
        "riskFrom": 0.29,
        "riskTo": 0.43,
        "n": 97,
        "positives": 29,
        "observedRate": 0.29896907216494845,
        "shareOfAllPositives": 0.21641791044776118
      },
      {
        "status": "ok",
        "riskFrom": 0,
        "riskTo": 0.29,
        "n": 277,
        "positives": 53,
        "observedRate": 0.19133574007220217,
        "shareOfAllPositives": 0.39552238805970147
      }
    ]
  },
  "fairness": [
    {
      "attribute": "age",
      "group": "18-49",
      "n": 50,
      "positives": 12,
      "observedRate": 0.24,
      "meanPredicted": 0.24169428655800843,
      "oe": 0.9929899602421848,
      "brier": 0.16219967258136303,
      "auroc": 0.7236842105263157,
      "aurocCi95": [
        0.5357494986631016,
        0.8838541666666666
      ],
      "oeCi95": [
        0.5108949387892121,
        1.4927868315864754
      ],
      "tooSmall": false
    },
    {
      "attribute": "age",
      "group": "50-64",
      "n": 146,
      "positives": 34,
      "observedRate": 0.2328767123287671,
      "meanPredicted": 0.261790995912738,
      "oe": 0.8895520318292046,
      "brier": 0.17024469968207195,
      "auroc": 0.6620273109243697,
      "aurocCi95": [
        0.5607381465517242,
        0.7653738612562142
      ],
      "oeCi95": [
        0.660755964602052,
        1.146010047658142
      ],
      "tooSmall": false
    }
  ],
  "plainFactors": [
    {
      "factor": "ER visit or hospital stay in 2017",
      "withFactor": {
        "n": 140,
        "rate": 0.45714285714285713
      },
      "without": {
        "n": 326,
        "rate": 0.2147239263803681
      },
      "rateRatio": 2.1289795918367345
    },
    {
      "factor": "Age 75 or older",
      "withFactor": {
        "n": 119,
        "rate": 0.4369747899159664
      },
      "without": {
        "n": 347,
        "rate": 0.23631123919308358
      },
      "rateRatio": 1.8491494158639066
    }
  ],
  "clinicalRecords": {
    "verdict": "No meaningful gain: clinical detail (stage, comorbidities) adds nothing even inside Synthea; Synthea-derived scores give the MEPS model at most a tiny Brier gain (about -0.001) and no clear AUROC gain. But a Synthea model on shared variables alone ranks real survivors about as well as the final survey model (tie within CI)",
    "detail": "(1) Inside Synthea (660 synthetic patients, 4033 person-years), clinical-only features (stage, metastasis, comorbidities, opioids, kidney function) add no signal over shared variables: AUROC 0.671 -> 0.670, d -0.001 [-0.008, +0.007]; stage is missing in 86% of person-years. (2) A Synthea model on shared variables only, applied unchanged to real MEPS survivors, ranks them at AUROC 0.686 [0.634, 0.740] with O/E 1.02, vs the MEPS model's 0.713 out-of-fold (paired d -0.026 [-0.068, +0.013]): the shared-variable risk pattern learned from synthetic records transports about as well as a model fit on the survey itself. (3) Added to the MEPS model: clinical-burden score d AUROC +0.004 [-0.003, +0.012], d Brier -0.0012 [-0.0022, -0.0001]; Synthea prior d AUROC +0.004 [-0.002, +0.010], d Brier -0.0009 [-0.0018, -0.0000]; stratum features (3 definitions) d AUROC between -0.006 and -0.003. (Q3 adds each Synthea score as one feature to the MEPS L2 logistic on 34 domain features, our earlier model; its reference AUROC is 0.663 with a wider C grid.) Without a shared key every Synthea feature is a function of variables MEPS already has, so a gain means the simulation is a useful prior at n=466, not that real stage or comorbidity data would help these patients. The submission uses a MEPS-only model (the calibrated forest)."
  },
  "heldoutStatusMix": {
    "alert": 40,
    "watch": 43,
    "ok": 116
  }
}
```

## `GET /`

Standalone demo page: model card, roster, one survivor panel. Same data as the API.
