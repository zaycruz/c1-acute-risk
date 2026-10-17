#!/usr/bin/env python3
"""Bake model outputs into the Worker's JSON (src/data/survivors.json, src/data/metrics.json).

Usage: .venv/bin/python -I analysis/export.py [data/meps]   (run analysis/train.py and analysis/synthea.py first)
Roster = the 199 held-out survivors: real forward predictions, outcome unknown to us.
"""
import json
import os
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import FEATURE_LABELS, FINAL_LABELS, RAW_USE, domain_features, final_features, subgroups  # noqa: E402
from explain import contributions  # noqa: E402

LABELS = {**FEATURE_LABELS, **FINAL_LABELS}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "out")
AS_OF = "2017-12-31T00:00:00Z"

# kind, who acts, and what to suggest when the factor pushes risk up.
FACTOR_PLAYBOOK = {
    "er_visits_17": ("prior-acute-care", "care-team", "Review last year's ER visits for preventable causes; set a same-day call-back route before the ER."),
    "hosp_stays_17": ("prior-acute-care", "care-team", "Schedule a post-discharge style check-in and medication reconciliation."),
    "home_health_17": ("prior-acute-care", "care-team", "Confirm home health is still in place and who to call after hours."),
    "rx_fills_17": ("medications", "care-team", "Do a medication review (polypharmacy, side effects, adherence)."),
    "office_visits_17": ("care-intensity", "care-team", "Many visits last year: check care is coordinated across providers."),
    "physical_score": ("physical-function", "care-team", "Low physical function: consider PT/rehab referral and a falls check."),
    "poor_physical_rating": ("physical-function", "coach", "Ask what daily tasks are hard right now; agree one small activity goal."),
    "activity_limited": ("physical-function", "coach", "Activities limited by cancer: explore supports for daily tasks."),
    "pain": ("symptoms", "care-team", "Pain is raised: review the pain plan and how to reach the team before it escalates."),
    "fatigue": ("symptoms", "coach", "Fatigue is raised: pace activities, screen for sleep and anaemia with the care team."),
    "distress_k6": ("distress", "care-team", "Psychological distress: offer a distress screen follow-up and psycho-oncology referral."),
    "depression_phq2": ("distress", "care-team", "Positive depression screen: follow up with a PHQ-9 and offer support."),
    "mental_score": ("distress", "coach", "Low mental health score: check in on mood, sleep and support at home."),
    "fear_recurrence": ("distress", "coach", "Worry about recurrence: talk through what follow-up looks like and who to ask."),
    "financial_toxicity": ("financial-toxicity", "care-team", "Financial hardship reported: refer to a financial navigator / social worker."),
    "cost_delay": ("financial-toxicity", "care-team", "Care delayed for cost: check prescriptions and visits are affordable; navigator referral."),
    "uninsured": ("access", "care-team", "Uninsured: connect with enrolment help or charity care programmes."),
    "public_only": ("access", "care-team", "Public insurance only: check coverage for needed services and transport."),
    "low_income": ("access", "care-team", "Low income: screen for transport, food and housing needs."),
    "current_treatment": ("treatment", "care-team", "In active treatment: make sure they know the side-effect hotline and fever rules."),
    "recurrence": ("treatment", "care-team", "Cancer came back: confirm the current plan and symptom triage route."),
    "family_caregiver": ("support", "coach", "A family member provides care: check how the caregiver is coping."),
    "not_married": ("support", "coach", "May have less support at home: ask who helps them day to day."),
    "age": ("demographic", "care-team", "Older age: a lower bar for proactive check-ins is reasonable."),
    "hosp_nights_17": ("prior-acute-care", "care-team", "Nights in hospital last year: confirm a discharge follow-up plan and who to call first."),
    "outpatient_visits_17": ("care-intensity", "care-team", "Many hospital outpatient visits: check the plan is coordinated and one team owns follow-up."),
    "home_health_days_17": ("prior-acute-care", "care-team", "Many home health days: confirm home health is still in place and who to call after hours."),
    "spending_17": ("care-intensity", "care-team", "High care use last year: review what drove it and whether one team owns the plan."),
    "missed_work_days_17": ("symptoms", "coach", "Missed work for illness: ask which symptoms keep them from work and agree when to call the team."),
}
SHORT = {"er_visits_17": "ER visits last year", "hosp_stays_17": "hospital stays last year", "rx_fills_17": "many prescriptions",
         "office_visits_17": "many office visits", "home_health_17": "home health care", "physical_score": "low physical function",
         "poor_physical_rating": "poor self-rated health", "activity_limited": "activity limits", "pain": "pain", "fatigue": "fatigue",
         "distress_k6": "psychological distress", "depression_phq2": "depression symptoms", "mental_score": "low mental health score",
         "fear_recurrence": "worry about recurrence", "financial_toxicity": "financial hardship", "cost_delay": "cost-related care delays",
         "uninsured": "no insurance", "public_only": "public-only insurance", "low_income": "low income", "current_treatment": "active treatment",
         "recurrence": "recurrence", "family_caregiver": "caregiver needs", "not_married": "limited support at home", "age": "age",
         "hosp_nights_17": "nights in hospital last year", "outpatient_visits_17": "hospital outpatient visits",
         "home_health_days_17": "home health days", "spending_17": "high care use last year", "missed_work_days_17": "missed work for illness"}
NON_ACTIONABLE = {"female", "hispanic", "nh_black", "nh_asian_other", "ca_breast", "ca_colon", "ca_lung", "ca_prostate",
                  "n_cancer_types", "no_saq"}


def describe(f, raw, s):
    """Plain-language description of a survivor's own value for one factor."""
    v = raw[f]
    if f == "er_visits_17": return f"{int(round(np.expm1(v)))} ER visit(s) in 2017 (most survivors had none)"
    if f == "hosp_stays_17": return f"{int(round(np.expm1(v)))} hospital stay(s) in 2017"
    if f == "rx_fills_17": return f"{int(round(np.expm1(v)))} prescription fills in 2017"
    if f == "office_visits_17": return f"{int(round(np.expm1(v)))} office visits in 2017"
    if f == "home_health_17": return "Had home health care in 2017" if v == 1 else "No home health care in 2017"
    if f == "physical_score": return f"Physical health score {v:.0f} (US average is 50; lower is worse)"
    if f == "mental_score": return f"Mental health score {v:.0f} (US average is 50; lower is worse)"
    if f == "distress_k6": return f"Distress score {v:.0f} of 24 (5+ = moderate, 13+ = serious)"
    if f == "depression_phq2": return f"Depression screen {v:.0f} of 6 (3+ = positive screen)"
    if f == "pain": return f"Average pain {v:.0f} of 10 in the last week"
    if f == "fatigue": return f"Fatigue {v:.0f} of 5 in the last week ({['', 'none', 'mild', 'moderate', 'severe', 'very severe'][int(v)]})"
    if f == "poor_physical_rating": return f"Rates physical health {['', 'excellent', 'very good', 'good', 'fair', 'poor'][int(v)]}"
    if f == "fear_recurrence": return f"Worry about cancer coming back: {['', 'not at all', 'a little', 'somewhat', 'quite a bit', 'very much'][int(v)]}"
    if f == "financial_toxicity": return f"{v:.0f} of 7 financial hardship items (debt, unpaid bills, worry about bills)"
    if f == "cost_delay": return f"Delayed or skipped {v:.0f} kind(s) of care because of cost" if v else "No care delayed for cost"
    if f == "age": return f"Age {v:.0f}" + (" or older (top-coded)" if v >= 85 else "")
    if f == "current_treatment": return "Currently in cancer treatment" if v == 1 else "Not currently in treatment"
    if f == "recurrence": return "Told the cancer came back" if v == 1 else "No recurrence reported"
    if f == "activity_limited": return "Activities limited by cancer" if v == 1 else "Activities not limited by cancer"
    if f == "not_married": return "Not married" if v == 1 else "Married"
    if f == "low_income": return "Family income under 200% of poverty" if v == 1 else "Family income 200%+ of poverty"
    if f == "public_only": return "Public insurance only (Medicare/Medicaid)" if v == 1 else "Has private insurance or none"
    if f == "uninsured": return "Uninsured all of 2017" if v == 1 else "Insured in 2017"
    if f == "family_caregiver": return "A family member provides care" if v == 1 else "No family caregiver reported"
    if f == "hosp_nights_17": return f"{int(round(np.expm1(v)))} night(s) in hospital in 2017"
    if f == "outpatient_visits_17": return f"{int(round(np.expm1(v)))} hospital outpatient visit(s) in 2017"
    if f == "home_health_days_17": return f"{int(round(np.expm1(v)))} home health day(s) in 2017"
    if f == "spending_17": return f"${int(round(np.expm1(v), -2)):,} total health spending in 2017 (median survivor about $6,700)"
    if f == "missed_work_days_17": return f"{int(round(np.expm1(v)))} work day(s) missed for illness in 2017"
    return f"{LABELS[f]}: {'yes' if v == 1 else 'no' if v == 0 else v}"


def univariate_factors(Xd, y):
    """Observed 2018 acute-care rates on the dev set for plain splits a care team understands."""
    splits = [
        ("ER visit or hospital stay in 2017", (Xd.er_visits_17 > 0) | (Xd.hosp_stays_17 > 0)),
        ("Physical health score under 40", Xd.physical_score < 40),
        ("Fair or poor self-rated physical health", Xd.poor_physical_rating >= 4),
        ("Pain 5 or more of 10", Xd.pain >= 5),
        ("Moderate+ fatigue", Xd.fatigue >= 3),
        ("Distress K6 5 or more", Xd.distress_k6 >= 5),
        ("Positive depression screen (PHQ-2 3+)", Xd.depression_phq2 >= 3),
        ("2+ financial hardship items", Xd.financial_toxicity >= 2),
        ("Delayed care because of cost", Xd.cost_delay >= 1),
        ("Currently in cancer treatment", Xd.current_treatment == 1),
        ("Age 75 or older", Xd.age >= 75),
        ("Public insurance only", Xd.public_only == 1),
        ("20+ prescription fills in 2017", Xd.rx_fills_17 >= np.log1p(20)),
    ]
    rows = []
    for label, m in splits:
        m = m.fillna(False).values
        n1, n0 = int(m.sum()), int((~m).sum())
        r1, r0 = float(y[m].mean()), float(y[~m].mean())
        rows.append({"factor": label, "withFactor": {"n": n1, "rate": r1}, "without": {"n": n0, "rate": r0},
                     "rateRatio": r1 / r0 if r0 else None})
    rows.sort(key=lambda r: -(r["rateRatio"] or 0))
    return rows


def _boot_ci(fn, n, seed=20261017, draws=2000):
    rg = np.random.default_rng(seed)
    v = []
    for _ in range(draws):
        i = rg.integers(0, n, n)
        r = fn(i)
        if r is not None:
            v.append(r)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], float(np.mean(np.array(v) > 0))


def model_search(y):
    """Honest estimate of the final model: nested CV of the whole search (the 10x5 CV numbers are post-selection)."""
    N = json.load(open(os.path.join(ROOT, "runs", "autoresearch", "round-nested.json")))
    oof = pd.read_csv(os.path.join(ROOT, "runs", "autoresearch", "round-nested-oof.csv"))
    yy = oof.y.values
    k = int(round(0.2 * len(yy)))
    top = {c: int(yy[np.argsort(-oof[c].values)[:k]].sum()) for c in ("procedure", "baseline", "submitted")}
    calls = {c: {"n": int((oof[c] >= 0.5).sum()), "cameTrue": float(yy[oof[c].values >= 0.5].mean())} for c in ("procedure", "baseline", "submitted")}
    return {"note": "Nested CV: the whole 37-candidate search re-run inside each of 10 outer folds, so the scored model never saw its test fold. "
                    "This is the unbiased estimate of what the chosen model does on new survivors.",
            "candidates": len(N["candidatePool"]), "outerFolds": N["outerFolds"], "picks": N["picks"],
            "auroc": {"search": N["procedure"]["auroc"], "baseline": N["baseline"]["auroc"], "previous": N["submittedModel"]["auroc"]},
            "logLoss": {"search": N["procedure"]["logLoss"], "baseline": N["baseline"]["logLoss"], "previous": N["submittedModel"]["logLoss"]},
            "vsBaseline": N["procedureVsBaseline"], "vsPrevious": N["procedureVsSubmitted"],
            "top20Events": {"of": int(yy.sum()), "flagged": k, **top},
            "callsAt50": calls,
            "powerNote": "With 466 survivors and 134 events an AUROC gain needs to be about +0.056 to clear a 95% CI; "
                         "the held-out set (199, about 57 events) has an AUROC standard error of about 0.04."}


def first_event(Xd, y):  # y in dev order
    """Alternative target: among survivors with no ER visit or hospital stay in 2017, who has a FIRST one in 2018?"""
    # nested-CV OOF (unbiased for the search); rows are in dev order, which the label check below guards
    oof = pd.read_csv(os.path.join(ROOT, "runs", "autoresearch", "round-nested-oof.csv"))
    assert (oof.y.values == y).all(), "nested OOF rows out of dev order"
    m = ((Xd.er_visits_17.fillna(0) == 0) & (Xd.hosp_stays_17.fillna(0) == 0)).values
    yy = oof.y.values[m]
    pf, pb = oof.procedure.values[m], oof.baseline.values[m]
    from sklearn.metrics import roc_auc_score
    d = lambda i: roc_auc_score(yy[i], pf[i]) - roc_auc_score(yy[i], pb[i]) if 0 < yy[i].sum() < len(i) else None
    ci, pb_ = _boot_ci(d, len(yy))
    return {"definition": "Survivors with no ER visit or hospital stay in 2017; outcome = first acute care in 2018",
            "estimate": "nested CV of the model search (runs/autoresearch/round-nested-oof.csv), not the post-selection 10x5 CV",
            "n": int(m.sum()), "events": int(yy.sum()), "rate": float(yy.mean()),
            "aurocModel": float(roc_auc_score(yy, pf)), "aurocBaseline": float(roc_auc_score(yy, pb)),
            "deltaAuroc": float(roc_auc_score(yy, pf) - roc_auc_score(yy, pb)), "deltaCi95": ci, "pBetter": pb_,
            "why": "Prior acute care explains most of the ranking on the full target (the 2017 repeat users are easy to find). "
                   "Finding the first event is the harder, more useful job for prevention."}


def flag_fairness(rows):
    """Plain flag + sentence per fairness group (shared by the metrics and each survivor's panel)."""
    for g in rows:
        g["flag"] = ("too-small" if g["tooSmall"] else
                     "weak-ranking" if g["auroc"] is not None and g["auroc"] < 0.6 else
                     "under-predicted" if g["oeCi95"][0] > 1 else "over-predicted" if g["oeCi95"][1] < 1 else "ok")
        g["text"] = {"too-small": f"{g['group']}: only {g['n']} people ({g['positives']} events), too few to judge",
                     "weak-ranking": f"{g['group']}: the model ranks risk poorly (AUROC {g['auroc']:.2f}, n = {g['n']}); use clinical judgement",
                     "under-predicted": f"{g['group']}: real risk ran higher than predicted ({g['oe']:.2f}x)",
                     "over-predicted": f"{g['group']}: real risk ran lower than predicted ({g['oe']:.2f}x)",
                     "ok": f"{g['group']}: works about as well as overall (AUROC {g['auroc']:.2f})"}[g["flag"]]


def add_display(m):
    """Plain-language, ready-to-render text for apps (Coach Console). Every number here comes from the fields above."""
    P = lambda v: f"{round(v * 100)}%"
    for r in m["plainFactors"]:
        r["text"] = (f"{r['factor']}: {P(r['withFactor']['rate'])} had an ER visit or hospital stay in 2018, vs {P(r['without']['rate'])} without it"
                     + (f" ({r['rateRatio']:.1f}x)" if r["rateRatio"] and abs(r["rateRatio"] - 1) >= 0.15 else " (no real difference)"))
    m["tiers"]["source"] = "development survivors (466), out-of-fold: each person scored by a model that never saw them"
    word = {"alert": "Alert", "watch": "Watch", "ok": "On track"}
    for t in m["tiers"]["tiers"]:
        t["text"] = (f"{word[t['status']]} ({P(t['riskFrom'])}+ risk): {P(t['observedRate'])} of {t['n']} development survivors had an ER visit or hospital stay"
                     if t["status"] == "alert" else
                     f"{word[t['status']]} ({P(t['riskFrom'])}-{P(t['riskTo'])}): {P(t['observedRate'])} of {t['n']} had one" if t["status"] == "watch" else
                     f"{word[t['status']]} (under {P(t['riskTo'])}): {P(t['observedRate'])} of {t['n']} had one")
    flag_fairness(m["fairness"])
    S, FE, F = m["modelSearch"], m["firstEvent"], m["finalModel"]["key"]
    top = next(t for t in m["tiers"]["tiers"] if t["status"] == "alert")
    flagged = [g["text"] for g in m["fairness"] if g["flag"] in ("weak-ranking", "under-predicted", "over-predicted")]
    m["display"] = {
        "note": "Plain-language summary for apps. Show headline, keyNumbers and howSure; put limits next to any risk number.",
        "headline": f"Flags who may need the ER or hospital next year. Of the people it puts on alert, about {P(top['observedRate'])} did; the average is {P(m['data']['devPositives'] / m['data']['devSurvivors'])}.",
        "keyNumbers": [
            {"value": P(top["observedRate"]), "label": "of alert-tier survivors had an ER visit or hospital stay", "sub": f"average survivor {P(m['data']['devPositives'] / m['data']['devSurvivors'])}"},
            {"value": f"{S['top20Events']['procedure']} of {S['top20Events']['of']}", "label": "events caught by calling the top fifth", "sub": f"the organisers' baseline catches {S['top20Events']['baseline']}"},
            {"value": P(S["callsAt50"]["procedure"]["cameTrue"]), "label": "of 50%+ risk calls came true", "sub": f"baseline {P(S['callsAt50']['baseline']['cameTrue'])}"},
            {"value": f"{S['auroc']['search']:.2f}", "label": "ranking quality (AUROC; 0.5 = coin flip, 1 = perfect)", "sub": f"baseline {S['auroc']['baseline']:.2f}; gap may be chance"},
        ],
        "howSure": [
            "The risk numbers are well calibrated: when it says 30%, about 30% of those people had an ER visit or hospital stay.",
            f"It ranks people somewhat better than the organisers' baseline (AUROC {S['auroc']['search']:.2f} vs {S['auroc']['baseline']:.2f}), but with 466 survivors that gap could be chance.",
            "All numbers are scored on people the model never saw (nested cross-validation).",
        ],
        "insight": "Heavy care use last year (ER visits, hospital nights, many prescriptions and visits) is the strongest sign of acute care next year. It marks need; it is not something to change directly.",
        "nextQuestion": (f"Who will have a FIRST ER visit or hospital stay? Of {FE['n']} survivors with none in 2017, {FE['events']} had one in 2018; "
                         f"no model finds them much better than the baseline yet (AUROC {FE['aurocModel']:.2f} vs {FE['aurocBaseline']:.2f})."),
        "limits": ["Associations, not causes: the factors flag who may need help; changing one is not proven to prevent an ER visit.",
                   "Built from survey answers only. The synthetic clinical records (Synthea) did not improve it and share no patient key with the survey."]
                  + flagged,
        "perSurvivor": "Each survivor's panel has headline, summary, evidence[] (top drivers in plain words, kind = topic), recommendations[] (audience = care-team | coach | survivor) and caveat (always show it with the risk).",
    }


def main():
    meps = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "meps")
    s17 = pd.read_csv(os.path.join(meps, "meps2017_survivors.csv")).set_index("ID")
    dev = pd.read_csv(os.path.join(meps, "meps2018_followup_dev.csv"))[["ID", "outcome_acute_care_2018"]].set_index("ID")
    held = pd.read_csv(os.path.join(meps, "heldout_ids.csv"))[["ID"]]
    M = json.load(open(os.path.join(OUT, "metrics_meps.json")))
    syn_path = os.path.join(OUT, "synthea.json")
    SYN = json.load(open(syn_path)) if os.path.exists(syn_path) else None
    model = pickle.load(open(os.path.join(OUT, "model.pkl"), "rb"))["final"]
    sub = pd.read_csv(os.path.join(ROOT, "submission", "heldout_predictions.csv")).set_index("ID")

    Xd = domain_features(s17)
    Xf = final_features(s17)
    contrib = contributions(model, Xf)  # TreeSHAP, calibrated log-odds scale (analysis/explain.py)
    risk = pd.Series(model.predict_proba(Xf)[:, 1], index=Xf.index)
    Xall = Xd.join(Xf[list(RAW_USE)])
    assert np.allclose(risk.loc[sub.index].round(6), sub.predicted_risk, atol=1e-6), "export drifted from submission"

    T = M["tiers"]
    flag_fairness(M["fairness"])
    FAIR = {(r["attribute"], r["group"]): r for r in M["fairness"]}
    base_rate = M["positives_dev"] / M["n_dev"]
    groups = subgroups(s17)

    def status_of(p):
        return "alert" if p >= T["alert"] else "watch" if p >= T["watch"] else "ok"

    tier_rate = {t["status"]: t["observedRate"] for t in T["tiers"]}
    roster, details = [], {}
    for sid in held.ID:
        x, c, p = Xall.loc[sid], contrib.loc[sid], float(risk.loc[sid])
        st = status_of(p)
        sex = "F" if x.female == 1 else "M"
        cancers = [n for n, col in (("breast", "ca_breast"), ("colon", "ca_colon"), ("lung", "ca_lung"), ("prostate", "ca_prostate")) if x[col] == 1]
        other = []
        for col, n in (("CABLADDR", "bladder"), ("CACERVIX", "cervix"), ("CALYMPH", "lymphoma"), ("CAMELANO", "melanoma"),
                       ("CASKINNM", "skin (non-melanoma)"), ("CASKINDK", "skin"), ("CAUTERUS", "uterus"), ("CAOTHER", "other")):
            if s17.loc[sid, col] == 1:
                other.append(n)
        ctypes = cancers + other
        age = int(x.age) if not np.isnan(x.age) else None
        display = f"{sid} · {age}{sex} · {ctypes[0] if ctypes else 'cancer'}"

        # drivers: raise risk, actionable, observed (not missing-indicators), at least 0.05 logit
        ranked = [(f, v) for f, v in c.sort_values(ascending=False).items() if not f.startswith("missing:")]
        up = [(f, v) for f, v in ranked if v > 0.02 and f not in NON_ACTIONABLE and not np.isnan(x[f])][:4]
        down = [(f, v) for f, v in reversed(ranked) if v < -0.05 and f not in NON_ACTIONABLE and not np.isnan(x[f])][:2]
        # spending summarises all care use; name a more specific driver in the headline when there is one
        lead_f = next((f for f, _ in up if f != "spending_17"), up[0][0]) if up else None
        lead = SHORT.get(lead_f, LABELS[lead_f].split(" (")[0].lower()) if lead_f else None
        pct = round(p * 100)
        if st == "alert":
            headline = f"Acute care risk {pct}% for 2018 (high), driven by {lead}" if lead else f"Acute care risk {pct}% for 2018 (high)"
        elif st == "watch":
            headline = f"Acute care risk {pct}% for 2018 (raised), mostly from {lead}" if lead else f"Acute care risk {pct}% for 2018 (raised)"
        else:
            headline = f"Acute care risk {pct}% for 2018, below the {round(base_rate * 100)}% average"
        evidence = [{"kind": "model", "text": f"Predicted chance of an ER visit or hospital stay in 2018: {pct}%. "
                     f"In the {st} tier, {round(tier_rate[st] * 100)}% of past survivors had one."}]
        for f, v in up:
            evidence.append({"kind": FACTOR_PLAYBOOK.get(f, ("other",))[0], "text": describe(f, x, s17.loc[sid]) + " (raises risk)",
                             "feature": f, "logitContribution": round(float(v), 3)})
        for f, v in down:
            evidence.append({"kind": FACTOR_PLAYBOOK.get(f, ("other",))[0], "text": describe(f, x, s17.loc[sid]) + " (lowers risk)",
                             "feature": f, "logitContribution": round(float(v), 3)})
        recs = []
        if st == "alert":
            recs.append({"audience": "care-team", "text": "Add to the proactive outreach list: a nurse call in the next 2 weeks and a clear same-day contact route instead of the ER."})
        elif st == "watch":
            recs.append({"audience": "coach", "text": "Raise at the next coaching call and check the top drivers below; escalate if symptoms are worsening."})
        else:
            recs.append({"audience": "coach", "text": "Routine follow-up. No extra outreach suggested by this model."})
        seen = set()
        for f, _ in up:
            if f in FACTOR_PLAYBOOK and FACTOR_PLAYBOOK[f][0] not in seen:  # one recommendation per kind
                recs.append({"audience": FACTOR_PLAYBOOK[f][1], "text": FACTOR_PLAYBOOK[f][2]})
                seen.add(FACTOR_PLAYBOOK[f][0])
        if st != "ok":
            recs.append({"audience": "survivor", "text": "If a symptom is getting worse, call your cancer care team first: they can often help the same day without an ER visit."})
        summary = (f"{pct}% predicted chance of an ER visit or hospital stay in 2018 (average survivor {round(base_rate * 100)}%). "
                   f"Status {st}: alert from {round(T['alert'] * 100)}%, watch from {round(T['watch'] * 100)}%. "
                   + ("Main drivers: " + "; ".join(describe(f, x, None) for f, _ in up[:3]) + "." if up else "No single factor stands out."))
        g = groups.loc[sid]
        profile = {
            "age": age, "sex": "female" if sex == "F" else "male", "raceEthnicity": g.race_ethnicity, "insurance2017": g.insurance,
            "cancerTypes": ctypes, "currentTreatment": {1.0: "yes", 0.0: "no"}.get(x.current_treatment, "unknown"),
            "region": {1: "Northeast", 2: "Midwest", 3: "South", 4: "West"}.get(int(s17.loc[sid, "REGION17"]), "unknown"),
            "dataSource": "MEPS 2017 survey (real survivor, ID reassigned by organisers)",
        }
        charts = {
            "risk": {"value": round(p, 4), "baseRate": round(base_rate, 4), "watchFrom": T["watch"], "alertFrom": T["alert"]},
            "drivers": [{"label": LABELS[f].split(" (")[0], "logitContribution": round(float(v), 3)} for f, v in up + down],
            "scores": {k: (None if np.isnan(x[k]) else round(float(x[k]), 1)) for k in
                       ("physical_score", "mental_score", "distress_k6", "depression_phq2", "pain", "fatigue", "financial_toxicity", "cost_delay")},
            "use2017": {"erVisits": int(max(s17.loc[sid, "ERTOT17"], 0)), "hospitalStays": int(max(s17.loc[sid, "IPDIS17"], 0)),
                        "officeVisits": int(max(s17.loc[sid, "OBTOTV17"], 0)), "rxFills": int(max(s17.loc[sid, "RXTOT17"], 0))},
        }
        caveat = ("Association, not cause: these factors flag who may need help; changing one is not proven to prevent an ER visit. "
                  "Risk is from survey answers only (clinical records did not improve it).")
        if x.no_saq == 1:
            caveat += " This survivor skipped the health questionnaire, so mental/physical scores were filled with typical values."
        if g.race_ethnicity in ("Hispanic", "NH Asian", "NH other/multiple") or g.insurance == "Uninsured":
            caveat += f" Few {g.race_ethnicity if g.insurance != 'Uninsured' else 'uninsured'} survivors in the training data: treat this estimate with extra caution."
        for attr, grp in (("race_ethnicity", g.race_ethnicity), ("age", g.age)):
            fr = FAIR.get((attr, grp))
            if not fr or fr["tooSmall"]:
                continue
            if fr["auroc"] is not None and fr["auroc"] < 0.6:
                caveat += (f" For {grp} survivors this model ranked risk poorly on development data (AUROC {fr['auroc']:.2f} "
                           f"[{fr['aurocCi95'][0]:.2f}, {fr['aurocCi95'][1]:.2f}], n = {fr['n']}): rely on clinical judgement.")
            if fr["oeCi95"][0] > 1:
                caveat += f" The model under-predicted acute care for {grp} survivors (observed {fr['oe']:.2f}x predicted): the true risk may be higher."
            if fr["oeCi95"][1] < 1:
                caveat += f" The model over-predicted acute care for {grp} survivors (observed {fr['oe']:.2f}x predicted)."
        # Console display fields (limits agreed with t-0003): riskWords <= 60, forEllie <= 160 incl. the caveat.
        k10 = max(1, min(9, round(p * 10)))
        lead_word = {"alert": "Higher than most", "watch": "Above average", "ok": "Below average"}[st]
        risk_words = f"{lead_word}: about {k10} in 10 like them had one"
        flags = []
        for attr, grp in (("race_ethnicity", g.race_ethnicity), ("age", g.age), ("insurance", g.insurance), ("cancer_type", g.cancer_type)):
            fr = FAIR.get((attr, grp))
            if fr and fr.get("flag", "ok") != "ok":
                flags.append({"attribute": attr, "group": grp, "flag": fr["flag"], "text": fr["text"]})
        weak = next((f for f in flags if f["flag"] in ("weak-ranking", "under-predicted", "over-predicted")), None)
        small = next((f for f in flags if f["flag"] == "too-small"), None)
        tail = (f" Less reliable for {weak['group']} survivors." if weak else f" Few {small['group']} survivors in training." if small else "") + " Association, not cause."
        driver = f", mainly {lead}" if lead and st != "ok" else ""
        for_ellie = f"Hospital risk {pct}% next year ({ {'alert': 'high', 'watch': 'raised', 'ok': 'low'}[st]}; average {round(base_rate * 100)}%){driver}.{tail}"
        if len(for_ellie) > 160:
            for_ellie = f"Hospital risk {pct}% next year{driver}.{tail}"
        d = {"survivorId": f"c1-{sid}", "displayName": display, "status": st, "headline": headline, "summary": summary,
             "risk": round(p, 4), "thresholds": {"alert": T["alert"], "watch": T["watch"]},
             "riskWords": risk_words, "forEllie": for_ellie, "fairnessFlags": flags,
             "evidence": evidence, "recommendations": recs, "charts": charts, "profile": profile, "caveat": caveat}
        details[f"c1-{sid}"] = d
        roster.append({"survivorId": d["survivorId"], "displayName": display, "status": st, "headline": headline,
                       "updatedAt": AS_OF, "_risk": p})
    order = {"alert": 0, "watch": 1, "ok": 2}
    roster.sort(key=lambda r: (order[r["status"]], -r["_risk"]))
    for r in roster:
        r.pop("_risk")

    y = dev.outcome_acute_care_2018.loc[Xd.loc[dev.index].index].values
    metrics = {
        "asOf": AS_OF,
        "outcome": M["outcome"],
        "data": {"devSurvivors": M["n_dev"], "devPositives": M["positives_dev"], "heldoutSurvivors": M["n_heldout"],
                 "predictorsFrom": "2017 MEPS only (2018 file used for the outcome column only)"},
        "validation": M["validation"],
        "finalModel": {"key": M["finalModel"],
                       "name": "Random forest (300 trees, min leaf 10) with sigmoid calibration, on 16 features: 2017 care use "
                               "(ER, hospital stays and nights, office, outpatient, home health, prescriptions, spending), age, "
                               "physical and mental health scores, distress, depression screen, self-rated health, missed work days",
                       "chosenBy": "nested cross-validation of a 37-candidate model search (runs/autoresearch): it won 6 of 10 outer folds",
                       "explanations": "TreeSHAP per survivor, converted to calibrated log-odds (analysis/explain.py)",
                       "previous": "L2 logistic regression on 34 survey-domain features (the first submission)"},
        "metrics": M["metrics"], "deltaVsBaseline": M["deltaVsBaseline"], "deltaVsPrevious": M["deltaVsPrevious"],
        "modelSearch": model_search(y),
        "firstEvent": first_event(Xd.loc[dev.index], y),  # nested-CV estimate
        "calibrationCurve": M["calibrationCurve"],
        "tiers": M["tiers"],
        "fairness": M["fairness"], "fairnessBaseline": M["fairnessBaseline"],
        "factors": [f for f in M["factors"] if not f["feature"].startswith("missing:")][:16],
        "plainFactors": univariate_factors(Xd.loc[dev.index], y),
        "clinicalRecords": SYN["verdict"] if SYN else {"verdict": "pending", "detail": "Synthea analysis not run yet."},
        "clinicalRecordsDetail": SYN,
        "heldoutStatusMix": {s: sum(r["status"] == s for r in roster) for s in order},
        "caveats": [
            "Associations, not causes. Prior acute care and poor physical function dominate; they mark need, not levers.",
            "Small data: 466 development survivors, 134 with the outcome. The ranking gain over the baseline (nested CV +0.04) is not statistically significant; the gain in probability quality (log loss, Brier) is.",
            "Subgroups with n < 30 or < 10 events (Hispanic, NH Asian, NH other, uninsured, colon, lung) are too small to judge.",
            "MEPS is a US national sample; the Synthea clinical records are synthetic and resemble South Florida. Nothing from Synthea is evidence about real patients.",
        ],
    }
    add_display(metrics)
    os.makedirs(os.path.join(ROOT, "src", "data"), exist_ok=True)
    json.dump({"asOf": AS_OF, "roster": roster, "details": details}, open(os.path.join(ROOT, "src", "data", "survivors.json"), "w"))
    json.dump(metrics, open(os.path.join(ROOT, "src", "data", "metrics.json"), "w"))
    print("roster", len(roster), metrics["heldoutStatusMix"])
    print(json.dumps(details[roster[0]["survivorId"]], indent=1)[:2500])
    for r in metrics["plainFactors"]:
        print(f"  {r['factor']:42s} {r['withFactor']['rate']:.2f} (n={r['withFactor']['n']}) vs {r['without']['rate']:.2f}  RR {r['rateRatio']:.2f}")


if __name__ == "__main__":
    main()
