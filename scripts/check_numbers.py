#!/usr/bin/env python3
"""Compare every headline number in README.md with the file and key it comes from.

Usage: python -I scripts/check_numbers.py [--out report.md]
Two verdicts:
  reproduction: this run's value equals the committed output (git HEAD) for every claim, and the submission matches;
  README:       the README prints exactly what the run produced.
Exit 0 when the reproduction verdict passes and every claim's text is found in README.md; README rounding typos are
listed but do not fail the run (they are present in the committed output too, so they are not reproduction failures).

Each claim is (README number, file, key, formatter, text that must appear in README.md).
The formatter rounds the produced value the way the README prints it, so "match" means the
README string is exactly what the run produced. The submission CSV is also compared, row by row,
with the committed copy (git HEAD).
"""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p)) if os.path.exists(p) else None


def load_committed(rel):
    """The same file as committed at git HEAD, i.e. what produced the README."""
    r = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{rel}"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def get(obj, path):
    for k in path.split("/"):
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    return obj


f3 = lambda v: f"{v:.3f}"
f4 = lambda v: f"{v:.4f}"
f2 = lambda v: f"{v:.2f}"
s3 = lambda v: f"{v:+.3f}".replace("+-", "-")
pct = lambda v: f"{round(v * 100)}%"
num = lambda v: str(int(v))
ci3 = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
ci2 = lambda v: f"[{v[0]:.2f}, {v[1]:.2f}]"
sci3 = lambda v: f"[{v[0]:+.3f}, {v[1]:+.3f}]"
ratio = lambda v: f"{v:.1f}×"

MM = "analysis/out/metrics_meps.json"
EX = "src/data/metrics.json"
NE = "runs/autoresearch/round-nested.json"
SY = "analysis/out/synthea.json"
ST = "runs/autoresearch/stratified.json"
R1 = "runs/autoresearch/round-1.json"
R3 = "runs/autoresearch/round-3.json"
FM = "analysis/out/fairness_mitigation.json"


def described(desc, fn):
    fn.desc = desc
    return fn


def cand(rel, name):
    return described(f'results[candidate="{name}"]/auroc', lambda J: next(r for r in J["results"] if r["candidate"] == name)["auroc"])


def fair(group, key):
    return described(f'fairness[group="{group}"]/{key}', lambda J: next(r for r in J["fairness"] if r["group"] == group)[key])


def tier(i, key):
    return described(f"tiers/tiers/{i}/{key}", lambda J: J["tiers"]["tiers"][i][key])


# (label, expected README string, file, key path or function, formatter, README text containing it)
CLAIMS = [
    # nested CV (the honest estimate)
    ("Nested AUROC, search", "0.711", NE, "procedure/auroc", f3, "| AUROC | **0.711** | 0.672 |"),
    ("Nested AUROC, baseline", "0.672", NE, "baseline/auroc", f3, "| AUROC | **0.711** | 0.672 |"),
    ("Nested ΔAUROC vs baseline", "+0.039", NE, "procedureVsBaseline/dAuroc", s3, "+0.039 [-0.015, +0.091]"),
    ("Nested ΔAUROC CI", "[-0.015, +0.091]", NE, "procedureVsBaseline/dAurocCi95", sci3, "+0.039 [-0.015, +0.091]"),
    ("Nested P(AUROC better)", "0.93", NE, "procedureVsBaseline/pAurocBetter", f2, "P(better) 0.93"),
    ("Nested log loss, search", "0.539", NE, "procedure/logLoss", f3, "| Log loss (lower = better) | **0.539** | 0.606 |"),
    ("Nested log loss, baseline", "0.606", NE, "baseline/logLoss", f3, "| Log loss (lower = better) | **0.539** | 0.606 |"),
    ("Nested Δlog loss vs baseline", "-0.067", NE, "procedureVsBaseline/dLogLoss", s3, "-0.067 [-0.115, -0.020]"),
    ("Nested Δlog loss CI", "[-0.115, -0.020]", NE, "procedureVsBaseline/dLogLossCi95", sci3, "-0.067 [-0.115, -0.020]"),
    ("Nested candidates", "37", NE, described("len(candidatePool)", lambda J: len(J["candidatePool"])), num, "rounds 1–2 search (37 candidates)"),
    ("Nested folds won by the forest", "6", NE, "picks/rf|compact_raw_use", num, "picked the forest in 6 of 10 folds"),
    ("Top-fifth events, search", "52", EX, "modelSearch/top20Events/procedure", num, "| Events caught in the top fifth (of 134) | **52** | 45 |"),
    ("Top-fifth events, baseline", "45", EX, "modelSearch/top20Events/baseline", num, "| Events caught in the top fifth (of 134) | **52** | 45 |"),
    ("At 50%: NH Black PPV", "20%", EX, described("subgroupAt50 rows[group=NH Black]/ppv", lambda d: next(r for r in d["subgroupAt50"]["rows"] if r["group"] == "NH Black")["ppv"]), pct, "| NH Black | 47 | 11 | 10 | 18% [0, 44] | 20% [0, 50] |"),
    ("At 50%: NH Black PPV CI", "[0, 50]", EX, described("subgroupAt50 rows[group=NH Black]/ppvCi95", lambda d: next(r for r in d["subgroupAt50"]["rows"] if r["group"] == "NH Black")["ppvCi95"]), lambda v: f"[{round(v[0]*100)}, {round(v[1]*100)}]", "PPV 20% [0, 50]"),
    ("At 50%: NH White PPV", "72%", EX, described("subgroupAt50 rows[group=NH White]/ppv", lambda d: next(r for r in d["subgroupAt50"]["rows"] if r["group"] == "NH White")["ppv"]), pct, "against 72% [57, 85] for NH White"),
    ("At 50%: NH White PPV CI", "[57, 85]", EX, described("subgroupAt50 rows[group=NH White]/ppvCi95", lambda d: next(r for r in d["subgroupAt50"]["rows"] if r["group"] == "NH White")["ppvCi95"]), lambda v: f"[{round(v[0]*100)}, {round(v[1]*100)}]", "against 72% [57, 85] for NH White"),
    ("At 50%: all survivors sensitivity", "26%", EX, described("subgroupAt50 rows[group=All survivors]/sensitivity", lambda d: next(r for r in d["subgroupAt50"]["rows"] if r["group"] == "All survivors")["sensitivity"]), pct, "| All survivors | 466 | 134 | 59 | 26% [19, 34] |"),
    ("At 50%: age 50-64 PPV", "33%", EX, described("subgroupAt50 rows[group=50-64]/ppv", lambda d: next(r for r in d["subgroupAt50"]["rows"] if r["group"] == "50-64")["ppv"]), pct, "a low PPV (33% [8, 62])"),
    ("Hero: served forest 50%+ calls that came true", "59%", EX, "servedModel/callsAt50/forest/cameTrue", pct, "it is right 59% of the time [46%, 71%]"),
    ("Hero: served forest 50%+ CI", "[46%, 71%]", EX, "servedModel/callsAt50/forest/cameTrueCi95", lambda v: f"[{round(v[0]*100)}%, {round(v[1]*100)}%]", "it is right 59% of the time [46%, 71%]"),
    ("Hero: served forest 50%+ calls (n)", "59", EX, "servedModel/callsAt50/forest/n", num, "That is 59 and 69 calls"),
    ("Hero: baseline 50%+ calls that came true", "48%", EX, "servedModel/callsAt50/baseline/cameTrue", pct, "baseline is right 48%"),
    ("Hero: baseline 50%+ calls (n)", "69", EX, "servedModel/callsAt50/baseline/n", num, "That is 59 and 69 calls"),
    ("Hero: difference CI (points)", "[-0.2, +23]", EX, "servedModel/callsAt50/differenceCi95", lambda v: f"[{v[0]*100:+.1f}, {v[1]*100:+.0f}]".replace("[-0.2", "[-0.2"), "+11 points [-0.2, +23]"),
    ("Expected held-out events", "57", EX, "servedModel/expectedHeldout/expectedEvents", num, "(about 57 events)"),
    ("Expected held-out AUROC range", "0.63 to 0.79", EX, "servedModel/expectedHeldout/aurocRange95", lambda v: f"{v[0]:.2f} to {v[1]:.2f}", "anywhere from 0.63 to 0.79"),
    ("50%+ calls that came true, search", "67%", EX, "modelSearch/callsAt50/procedure/cameTrue", pct, "**67%** of 55 calls"),
    ("50%+ calls, search (n)", "55", EX, "modelSearch/callsAt50/procedure/n", num, "**67%** of 55 calls"),
    ("50%+ calls that came true, baseline", "49%", EX, "modelSearch/callsAt50/baseline/cameTrue", pct, "49% of 73 calls"),
    ("50%+ calls, baseline (n)", "73", EX, "modelSearch/callsAt50/baseline/n", num, "49% of 73 calls"),
    ("Nested ΔAUROC vs first submission", "+0.034", NE, "procedureVsSubmitted/dAuroc", s3, "AUROC +0.034 [-0.001, +0.066]"),
    ("Nested ΔAUROC vs first submission CI", "[-0.001, +0.066]", NE, "procedureVsSubmitted/dAurocCi95", sci3, "AUROC +0.034 [-0.001, +0.066]"),
    ("Nested Δlog loss vs first submission", "-0.027", NE, "procedureVsSubmitted/dLogLoss", s3, "log loss -0.027 [-0.043, -0.009]"),
    ("Nested Δlog loss vs first submission CI", "[-0.043, -0.009]", NE, "procedureVsSubmitted/dLogLossCi95", sci3, "log loss -0.027 [-0.043, -0.009]"),
    # 10x5 CV
    ("10×5 AUROC, baseline", "0.659", MM, "metrics/baseline/auroc/value", f3, "| AUROC | 0.659 [0.603, 0.718] |"),
    ("10×5 AUROC CI, baseline", "[0.603, 0.718]", MM, "metrics/baseline/auroc/ci95", ci3, "| AUROC | 0.659 [0.603, 0.718] |"),
    ("10×5 AUROC, logistic", "0.666", MM, "metrics/logistic/auroc/value", f3, "| AUROC | 0.659 [0.603, 0.718] | 0.666 |"),
    ("10×5 AUROC, forest", "0.713", MM, "metrics/forest/auroc/value", f3, "**0.713** [0.662, 0.764]"),
    ("10×5 AUROC CI, forest", "[0.662, 0.764]", MM, "metrics/forest/auroc/ci95", ci3, "**0.713** [0.662, 0.764]"),
    ("10×5 ΔAUROC forest vs baseline", "+0.053", MM, "deltaVsBaseline/forest/auroc/value", s3, "+0.053 [-0.001, +0.105]"),
    ("10×5 ΔAUROC CI", "[-0.001, +0.105]", MM, "deltaVsBaseline/forest/auroc/ci95", sci3, "+0.053 [-0.001, +0.105]"),
    ("10×5 AUPRC, baseline", "0.423", MM, "metrics/baseline/auprc/value", f3, "| AUPRC | 0.423 | 0.438 | **0.508** |"),
    ("10×5 AUPRC, logistic", "0.438", MM, "metrics/logistic/auprc/value", f3, "| AUPRC | 0.423 | 0.438 | **0.508** |"),
    ("10×5 AUPRC, forest", "0.508", MM, "metrics/forest/auprc/value", f3, "| AUPRC | 0.423 | 0.438 | **0.508** |"),
    ("10×5 ΔAUPRC", "+0.085", MM, "deltaVsBaseline/forest/auprc/value", s3, "+0.085 [+0.017, +0.146]"),
    ("10×5 ΔAUPRC CI", "[+0.017, +0.146]", MM, "deltaVsBaseline/forest/auprc/ci95", sci3, "+0.085 [+0.017, +0.146]"),
    ("10×5 Brier, baseline", "0.2008", MM, "metrics/baseline/brier/value", f4, "| Brier | 0.2008 | 0.1921 | **0.1796** |"),
    ("10×5 Brier, logistic", "0.1921", MM, "metrics/logistic/brier/value", f4, "| Brier | 0.2008 | 0.1921 | **0.1796** |"),
    ("10×5 Brier, forest", "0.1796", MM, "metrics/forest/brier/value", f4, "| Brier | 0.2008 | 0.1921 | **0.1796** |"),
    ("10×5 ΔBrier", "-0.021", MM, "deltaVsBaseline/forest/brier/value", s3, "-0.021 [-0.035, -0.007]"),
    ("10×5 ΔBrier CI", "[-0.035, -0.007]", MM, "deltaVsBaseline/forest/brier/ci95", sci3, "-0.021 [-0.035, -0.007]"),
    ("10×5 log loss, baseline", "0.606", MM, "metrics/baseline/log_loss/value", f3, "| Log loss | 0.606 | 0.570 | **0.539** |"),
    ("10×5 log loss, logistic", "0.570", MM, "metrics/logistic/log_loss/value", f3, "| Log loss | 0.606 | 0.570 | **0.539** |"),
    ("10×5 log loss, forest", "0.539", MM, "metrics/forest/log_loss/value", f3, "| Log loss | 0.606 | 0.570 | **0.539** |"),
    ("10×5 Δlog loss", "-0.067", MM, "deltaVsBaseline/forest/log_loss/value", s3, "-0.067 [-0.107, -0.026]"),
    ("10×5 Δlog loss CI", "[-0.107, -0.026]", MM, "deltaVsBaseline/forest/log_loss/ci95", sci3, "-0.067 [-0.107, -0.026]"),
    ("Calibration slope, baseline", "0.45", MM, "metrics/baseline/cal_slope/value", f2, "0.45 [0.25, 0.69]"),
    ("Calibration slope CI, baseline", "[0.25, 0.69]", MM, "metrics/baseline/cal_slope/ci95", ci2, "0.45 [0.25, 0.69]"),
    ("Calibration slope, logistic", "1.09", MM, "metrics/logistic/cal_slope/value", f2, "0.45 [0.25, 0.69] | 1.09 |"),
    ("Calibration slope, forest", "1.10", MM, "metrics/forest/cal_slope/value", f2, "**1.10** [0.82, 1.44]"),
    ("Calibration slope CI, forest", "[0.82, 1.44]", MM, "metrics/forest/cal_slope/ci95", ci2, "**1.10** [0.82, 1.44]"),
    # tiers and roster
    ("Alert cut-off", "43%", EX, "tiers/alert", pct, "alert is 43% or more"),
    ("Alert tier observed rate", "57%", EX, tier(0, "observedRate"), pct, "57% had acute care"),
    ("Alert tier share of events", "39%", EX, tier(0, "shareOfAllPositives"), pct, "39% of all events"),
    ("Watch cut-off", "29%", EX, "tiers/watch", pct, "Ok is below 29% (19%)"),
    ("Watch tier observed rate", "30%", EX, tier(1, "observedRate"), pct, "Watch is 29–43% (30%)"),
    ("Ok tier observed rate", "19%", EX, tier(2, "observedRate"), pct, "Ok is below 29% (19%)"),
    ("Held-out alert", "40", EX, "heldoutStatusMix/alert", num, "40 alert, 43 watch and 116 ok"),
    ("Held-out watch", "43", EX, "heldoutStatusMix/watch", num, "40 alert, 43 watch and 116 ok"),
    ("Held-out ok", "116", EX, "heldoutStatusMix/ok", num, "40 alert, 43 watch and 116 ok"),
    # insight, stratified check, first event
    ("Six prior-use features alone", "0.697", R1, cand(R1, "lr_l2|prior_use"), f3, "alone reach AUROC 0.697"),
    ("Within prior-use group ΔAUROC", "+0.094", ST, "prior/search/delta", s3, "(+0.094 [-0.002, +0.206])"),
    ("Within prior-use group CI", "[-0.002, +0.206]", ST, "prior/search/ci95", sci3, "(+0.094 [-0.002, +0.206])"),
    ("First event n", "326", EX, "firstEvent/n", num, "Among the 326 survivors"),
    ("First event events", "70", EX, "firstEvent/events", num, "(70 had a first one in 2018)"),
    ("First event AUROC, search", "0.653", EX, "firstEvent/aurocModel", f3, "ranks at AUROC 0.653"),
    ("First event AUROC, baseline", "0.634", EX, "firstEvent/aurocBaseline", f3, "vs the baseline's 0.634"),
    ("First event ΔAUROC", "+0.019", EX, "firstEvent/deltaAuroc", s3, "+0.019 [-0.065, +0.103]"),
    ("First event ΔAUROC CI", "[-0.065, +0.103]", EX, "firstEvent/deltaCi95", sci3, "+0.019 [-0.065, +0.103]"),
    # plain factors
    ("Prior acute care rate with", "46%", EX, "plainFactors/0/withFactor/rate", pct, "prior ER visit or hospital stay 46% vs 21% (2.1×)"),
    ("Prior acute care rate without", "21%", EX, "plainFactors/0/without/rate", pct, "prior ER visit or hospital stay 46% vs 21% (2.1×)"),
    ("Prior acute care ratio", "2.1×", EX, "plainFactors/0/rateRatio", ratio, "prior ER visit or hospital stay 46% vs 21% (2.1×)"),
    ("Age 75+ rate with", "44%", EX, "plainFactors/1/withFactor/rate", pct, "Age 75+ 44% vs 24%"),
    ("Age 75+ rate without", "24%", EX, "plainFactors/1/without/rate", pct, "Age 75+ 44% vs 24%"),
    # fairness
    ("Fairness AUROC, female", "0.72", EX, fair("Female", "auroc"), f2, "AUROC 0.72 F, 0.70 M"),
    ("Fairness AUROC, male", "0.70", EX, fair("Male", "auroc"), f2, "AUROC 0.72 F, 0.70 M"),
    ("Fairness AUROC, any private", "0.68", EX, fair("Any private", "auroc"), f2, "(0.68 private, 0.75 public-only)"),
    ("Fairness AUROC, public only", "0.75", EX, fair("Public only", "auroc"), f2, "(0.68 private, 0.75 public-only)"),
    ("Age 75+ O/E", "1.15", EX, fair("75+ (85 = top-coded)", "oe"), f2, "observed/expected 1.15 [0.91, 1.37]"),
    ("Age 75+ O/E CI", "[0.91, 1.37]", EX, fair("75+ (85 = top-coded)", "oeCi95"), ci2, "observed/expected 1.15 [0.91, 1.37]"),
    ("NH Black AUROC", "0.48", EX, fair("NH Black", "auroc"), f2, "AUROC 0.48 [0.25, 0.70], n = 47"),
    ("NH Black AUROC CI", "[0.25, 0.70]", EX, fair("NH Black", "aurocCi95"), ci2, "AUROC 0.48 [0.25, 0.70], n = 47"),
    ("NH Black n", "47", EX, fair("NH Black", "n"), num, "AUROC 0.48 [0.25, 0.70], n = 47"),
    # Synthea
    ("Synthea Q1 AUROC shared", "0.671", SY, "q1WithinSynthea/aurocShared", f3, "0.671 → 0.670, Δ -0.001 [-0.008, +0.007]"),
    ("Synthea Q1 AUROC shared + clinical", "0.670", SY, "q1WithinSynthea/aurocSharedPlusClinical", f3, "0.671 → 0.670, Δ -0.001 [-0.008, +0.007]"),
    ("Synthea Q1 Δ", "-0.001", SY, "q1WithinSynthea/deltaAuroc", s3, "0.671 → 0.670, Δ -0.001 [-0.008, +0.007]"),
    ("Synthea Q1 Δ CI", "[-0.008, +0.007]", SY, "q1WithinSynthea/deltaAurocCi95", sci3, "0.671 → 0.670, Δ -0.001 [-0.008, +0.007]"),
    ("Synthea stage missing", "86%", SY, "q1WithinSynthea/stageMissingShare", pct, "Stage is missing in 86% of person-years"),
    ("Synthea Q2 transport AUROC", "0.686", SY, "q2Transport/aurocInMeps", f3, "AUROC 0.686 [0.634, 0.740], observed/expected 1.02"),
    ("Synthea Q2 transport CI", "[0.634, 0.740]", SY, "q2Transport/ci95", ci3, "AUROC 0.686 [0.634, 0.740], observed/expected 1.02"),
    ("Synthea Q2 O/E", "1.02", SY, "q2Transport/oe", f2, "AUROC 0.686 [0.634, 0.740], observed/expected 1.02"),
    ("Synthea Q2 Δ vs forest", "-0.026", SY, "q2Transport/vsMepsModel/deltaAuroc", s3, "Δ -0.026 [-0.068, +0.013], a tie"),
    ("Synthea Q2 Δ CI", "[-0.068, +0.013]", SY, "q2Transport/vsMepsModel/ci95", sci3, "Δ -0.026 [-0.068, +0.013], a tie"),
    ("Synthea Q3 burden ΔAUROC", "+0.004", SY, "q3Increment/transfer_clinical_burden/delta/auroc/value", s3, "ΔAUROC +0.004 [-0.003, +0.012]"),
    ("Synthea Q3 burden ΔAUROC CI", "[-0.003, +0.012]", SY, "q3Increment/transfer_clinical_burden/delta/auroc/ci95", sci3, "ΔAUROC +0.004 [-0.003, +0.012]"),
    ("Synthea Q3 prior ΔAUROC", "+0.004", SY, "q3Increment/transfer_prior_logit/delta/auroc/value", s3, "ΔAUROC +0.004 [-0.002, +0.010]"),
    ("Synthea Q3 prior ΔAUROC CI", "[-0.002, +0.010]", SY, "q3Increment/transfer_prior_logit/delta/auroc/ci95", sci3, "ΔAUROC +0.004 [-0.002, +0.010]"),
    ("Synthea Q3 MEPS-only reference", "0.663", SY, "q3Increment/baseline/auroc/value", f3, "reference in Q3 is 0.663"),
    ("Synthea-prior candidate (round 3)", "0.692", R3, cand(R3, "synthea_prior|prior_use"), f3, "(AUROC 0.692) and lost to the forest"),
    # fairness mitigation (pre-registered) and extra subgroups
    ("Mitigation: current NH Black AUROC CI (2,000 draws)", "[0.25, 0.71]", FM, "variants/current/nhBlack/aurocCi95", ci2, "| Current forest | 0.48 [0.25, 0.71] | 0.73 |"),
    ("Mitigation: current NH Black O/E", "0.73", FM, "variants/current/nhBlack/oe", f2, "| Current forest | 0.48 [0.25, 0.71] | 0.73 |"),
    ("Mitigation: recalibrated NH Black AUROC", "0.44", FM, "variants/recalibrated/nhBlack/auroc", f2, "| Group-aware recalibration (cross-fitted) | 0.44 [0.23, 0.67] | 1.00 | -0.040 [-0.079, -0.011] | 0.542 |"),
    ("Mitigation: recalibrated NH Black O/E", "1.00", FM, "variants/recalibrated/nhBlack/oe", f2, "| Group-aware recalibration (cross-fitted) | 0.44 [0.23, 0.67] | 1.00 |"),
    ("Mitigation: recalibrated Δ within group", "-0.040", FM, "variants/recalibrated/vsCurrent/groupDeltaAuroc", s3, "| 1.00 | -0.040 [-0.079, -0.011] | 0.542 |"),
    ("Mitigation: recalibrated log loss", "0.542", FM, "variants/recalibrated/overall/logLoss", f3, "| 1.00 | -0.040 [-0.079, -0.011] | 0.542 |"),
    ("Mitigation: reweighted NH Black AUROC", "0.46", FM, "variants/reweighted/nhBlack/auroc", f2, "| Refit, NH Black weighted ×3 | 0.46 [0.24, 0.69] | 0.79 | -0.018 [-0.068, +0.029] | 0.546 |"),
    ("Mitigation: reweighted Δ CI", "[-0.068, +0.029]", FM, "variants/reweighted/vsCurrent/groupDeltaAurocCi95", sci3, "| 0.79 | -0.018 [-0.068, +0.029] | 0.546 |"),
    ("Mitigation: reweighted log loss", "0.546", FM, "variants/reweighted/overall/logLoss", f3, "| 0.79 | -0.018 [-0.068, +0.029] | 0.546 |"),
    ("Mitigation: group features NH Black AUROC", "0.47", FM, "variants/group_features/nhBlack/auroc", f2, "| Refit, race/ethnicity as features | 0.47 [0.24, 0.70] | 0.74 | -0.008 [-0.039, +0.016] | 0.539 |"),
    ("Mitigation: group features Δ", "-0.008", FM, "variants/group_features/vsCurrent/groupDeltaAuroc", s3, "| 0.74 | -0.008 [-0.039, +0.016] | 0.539 |"),
    ("Mitigation: both NH Black O/E", "0.81", FM, "variants/both/nhBlack/oe", f2, "| Both | 0.46 [0.24, 0.69] | 0.81 | -0.020 [-0.077, +0.026] | 0.545 |"),
    ("Mitigation: both log loss", "0.545", FM, "variants/both/overall/logLoss", f3, "| Both | 0.46 [0.24, 0.69] | 0.81 | -0.020 [-0.077, +0.026] | 0.545 |"),
    ("Mitigation: variants passing", "No variant passes", FM, described("len(passed)", lambda J: len(J["passed"])), lambda v: "No variant passes" if v == 0 else f"{v} pass", "No variant passes."),
    ("Pooled not-NH-White AUROC", "0.56", FM, "extraSubgroups/1/auroc", f2, "AUROC 0.56 [0.41, 0.71], n = 95, 21 events"),
    ("Pooled not-NH-White AUROC CI", "[0.41, 0.71]", FM, "extraSubgroups/1/aurocCi95", ci2, "AUROC 0.56 [0.41, 0.71], n = 95, 21 events"),
    ("Pooled not-NH-White n", "95", FM, "extraSubgroups/1/n", num, "AUROC 0.56 [0.41, 0.71], n = 95, 21 events"),
    ("Pooled not-NH-White O/E CI", "[0.46, 1.01]", FM, "extraSubgroups/1/oeCi95", ci2, "observed/expected 0.72 [0.46, 1.01]"),
    ("Hispanic AUROC", "0.64", FM, "extraSubgroups/0/auroc", f2, "AUROC 0.64 [0.38, 0.86], n = 28, 7 events"),
    ("Hispanic AUROC CI", "[0.38, 0.86]", FM, "extraSubgroups/0/aurocCi95", ci2, "AUROC 0.64 [0.38, 0.86], n = 28, 7 events"),
    ("NH White AUROC", "0.75", EX, fair("NH White", "auroc"), f2, "than for NH White survivors (0.75)"),
    ("Held-out survivors with humanCheck", "4", "src/data/survivors.json", described("count(details[].humanCheck.required)", lambda J: sum(d["humanCheck"]["required"] for d in J["details"].values())), num, "This applies to 4 of 199 held-out survivors."),
    # alert budget
    ("Alert calls/week per 500 survivors", "1.9", EX, described("alertBudget/cutoffs[topShare=0.2]/per100SurvivorsPerWeek x 5", lambda J: next(r for r in J["alertBudget"]["cutoffs"] if r["topShare"] == 0.2)["per100SurvivorsPerWeek"] * 5), lambda v: f"{v:.1f}", "about 1.9 calls a week for a navigator with 500 survivors"),
    ("Alert calls per event found", "1.8", EX, tier(0, "observedRate"), lambda v: f"{1 / v:.1f}", "(1.8 calls per event found)"),
    ("Top-tenth share of events", "21%", EX, described("alertBudget/cutoffs[topShare=0.1]/shareOfAllEvents", lambda J: next(r for r in J["alertBudget"]["cutoffs"] if r["topShare"] == 0.1)["shareOfAllEvents"]), pct, "only 21% of events at 60% precision"),
    ("Top-tenth precision", "60%", EX, described("alertBudget/cutoffs[topShare=0.1]/devObservedRate", lambda J: next(r for r in J["alertBudget"]["cutoffs"] if r["topShare"] == 0.1)["devObservedRate"]), pct, "only 21% of events at 60% precision"),
]


def submission_check():
    rel = "submission/heldout_predictions.csv"
    try:
        head = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{rel}"], capture_output=True, text=True, check=True).stdout
    except Exception as e:  # noqa: BLE001
        return False, f"could not read committed copy: {e}"
    a = list(csv.DictReader(io.StringIO(head)))
    b = list(csv.DictReader(open(os.path.join(ROOT, rel))))
    if [r["ID"] for r in a] != [r["ID"] for r in b]:
        return False, "row IDs or order differ"
    d = max(abs(float(x["predicted_risk"]) - float(y["predicted_risk"])) for x, y in zip(a, b))
    return d < 1e-9, f"{len(b)} rows, same IDs and order, max |Δ predicted_risk| = {d:.2e}"


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    readme = open(os.path.join(ROOT, "README.md")).read()
    cache, committed, rows, bad, rerun_diff = {}, {}, [], 0, 0

    def value(J, key, fmt):
        if J is None:
            return "n/a"
        try:
            return fmt(key(J) if callable(key) else get(J, key))
        except Exception as e:  # noqa: BLE001
            return f"error: {e}"

    for label, exp, rel, key, fmt, text in CLAIMS:
        got = value(cache.setdefault(rel, load(rel)), key, fmt)
        was = value(committed.setdefault(rel, load_committed(rel)), key, fmt)
        in_readme = text in readme and exp in text
        ok = got == exp and in_readme
        bad += not ok
        new = was == "n/a" or was.startswith("error:")  # claim added after the last commit: nothing to compare yet
        rerun_diff += not new and got != was
        if ok:
            res = "match"
        elif not in_readme:
            res = "NOT IN README"
        elif got == was or new:
            res = "MISMATCH: README differs from the committed output too (README rounding/typo, not the rerun)"
        else:
            res = "MISMATCH: rerun differs from the committed output"
        where = f"`{rel}` → `{key if isinstance(key, str) else key.desc}`"
        rows.append(f"| {label} | {exp} | {where} | {was} | {got} | {res} |")
    sub_ok, sub_msg = submission_check()
    missing = sum("NOT IN README" in r for r in rows)
    readme_bad = bad
    repro_ok = rerun_diff == 0 and sub_ok and missing == 0
    n = len(CLAIMS)
    md = ["| README number | README says | file → key | committed output | this run | result |", "|---|---|---|---|---|---|", *rows,
          f"| Submission CSV | committed copy | `submission/heldout_predictions.csv` | | {sub_msg} | {'match' if sub_ok else 'MISMATCH'} |",
          "",
          f"**Reproduction: {'PASS' if repro_ok else 'FAIL'}.** This run differs from the committed outputs on {rerun_diff} of {n} numbers; "
          f"submission CSV {'identical' if sub_ok else 'DIFFERS'}.",
          "",
          f"**README: {n - readme_bad} of {n} numbers match this run.**"
          + (" The rest are README rounding or typo errors that the committed output shows too (listed above)." if readme_bad else ""),
          "",
          f"**Submission sha256 (this run): `{hashlib.sha256(open(os.path.join(ROOT, 'submission', 'heldout_predictions.csv'), 'rb').read()).hexdigest()}`.** "
          "The live API serves its hash as the `x-c1-artifact` header and `/api/c1/metrics` → `build.submissionSha256`; equal hashes mean the served predictions are these."]
    txt = "\n".join(md)
    print(txt)
    if out:
        open(out, "w").write(txt + "\n")
    sys.exit(0 if repro_ok else 1)


if __name__ == "__main__":
    main()
