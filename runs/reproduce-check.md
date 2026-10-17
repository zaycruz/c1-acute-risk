| README number | README says | file → key | committed output | this run | result |
|---|---|---|---|---|---|
| Nested AUROC, search | 0.711 | `runs/autoresearch/round-nested.json` → `procedure/auroc` | 0.711 | 0.711 | match |
| Nested AUROC, baseline | 0.672 | `runs/autoresearch/round-nested.json` → `baseline/auroc` | 0.672 | 0.672 | match |
| Nested ΔAUROC vs baseline | +0.039 | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dAuroc` | +0.039 | +0.039 | match |
| Nested ΔAUROC CI | [-0.015, +0.091] | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dAurocCi95` | [-0.015, +0.091] | [-0.015, +0.091] | match |
| Nested P(AUROC better) | 0.93 | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/pAurocBetter` | 0.93 | 0.93 | match |
| Nested log loss, search | 0.539 | `runs/autoresearch/round-nested.json` → `procedure/logLoss` | 0.539 | 0.539 | match |
| Nested log loss, baseline | 0.606 | `runs/autoresearch/round-nested.json` → `baseline/logLoss` | 0.606 | 0.606 | match |
| Nested Δlog loss vs baseline | -0.067 | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dLogLoss` | -0.067 | -0.067 | match |
| Nested Δlog loss CI | [-0.115, -0.020] | `runs/autoresearch/round-nested.json` → `procedureVsBaseline/dLogLossCi95` | [-0.115, -0.020] | [-0.115, -0.020] | match |
| Nested candidates | 37 | `runs/autoresearch/round-nested.json` → `len(candidatePool)` | 37 | 37 | match |
| Nested folds won by the forest | 6 | `runs/autoresearch/round-nested.json` → `picks/rf|compact_raw_use` | 6 | 6 | match |
| Top-fifth events, search | 52 | `src/data/metrics.json` → `modelSearch/top20Events/procedure` | 52 | 52 | match |
| Top-fifth events, baseline | 45 | `src/data/metrics.json` → `modelSearch/top20Events/baseline` | 45 | 45 | match |
| At 50%: NH Black PPV | 20% | `src/data/metrics.json` → `subgroupAt50 rows[group=NH Black]/ppv` | 20% | 20% | match |
| At 50%: NH Black PPV CI | [0, 50] | `src/data/metrics.json` → `subgroupAt50 rows[group=NH Black]/ppvCi95` | [0, 50] | [0, 50] | match |
| At 50%: NH White PPV | 72% | `src/data/metrics.json` → `subgroupAt50 rows[group=NH White]/ppv` | 72% | 72% | match |
| At 50%: NH White PPV CI | [57, 85] | `src/data/metrics.json` → `subgroupAt50 rows[group=NH White]/ppvCi95` | [57, 85] | [57, 85] | match |
| At 50%: all survivors sensitivity | 26% | `src/data/metrics.json` → `subgroupAt50 rows[group=All survivors]/sensitivity` | 26% | 26% | match |
| At 50%: age 50-64 PPV | 33% | `src/data/metrics.json` → `subgroupAt50 rows[group=50-64]/ppv` | 33% | 33% | match |
| Hero: served forest 50%+ calls that came true | 59% | `src/data/metrics.json` → `servedModel/callsAt50/forest/cameTrue` | 59% | 59% | match |
| Hero: served forest 50%+ CI | [46%, 71%] | `src/data/metrics.json` → `servedModel/callsAt50/forest/cameTrueCi95` | [46%, 71%] | [46%, 71%] | match |
| Hero: served forest 50%+ calls (n) | 59 | `src/data/metrics.json` → `servedModel/callsAt50/forest/n` | 59 | 59 | match |
| Hero: baseline 50%+ calls that came true | 48% | `src/data/metrics.json` → `servedModel/callsAt50/baseline/cameTrue` | 48% | 48% | match |
| Hero: baseline 50%+ calls (n) | 69 | `src/data/metrics.json` → `servedModel/callsAt50/baseline/n` | 69 | 69 | match |
| Hero: difference CI (points) | [-0.2, +23] | `src/data/metrics.json` → `servedModel/callsAt50/differenceCi95` | [-0.2, +23] | [-0.2, +23] | match |
| Expected held-out events | 57 | `src/data/metrics.json` → `servedModel/expectedHeldout/expectedEvents` | 57 | 57 | match |
| Expected held-out AUROC range | 0.63 to 0.79 | `src/data/metrics.json` → `servedModel/expectedHeldout/aurocRange95` | 0.63 to 0.79 | 0.63 to 0.79 | match |
| 50%+ calls that came true, search | 67% | `src/data/metrics.json` → `modelSearch/callsAt50/procedure/cameTrue` | 67% | 67% | match |
| 50%+ calls, search (n) | 55 | `src/data/metrics.json` → `modelSearch/callsAt50/procedure/n` | 55 | 55 | match |
| 50%+ calls that came true, baseline | 49% | `src/data/metrics.json` → `modelSearch/callsAt50/baseline/cameTrue` | 49% | 49% | match |
| 50%+ calls, baseline (n) | 73 | `src/data/metrics.json` → `modelSearch/callsAt50/baseline/n` | 73 | 73 | match |
| Nested ΔAUROC vs first submission | +0.034 | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dAuroc` | +0.034 | +0.034 | match |
| Nested ΔAUROC vs first submission CI | [-0.001, +0.066] | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dAurocCi95` | [-0.001, +0.066] | [-0.001, +0.066] | match |
| Nested Δlog loss vs first submission | -0.027 | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dLogLoss` | -0.027 | -0.027 | match |
| Nested Δlog loss vs first submission CI | [-0.043, -0.009] | `runs/autoresearch/round-nested.json` → `procedureVsSubmitted/dLogLossCi95` | [-0.043, -0.009] | [-0.043, -0.009] | match |
| 10×5 AUROC, baseline | 0.659 | `analysis/out/metrics_meps.json` → `metrics/baseline/auroc/value` | 0.659 | 0.659 | match |
| 10×5 AUROC CI, baseline | [0.603, 0.718] | `analysis/out/metrics_meps.json` → `metrics/baseline/auroc/ci95` | [0.603, 0.718] | [0.603, 0.718] | match |
| 10×5 AUROC, logistic | 0.666 | `analysis/out/metrics_meps.json` → `metrics/logistic/auroc/value` | 0.666 | 0.666 | match |
| 10×5 AUROC, forest | 0.713 | `analysis/out/metrics_meps.json` → `metrics/forest/auroc/value` | 0.713 | 0.713 | match |
| 10×5 AUROC CI, forest | [0.662, 0.764] | `analysis/out/metrics_meps.json` → `metrics/forest/auroc/ci95` | [0.662, 0.764] | [0.662, 0.764] | match |
| 10×5 ΔAUROC forest vs baseline | +0.053 | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auroc/value` | +0.053 | +0.053 | match |
| 10×5 ΔAUROC CI | [-0.001, +0.105] | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auroc/ci95` | [-0.001, +0.105] | [-0.001, +0.105] | match |
| 10×5 AUPRC, baseline | 0.423 | `analysis/out/metrics_meps.json` → `metrics/baseline/auprc/value` | 0.423 | 0.423 | match |
| 10×5 AUPRC, logistic | 0.438 | `analysis/out/metrics_meps.json` → `metrics/logistic/auprc/value` | 0.438 | 0.438 | match |
| 10×5 AUPRC, forest | 0.508 | `analysis/out/metrics_meps.json` → `metrics/forest/auprc/value` | 0.508 | 0.508 | match |
| 10×5 ΔAUPRC | +0.085 | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auprc/value` | +0.085 | +0.085 | match |
| 10×5 ΔAUPRC CI | [+0.017, +0.146] | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/auprc/ci95` | [+0.017, +0.146] | [+0.017, +0.146] | match |
| 10×5 Brier, baseline | 0.2008 | `analysis/out/metrics_meps.json` → `metrics/baseline/brier/value` | 0.2008 | 0.2008 | match |
| 10×5 Brier, logistic | 0.1921 | `analysis/out/metrics_meps.json` → `metrics/logistic/brier/value` | 0.1921 | 0.1921 | match |
| 10×5 Brier, forest | 0.1796 | `analysis/out/metrics_meps.json` → `metrics/forest/brier/value` | 0.1796 | 0.1796 | match |
| 10×5 ΔBrier | -0.021 | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/brier/value` | -0.021 | -0.021 | match |
| 10×5 ΔBrier CI | [-0.035, -0.007] | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/brier/ci95` | [-0.035, -0.007] | [-0.035, -0.007] | match |
| 10×5 log loss, baseline | 0.606 | `analysis/out/metrics_meps.json` → `metrics/baseline/log_loss/value` | 0.606 | 0.606 | match |
| 10×5 log loss, logistic | 0.570 | `analysis/out/metrics_meps.json` → `metrics/logistic/log_loss/value` | 0.570 | 0.570 | match |
| 10×5 log loss, forest | 0.539 | `analysis/out/metrics_meps.json` → `metrics/forest/log_loss/value` | 0.539 | 0.539 | match |
| 10×5 Δlog loss | -0.067 | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/log_loss/value` | -0.067 | -0.067 | match |
| 10×5 Δlog loss CI | [-0.107, -0.026] | `analysis/out/metrics_meps.json` → `deltaVsBaseline/forest/log_loss/ci95` | [-0.107, -0.026] | [-0.107, -0.026] | match |
| Calibration slope, baseline | 0.45 | `analysis/out/metrics_meps.json` → `metrics/baseline/cal_slope/value` | 0.45 | 0.45 | match |
| Calibration slope CI, baseline | [0.25, 0.69] | `analysis/out/metrics_meps.json` → `metrics/baseline/cal_slope/ci95` | [0.25, 0.69] | [0.25, 0.69] | match |
| Calibration slope, logistic | 1.09 | `analysis/out/metrics_meps.json` → `metrics/logistic/cal_slope/value` | 1.09 | 1.09 | match |
| Calibration slope, forest | 1.10 | `analysis/out/metrics_meps.json` → `metrics/forest/cal_slope/value` | 1.10 | 1.10 | match |
| Calibration slope CI, forest | [0.82, 1.44] | `analysis/out/metrics_meps.json` → `metrics/forest/cal_slope/ci95` | [0.82, 1.44] | [0.82, 1.44] | match |
| Alert cut-off | 43% | `src/data/metrics.json` → `tiers/alert` | 43% | 43% | match |
| Alert tier observed rate | 57% | `src/data/metrics.json` → `tiers/tiers/0/observedRate` | 57% | 57% | match |
| Alert tier share of events | 39% | `src/data/metrics.json` → `tiers/tiers/0/shareOfAllPositives` | 39% | 39% | match |
| Watch cut-off | 29% | `src/data/metrics.json` → `tiers/watch` | 29% | 29% | match |
| Watch tier observed rate | 30% | `src/data/metrics.json` → `tiers/tiers/1/observedRate` | 30% | 30% | match |
| Ok tier observed rate | 19% | `src/data/metrics.json` → `tiers/tiers/2/observedRate` | 19% | 19% | match |
| Held-out alert | 40 | `src/data/metrics.json` → `heldoutStatusMix/alert` | 40 | 40 | match |
| Held-out watch | 43 | `src/data/metrics.json` → `heldoutStatusMix/watch` | 43 | 43 | match |
| Held-out ok | 116 | `src/data/metrics.json` → `heldoutStatusMix/ok` | 116 | 116 | match |
| Six prior-use features alone | 0.697 | `runs/autoresearch/round-1.json` → `results[candidate="lr_l2|prior_use"]/auroc` | 0.697 | 0.697 | match |
| Within prior-use group ΔAUROC | +0.094 | `runs/autoresearch/stratified.json` → `prior/search/delta` | +0.094 | +0.094 | match |
| Within prior-use group CI | [-0.002, +0.206] | `runs/autoresearch/stratified.json` → `prior/search/ci95` | [-0.002, +0.206] | [-0.002, +0.206] | match |
| First event n | 326 | `src/data/metrics.json` → `firstEvent/n` | 326 | 326 | match |
| First event events | 70 | `src/data/metrics.json` → `firstEvent/events` | 70 | 70 | match |
| First event AUROC, search | 0.653 | `src/data/metrics.json` → `firstEvent/aurocModel` | 0.653 | 0.653 | match |
| First event AUROC, baseline | 0.634 | `src/data/metrics.json` → `firstEvent/aurocBaseline` | 0.634 | 0.634 | match |
| First event ΔAUROC | +0.019 | `src/data/metrics.json` → `firstEvent/deltaAuroc` | +0.019 | +0.019 | match |
| First event ΔAUROC CI | [-0.065, +0.103] | `src/data/metrics.json` → `firstEvent/deltaCi95` | [-0.065, +0.103] | [-0.065, +0.103] | match |
| Prior acute care rate with | 46% | `src/data/metrics.json` → `plainFactors/0/withFactor/rate` | 46% | 46% | match |
| Prior acute care rate without | 21% | `src/data/metrics.json` → `plainFactors/0/without/rate` | 21% | 21% | match |
| Prior acute care ratio | 2.1× | `src/data/metrics.json` → `plainFactors/0/rateRatio` | 2.1× | 2.1× | match |
| Age 75+ rate with | 44% | `src/data/metrics.json` → `plainFactors/1/withFactor/rate` | 44% | 44% | match |
| Age 75+ rate without | 24% | `src/data/metrics.json` → `plainFactors/1/without/rate` | 24% | 24% | match |
| Fairness AUROC, female | 0.72 | `src/data/metrics.json` → `fairness[group="Female"]/auroc` | 0.72 | 0.72 | match |
| Fairness AUROC, male | 0.70 | `src/data/metrics.json` → `fairness[group="Male"]/auroc` | 0.70 | 0.70 | match |
| Fairness AUROC, any private | 0.68 | `src/data/metrics.json` → `fairness[group="Any private"]/auroc` | 0.68 | 0.68 | match |
| Fairness AUROC, public only | 0.75 | `src/data/metrics.json` → `fairness[group="Public only"]/auroc` | 0.75 | 0.75 | match |
| Age 75+ O/E | 1.15 | `src/data/metrics.json` → `fairness[group="75+ (85 = top-coded)"]/oe` | 1.15 | 1.15 | match |
| Age 75+ O/E CI | [0.91, 1.37] | `src/data/metrics.json` → `fairness[group="75+ (85 = top-coded)"]/oeCi95` | [0.91, 1.37] | [0.91, 1.37] | match |
| NH Black AUROC | 0.48 | `src/data/metrics.json` → `fairness[group="NH Black"]/auroc` | 0.48 | 0.48 | match |
| NH Black AUROC CI | [0.25, 0.70] | `src/data/metrics.json` → `fairness[group="NH Black"]/aurocCi95` | [0.25, 0.70] | [0.25, 0.70] | match |
| NH Black n | 47 | `src/data/metrics.json` → `fairness[group="NH Black"]/n` | 47 | 47 | match |
| Synthea Q1 AUROC shared | 0.671 | `analysis/out/synthea.json` → `q1WithinSynthea/aurocShared` | 0.671 | 0.671 | match |
| Synthea Q1 AUROC shared + clinical | 0.670 | `analysis/out/synthea.json` → `q1WithinSynthea/aurocSharedPlusClinical` | 0.670 | 0.670 | match |
| Synthea Q1 Δ | -0.001 | `analysis/out/synthea.json` → `q1WithinSynthea/deltaAuroc` | -0.001 | -0.001 | match |
| Synthea Q1 Δ CI | [-0.008, +0.007] | `analysis/out/synthea.json` → `q1WithinSynthea/deltaAurocCi95` | [-0.008, +0.007] | [-0.008, +0.007] | match |
| Synthea stage missing | 86% | `analysis/out/synthea.json` → `q1WithinSynthea/stageMissingShare` | 86% | 86% | match |
| Synthea Q2 transport AUROC | 0.686 | `analysis/out/synthea.json` → `q2Transport/aurocInMeps` | 0.686 | 0.686 | match |
| Synthea Q2 transport CI | [0.634, 0.740] | `analysis/out/synthea.json` → `q2Transport/ci95` | [0.634, 0.740] | [0.634, 0.740] | match |
| Synthea Q2 O/E | 1.02 | `analysis/out/synthea.json` → `q2Transport/oe` | 1.02 | 1.02 | match |
| Synthea Q2 Δ vs forest | -0.026 | `analysis/out/synthea.json` → `q2Transport/vsMepsModel/deltaAuroc` | -0.026 | -0.026 | match |
| Synthea Q2 Δ CI | [-0.068, +0.013] | `analysis/out/synthea.json` → `q2Transport/vsMepsModel/ci95` | [-0.068, +0.013] | [-0.068, +0.013] | match |
| Synthea Q3 burden ΔAUROC | +0.004 | `analysis/out/synthea.json` → `q3Increment/transfer_clinical_burden/delta/auroc/value` | +0.004 | +0.004 | match |
| Synthea Q3 burden ΔAUROC CI | [-0.003, +0.012] | `analysis/out/synthea.json` → `q3Increment/transfer_clinical_burden/delta/auroc/ci95` | [-0.003, +0.012] | [-0.003, +0.012] | match |
| Synthea Q3 prior ΔAUROC | +0.004 | `analysis/out/synthea.json` → `q3Increment/transfer_prior_logit/delta/auroc/value` | +0.004 | +0.004 | match |
| Synthea Q3 prior ΔAUROC CI | [-0.002, +0.010] | `analysis/out/synthea.json` → `q3Increment/transfer_prior_logit/delta/auroc/ci95` | [-0.002, +0.010] | [-0.002, +0.010] | match |
| Synthea Q3 MEPS-only reference | 0.663 | `analysis/out/synthea.json` → `q3Increment/baseline/auroc/value` | 0.663 | 0.663 | match |
| Synthea-prior candidate (round 3) | 0.692 | `runs/autoresearch/round-3.json` → `results[candidate="synthea_prior|prior_use"]/auroc` | 0.692 | 0.692 | match |
| Mitigation: current NH Black AUROC CI (2,000 draws) | [0.25, 0.71] | `analysis/out/fairness_mitigation.json` → `variants/current/nhBlack/aurocCi95` | [0.25, 0.71] | [0.25, 0.71] | match |
| Mitigation: current NH Black O/E | 0.73 | `analysis/out/fairness_mitigation.json` → `variants/current/nhBlack/oe` | 0.73 | 0.73 | match |
| Mitigation: recalibrated NH Black AUROC | 0.44 | `analysis/out/fairness_mitigation.json` → `variants/recalibrated/nhBlack/auroc` | 0.44 | 0.44 | match |
| Mitigation: recalibrated NH Black O/E | 1.00 | `analysis/out/fairness_mitigation.json` → `variants/recalibrated/nhBlack/oe` | 1.00 | 1.00 | match |
| Mitigation: recalibrated Δ within group | -0.040 | `analysis/out/fairness_mitigation.json` → `variants/recalibrated/vsCurrent/groupDeltaAuroc` | -0.040 | -0.040 | match |
| Mitigation: recalibrated log loss | 0.542 | `analysis/out/fairness_mitigation.json` → `variants/recalibrated/overall/logLoss` | 0.542 | 0.542 | match |
| Mitigation: reweighted NH Black AUROC | 0.46 | `analysis/out/fairness_mitigation.json` → `variants/reweighted/nhBlack/auroc` | 0.46 | 0.46 | match |
| Mitigation: reweighted Δ CI | [-0.068, +0.029] | `analysis/out/fairness_mitigation.json` → `variants/reweighted/vsCurrent/groupDeltaAurocCi95` | [-0.068, +0.029] | [-0.068, +0.029] | match |
| Mitigation: reweighted log loss | 0.546 | `analysis/out/fairness_mitigation.json` → `variants/reweighted/overall/logLoss` | 0.546 | 0.546 | match |
| Mitigation: group features NH Black AUROC | 0.47 | `analysis/out/fairness_mitigation.json` → `variants/group_features/nhBlack/auroc` | 0.47 | 0.47 | match |
| Mitigation: group features Δ | -0.008 | `analysis/out/fairness_mitigation.json` → `variants/group_features/vsCurrent/groupDeltaAuroc` | -0.008 | -0.008 | match |
| Mitigation: both NH Black O/E | 0.81 | `analysis/out/fairness_mitigation.json` → `variants/both/nhBlack/oe` | 0.81 | 0.81 | match |
| Mitigation: both log loss | 0.545 | `analysis/out/fairness_mitigation.json` → `variants/both/overall/logLoss` | 0.545 | 0.545 | match |
| Mitigation: variants passing | No variant passes | `analysis/out/fairness_mitigation.json` → `len(passed)` | No variant passes | No variant passes | match |
| Pooled not-NH-White AUROC | 0.56 | `analysis/out/fairness_mitigation.json` → `extraSubgroups/1/auroc` | 0.56 | 0.56 | match |
| Pooled not-NH-White AUROC CI | [0.41, 0.71] | `analysis/out/fairness_mitigation.json` → `extraSubgroups/1/aurocCi95` | [0.41, 0.71] | [0.41, 0.71] | match |
| Pooled not-NH-White n | 95 | `analysis/out/fairness_mitigation.json` → `extraSubgroups/1/n` | 95 | 95 | match |
| Pooled not-NH-White O/E CI | [0.46, 1.01] | `analysis/out/fairness_mitigation.json` → `extraSubgroups/1/oeCi95` | [0.46, 1.01] | [0.46, 1.01] | match |
| Hispanic AUROC | 0.64 | `analysis/out/fairness_mitigation.json` → `extraSubgroups/0/auroc` | 0.64 | 0.64 | match |
| Hispanic AUROC CI | [0.38, 0.86] | `analysis/out/fairness_mitigation.json` → `extraSubgroups/0/aurocCi95` | [0.38, 0.86] | [0.38, 0.86] | match |
| NH White AUROC | 0.75 | `src/data/metrics.json` → `fairness[group="NH White"]/auroc` | 0.75 | 0.75 | match |
| Held-out survivors with humanCheck | 4 | `src/data/survivors.json` → `count(details[].humanCheck.required)` | n/a | 4 | match |
| Alert calls/week per 500 survivors | 1.9 | `src/data/metrics.json` → `alertBudget/cutoffs[topShare=0.2]/per100SurvivorsPerWeek x 5` | 1.9 | 1.9 | match |
| Alert calls per event found | 1.8 | `src/data/metrics.json` → `tiers/tiers/0/observedRate` | 1.8 | 1.8 | match |
| Top-tenth share of events | 21% | `src/data/metrics.json` → `alertBudget/cutoffs[topShare=0.1]/shareOfAllEvents` | 21% | 21% | match |
| Top-tenth precision | 60% | `src/data/metrics.json` → `alertBudget/cutoffs[topShare=0.1]/devObservedRate` | 60% | 60% | match |
| Submission CSV | committed copy | `submission/heldout_predictions.csv` | | 199 rows, same IDs and order, max |Δ predicted_risk| = 0.00e+00 | match |

**Reproduction: PASS.** This run differs from the committed outputs on 0 of 136 numbers; submission CSV identical.

**README: 136 of 136 numbers match this run.**

**Submission sha256 (this run): `77f6006837c4081102998f7f81198985e530b5aedb6fc66df8c29b98c2013aee`.** The live API serves its hash as the `x-c1-artifact` header and `/api/c1/metrics` → `build.submissionSha256`; equal hashes mean the served predictions are these.
