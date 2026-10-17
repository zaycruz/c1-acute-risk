# C1 Care Team Risk: API contract

Base URL (deployed): `https://c1-acute-risk.zay-259.workers.dev`. All responses are JSON with `access-control-allow-origin: *`; only `GET` (and `OPTIONS`) are accepted, anything else is `405`.
The examples below are real responses, captured by `npm run e2e` on 2026-10-17T14:52:54.524Z (27/27 checks passed) and turned into this file by `npm run contract`.

Predictions are for the **199 held-out MEPS survivors** (`meps/heldout_ids.csv`): real people, forward predictions, outcome unknown to us.
`survivorId` = `c1-` + the challenge's MEPS `ID`. `updatedAt` is the as-of date of the data (end of 2017), not the build time.

## `GET /api/c1/survivors`: roster tiles

Sorted by `status` (alert, then watch, then ok), then by risk. Status comes from calibrated risk tiers set on out-of-fold development predictions:
`alert` = predicted risk >= 0.36 (top fifth; 46% of development survivors in this tier had acute care),
`watch` = >= 0.29 (the base rate; 38% had it), `ok` = below (20%).
199 survivors (41 alert, 41 watch, 117 ok), showing 3:

```json
[
  {
    "survivorId": "c1-S2480BBDE",
    "displayName": "S2480BBDE · 61F · other",
    "status": "alert",
    "headline": "Acute care risk 73% for 2018 (high), driven by ER visits last year",
    "updatedAt": "2017-12-31T00:00:00Z"
  },
  {
    "survivorId": "c1-S9707145E",
    "displayName": "S9707145E · 74F · breast",
    "status": "alert",
    "headline": "Acute care risk 68% for 2018 (high), driven by ER visits last year",
    "updatedAt": "2017-12-31T00:00:00Z"
  },
  {
    "survivorId": "c1-S13BA2BCD",
    "displayName": "S13BA2BCD · 67F · other",
    "status": "alert",
    "headline": "Acute care risk 65% for 2018 (high), driven by ER visits last year",
    "updatedAt": "2017-12-31T00:00:00Z"
  }
]
```

## `GET /api/c1/survivors/:id`: survivor panel

Contract fields: `survivorId, status, headline, summary, evidence, recommendations, charts, profile, caveat`. Extra fields: `displayName`, `risk` (0..1, identical to the submitted `predicted_risk`), `thresholds`.

- `evidence[]`: `{kind, text}`. The first item (`kind: "model"`) states the risk and what the tier meant on development data. Then up to 4 factors that raise this person's risk and up to 2 that lower it, biggest first. Extra keys: `feature`, `logitContribution` (coefficient x standardised value, log-odds vs an average survivor). `kind` is one of `prior-acute-care, medications, care-intensity, physical-function, symptoms, distress, financial-toxicity, access, treatment, support, demographic`.
- `recommendations[]`: `{audience: "coach" | "care-team" | "survivor", text}`. Tier action first, then one per actionable driver. The coach does not diagnose; clinical items go to `care-team`.
- `charts`: `risk` (value, base rate, tier cut-offs), `drivers` (bar chart of logit contributions), `scores` (2017 survey scores, `null` = not answered), `use2017` (counts).
- `caveat`: always present: association not cause, plus a warning when the questionnaire was skipped or the person belongs to a subgroup too small to judge.

```json
{
  "survivorId": "c1-S2480BBDE",
  "displayName": "S2480BBDE · 61F · other",
  "status": "alert",
  "headline": "Acute care risk 73% for 2018 (high), driven by ER visits last year",
  "summary": "73% predicted chance of an ER visit or hospital stay in 2018 (average survivor 29%). Status alert: alert from 36%, watch from 29%. Main drivers: 11 ER visit(s) in 2017 (most survivors had none); 12 hospital stay(s) in 2017; Had home health care in 2017.",
  "risk": 0.7323,
  "thresholds": {
    "alert": 0.36,
    "watch": 0.29
  },
  "evidence": [
    {
      "kind": "model",
      "text": "Predicted chance of an ER visit or hospital stay in 2018: 73%. Among development survivors in the alert tier, 46% had one."
    },
    {
      "kind": "prior-acute-care",
      "text": "11 ER visit(s) in 2017 (most survivors had none) (raises risk)",
      "feature": "er_visits_17",
      "logitContribution": 0.742
    },
    {
      "kind": "prior-acute-care",
      "text": "12 hospital stay(s) in 2017 (raises risk)",
      "feature": "hosp_stays_17",
      "logitContribution": 0.737
    },
    {
      "kind": "prior-acute-care",
      "text": "Had home health care in 2017 (raises risk)",
      "feature": "home_health_17",
      "logitContribution": 0.213
    },
    {
      "kind": "medications",
      "text": "143 prescription fills in 2017 (raises risk)",
      "feature": "rx_fills_17",
      "logitContribution": 0.19
    }
  ],
  "recommendations": [
    {
      "audience": "care-team",
      "text": "Add to the proactive outreach list: a nurse call in the next 2 weeks and a clear same-day contact route instead of the ER."
    },
    {
      "audience": "care-team",
      "text": "Review last year's ER visits for preventable causes; set a same-day call-back route before the ER."
    },
    {
      "audience": "care-team",
      "text": "Schedule a post-discharge style check-in and medication reconciliation."
    },
    {
      "audience": "care-team",
      "text": "Confirm home health is still in place and who to call after hours."
    },
    {
      "audience": "care-team",
      "text": "Do a medication review (polypharmacy, side effects, adherence)."
    },
    {
      "audience": "survivor",
      "text": "If a symptom is getting worse, call your cancer care team first: they can often help the same day without an ER visit."
    }
  ],
  "charts": {
    "risk": {
      "value": 0.7323,
      "baseRate": 0.2876,
      "watchFrom": 0.29,
      "alertFrom": 0.36
    },
    "drivers": [
      {
        "label": "ER visits in 2017",
        "logitContribution": 0.742
      },
      {
        "label": "Hospital stays in 2017",
        "logitContribution": 0.737
      },
      {
        "label": "Any home health care in 2017",
        "logitContribution": 0.213
      },
      {
        "label": "Prescription fills in 2017",
        "logitContribution": 0.19
      }
    ],
    "scores": {
      "physical_score": 22.8,
      "mental_score": 36.6,
      "distress_k6": 5,
      "depression_phq2": 1,
      "pain": 5,
      "fatigue": 4,
      "financial_toxicity": 1,
      "cost_delay": 1
    },
    "use2017": {
      "erVisits": 11,
      "hospitalStays": 12,
      "officeVisits": 15,
      "rxFills": 143
    }
  },
  "profile": {
    "age": 61,
    "sex": "female",
    "raceEthnicity": "NH White",
    "insurance2017": "Any private",
    "cancerTypes": [
      "other"
    ],
    "currentTreatment": "no",
    "region": "Northeast",
    "dataSource": "MEPS 2017 survey (real survivor, ID reassigned by organisers)"
  },
  "caveat": "Association, not cause: these factors flag who may need help; changing one is not proven to prevent an ER visit. Risk is from survey answers only (clinical records did not improve it)."
}
```

Unknown id: `404 {"error":"survivor not found"}`.

## `GET /api/c1/metrics`: model card

Top-level keys: `asOf`, `outcome`, `data`, `validation`, `finalModel`, `metrics`, `deltaVsBaseline`, `calibrationCurve`, `tiers`, `fairness`, `fairnessBaseline`, `factors`, `plainFactors`, `clinicalRecords`, `clinicalRecordsDetail`, `heldoutStatusMix`, `caveats`.

- `metrics.{baseline,logistic,gbm_calibrated}`: `auroc, auprc, brier, cal_intercept, cal_slope, mean_pred`, each `{value, ci95}`, out-of-fold on the 466 development survivors.
- `deltaVsBaseline`: paired bootstrap differences with `ci95` and `p_better`.
- `calibrationCurve`: 5 equal-size bins per model, with Wilson 95% CIs on the observed rate.
- `fairness[]` / `fairnessBaseline[]`: per subgroup `n, positives, observedRate, meanPredicted, oe, brier, auroc, tooSmall` (n < 30 or < 10 events).
- `factors[]`: model coefficients per SD with bootstrap CIs; `plainFactors[]`: observed 2018 rates with vs without a 2017 factor.
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
    "name": "L2 logistic regression on 34 survey-domain features + missing indicators",
    "regularisationC": 0.004641588833612777,
    "tunedBy": "inner 5-fold CV on log loss inside each training fold"
  },
  "metrics": {
    "logistic": {
      "auroc": {
        "value": 0.6661571659773422,
        "ci95": [
          0.6095965552293442,
          0.7246160569076577
        ]
      },
      "auprc": {
        "value": 0.43815222144065064,
        "ci95": [
          0.366760822894479,
          0.5332875310514751
        ]
      },
      "brier": {
        "value": 0.19210365226411782,
        "ci95": [
          0.17423579475742795,
          0.21039385619245546
        ]
      },
      "cal_intercept": {
        "value": -0.000578279240339202,
        "ci95": [
          -0.21849813843644184,
          0.19854213885590177
        ]
      },
      "cal_slope": {
        "value": 1.093224415389126,
        "ci95": [
          0.6774200964975093,
          1.6271456624251441
        ]
      },
      "mean_pred": {
        "value": 0.28766579325990455,
        "ci95": [
          0.27870646642792213,
          0.29739649003052265
        ]
      },
      "auroc_per_repeat": {
        "mean": 0.6580965653659414,
        "sd": 0.009326636724961698
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
    "logistic": {
      "auroc": {
        "value": 0.006810825391116659,
        "ci95": [
          -0.03830729529839445,
          0.049672308835254794
        ],
        "p_better": 0.6355
      },
      "auprc": {
        "value": 0.01550380657617828,
        "ci95": [
          -0.03321932989513826,
          0.06902988583121802
        ],
        "p_better": 0.73
      },
      "brier": {
        "value": -0.008658493032033893,
        "ci95": [
          -0.020539336312090643,
          0.0028582695377787123
        ],
        "p_better": 0.9195
      }
    }
  },
  "tiers": {
    "watch": 0.29,
    "alert": 0.36,
    "tiers": [
      {
        "status": "alert",
        "riskFrom": 0.36,
        "riskTo": 1,
        "n": 100,
        "positives": 46,
        "observedRate": 0.46,
        "shareOfAllPositives": 0.34328358208955223
      },
      {
        "status": "watch",
        "riskFrom": 0.29,
        "riskTo": 0.36,
        "n": 84,
        "positives": 32,
        "observedRate": 0.38095238095238093,
        "shareOfAllPositives": 0.23880597014925373
      },
      {
        "status": "ok",
        "riskFrom": 0,
        "riskTo": 0.29,
        "n": 282,
        "positives": 56,
        "observedRate": 0.19858156028368795,
        "shareOfAllPositives": 0.417910447761194
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
      "meanPredicted": 0.2195627720049579,
      "oe": 1.0930814810198362,
      "brier": 0.17871772196378932,
      "auroc": 0.5942982456140351,
      "aurocCi95": [
        0.3791787650019357,
        0.7949373717510259
      ],
      "oeCi95": [
        0.549496399779112,
        1.629740368487792
      ],
      "tooSmall": false
    },
    {
      "attribute": "age",
      "group": "50-64",
      "n": 146,
      "positives": 34,
      "observedRate": 0.2328767123287671,
      "meanPredicted": 0.26666396002194503,
      "oe": 0.8732965351208412,
      "brier": 0.17143137448411816,
      "auroc": 0.6685924369747899,
      "aurocCi95": [
        0.5675023443988961,
        0.7734516028633676
      ],
      "oeCi95": [
        0.6578727450335714,
        1.1326883635063087
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
    "verdict": "No meaningful gain: clinical detail (stage, comorbidities) adds nothing even inside Synthea; Synthea-derived scores give the MEPS model at most a tiny Brier gain (about -0.001) and no clear AUROC gain. But a Synthea model on shared variables alone ranks real survivors about as well as the survey model (tie within CI)",
    "detail": "(1) Inside Synthea (660 synthetic patients, 4033 person-years), clinical-only features (stage, metastasis, comorbidities, opioids, kidney function) add no signal over shared variables: AUROC 0.671 -> 0.670, d -0.001 [-0.008, +0.007]; stage is missing in 86% of person-years. (2) A Synthea model on shared variables only, applied unchanged to real MEPS survivors, ranks them at AUROC 0.686 [0.634, 0.740] with O/E 1.02, vs the MEPS model's 0.666 out-of-fold (paired d +0.020 [-0.021, +0.063]): the shared-variable risk pattern learned from synthetic records transports about as well as a model fit on the survey itself. (3) Added to the MEPS model: clinical-burden score d AUROC +0.004 [-0.003, +0.012], d Brier -0.0012 [-0.0022, -0.0001]; Synthea prior d AUROC +0.004 [-0.002, +0.010], d Brier -0.0009 [-0.0018, -0.0000]; stratum features (3 definitions) d AUROC between -0.006 and -0.003. (Q3's MEPS-only reference is 0.663, not 0.666, because it uses a wider C grid.) Without a shared key every Synthea feature is a function of variables MEPS already has, so a gain means the simulation is a useful prior at n=466, not that real stage or comorbidity data would help these patients. The submission uses the MEPS-only model."
  },
  "heldoutStatusMix": {
    "alert": 41,
    "watch": 41,
    "ok": 117
  }
}
```

## `GET /`

Standalone demo page: model card, roster, one survivor panel. Same data as the API.
