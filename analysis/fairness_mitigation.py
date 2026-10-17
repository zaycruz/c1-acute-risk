#!/usr/bin/env python3
"""Can we fix the weak ranking for NH Black survivors (AUROC 0.48, n=47, 11 events)? Pre-registered mitigation test.

Usage: uv run python -I analysis/fairness_mitigation.py [data/meps]     (run train.py first)
Writes analysis/out/fairness_mitigation.json, which export.py serves as /api/c1/metrics -> fairnessMitigation.

Written before running. Variants, all on train.py's folds (10x5 RepeatedStratifiedKFold, SEED), OOF averaged over repeats:
  current        the final forest, unchanged (reference; must equal oof.csv p_forest)
  recalibrated   group-aware recalibration: logit(p) + offset per race/ethnicity group (Hispanic, NH Black, NH White, other),
                 offsets fit on the current model's OOF predictions by 5-fold cross-fitting x 10 repeats (second stage
                 never sees the row it predicts). A monotone shift inside a group cannot change that group's AUROC; it
                 can only fix its calibration (O/E). Included because it is the standard first step.
  reweighted     refit with NH Black survivors weighted x3 (sample_weight; fixed in advance, not tuned)
  group_features refit with race/ethnicity indicators (Hispanic, NH Black, NH Asian/other) added to the 16 features
  both           reweighted + group_features
Pass (stated in advance): NH Black AUROC >= 0.60 AND the paired within-group dAUROC 95% CI above 0 AND overall log loss
no more than 0.005 worse than current. Paired bootstrap, 2,000 draws, resampled within the group for group metrics.
If nothing passes we keep the current model and ship a safeguard instead (export.py: humanCheck on NH Black alerts).
Also reports two subgroup rows the fairness table lacks: Hispanic (n=28) with its CI, and all survivors other than NH White
pooled (large enough to judge), and states that the MEPS extract has no language field.
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import final_features, subgroups  # noqa: E402
from train import N_REPEATS, N_SPLITS, SEED, make_models  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "out")
W_BLACK = 3.0
N_BOOT = 2000


def fit_predict(X, y, w, tr, te):
    m = clone(make_models()["forest"])
    kw = {} if w is None else {"calibratedclassifiercv__sample_weight": w[tr]}
    return m.fit(X.iloc[tr], y[tr], **kw).predict_proba(X.iloc[te])[:, 1]


def oof_for(X, y, w, splits):
    parts = Parallel(n_jobs=-1)(delayed(fit_predict)(X, y, w, tr, te) for tr, te in splits)
    P = np.zeros((N_REPEATS, len(y)))
    for i, ((_, te), p) in enumerate(zip(splits, parts)):
        P[i // N_SPLITS, te] = p
    return P.mean(axis=0)


def lg(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def recalibrate(y, p, grp):
    """Cross-fitted per-group intercept offsets on logit(p) (slope fixed at 1)."""
    D = pd.get_dummies(grp).astype(float).values
    out = np.zeros((10, len(y)))
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
    for i, (tr, te) in enumerate(rskf.split(np.zeros(len(y)), y)):
        b = _offset_fit(lg(p[tr]), D[tr], y[tr])  # logit(y) = logit(p) + D b
        out[i // 5, te] = 1 / (1 + np.exp(-(lg(p[te]) + D[te] @ b)))
    return out.mean(axis=0)


def _offset_fit(off, D, y, iters=50):
    """Newton steps for logistic regression with a fixed offset and no other intercept."""
    b = np.zeros(D.shape[1])
    for _ in range(iters):
        eta = off + D @ b
        mu = 1 / (1 + np.exp(-eta))
        g = D.T @ (y - mu)
        H = D.T @ (D * (mu * (1 - mu))[:, None]) + 1e-6 * np.eye(D.shape[1])
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def group_metrics(y, p, m, rng_seed=SEED):
    yi, pi = y[m], p[m]
    rg = np.random.default_rng(rng_seed)
    au, oe = [], []
    for _ in range(N_BOOT):
        j = rg.integers(0, len(yi), len(yi))
        if 0 < yi[j].sum() < len(j):
            au.append(roc_auc_score(yi[j], pi[j]))
        oe.append(yi[j].mean() / pi[j].mean())
    return {"n": int(m.sum()), "events": int(yi.sum()), "auroc": float(roc_auc_score(yi, pi)),
            "aurocCi95": [float(np.percentile(au, 2.5)), float(np.percentile(au, 97.5))],
            "oe": float(yi.mean() / pi.mean()), "oeCi95": [float(np.percentile(oe, 2.5)), float(np.percentile(oe, 97.5))]}


def paired(y, pa, pb, m):
    """Variant (pa) minus current (pb): within-group dAUROC, overall dAUROC and dLogLoss."""
    rg = np.random.default_rng(SEED)
    gi = np.where(m)[0]
    dg, da, dl = [], [], []
    for _ in range(N_BOOT):
        j = rg.integers(0, len(gi), len(gi))
        k = gi[j]
        if 0 < y[k].sum() < len(k):
            dg.append(roc_auc_score(y[k], pa[k]) - roc_auc_score(y[k], pb[k]))
        a = rg.integers(0, len(y), len(y))
        if 0 < y[a].sum() < len(a):
            da.append(roc_auc_score(y[a], pa[a]) - roc_auc_score(y[a], pb[a]))
        dl.append(log_loss(y[a], pa[a]) - log_loss(y[a], pb[a]))
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    return {"groupDeltaAuroc": float(roc_auc_score(y[m], pa[m]) - roc_auc_score(y[m], pb[m])), "groupDeltaAurocCi95": ci(dg),
            "deltaAuroc": float(roc_auc_score(y, pa) - roc_auc_score(y, pb)), "deltaAurocCi95": ci(da),
            "deltaLogLoss": float(log_loss(y, pa) - log_loss(y, pb)), "deltaLogLossCi95": ci(dl)}


def main():
    meps = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "meps")
    s17 = pd.read_csv(os.path.join(meps, "meps2017_survivors.csv")).set_index("ID")
    dev = pd.read_csv(os.path.join(meps, "meps2018_followup_dev.csv"))[["ID", "outcome_acute_care_2018"]].set_index("ID")
    ids = dev.index
    y = dev.outcome_acute_care_2018.values.astype(int)
    race = subgroups(s17.loc[ids]).race_ethnicity.values
    black = race == "NH Black"
    X = final_features(s17).loc[ids]
    Xg = X.assign(grp_hispanic=(race == "Hispanic").astype(float), grp_nh_black=black.astype(float),
                  grp_nh_asian_other=np.isin(race, ["NH Asian", "NH other/multiple"]).astype(float))
    w = np.where(black, W_BLACK, 1.0)
    splits = list(RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED).split(np.zeros(len(y)), y))

    ref = pd.read_csv(os.path.join(OUT, "oof.csv")).set_index("ID").loc[ids].p_forest.values
    P = {"current": oof_for(X, y, None, splits)}
    assert np.allclose(P["current"], ref, atol=1e-9), "current forest does not reproduce oof.csv"
    grp4 = np.where(np.isin(race, ["Hispanic", "NH Black", "NH White"]), race, "other")
    P["recalibrated"] = recalibrate(y, P["current"], grp4)
    P["reweighted"] = oof_for(X, y, w, splits)
    P["group_features"] = oof_for(Xg, y, None, splits)
    P["both"] = oof_for(Xg, y, w, splits)

    variants = {}
    for k, p in P.items():
        row = {"overall": {"auroc": float(roc_auc_score(y, p)), "logLoss": float(log_loss(y, p))},
               "nhBlack": group_metrics(y, p, black)}
        if k != "current":
            row["vsCurrent"] = paired(y, p, P["current"], black)
            v = row["vsCurrent"]
            row["passes"] = bool(row["nhBlack"]["auroc"] >= 0.60 and v["groupDeltaAurocCi95"][0] > 0 and v["deltaLogLoss"] <= 0.005)
        variants[k] = row
        print(f"{k:15s} overall AUROC {row['overall']['auroc']:.3f} logloss {row['overall']['logLoss']:.4f} | NH Black AUROC "
              f"{row['nhBlack']['auroc']:.2f} {np.round(row['nhBlack']['aurocCi95'], 2)} O/E {row['nhBlack']['oe']:.2f}"
              + (f" | dGroup {row['vsCurrent']['groupDeltaAuroc']:+.3f} {np.round(row['vsCurrent']['groupDeltaAurocCi95'], 3)}"
                 f" pass={row['passes']}" if k != "current" else ""))
    passed = [k for k, r in variants.items() if r.get("passes")]

    p0 = P["current"]
    extra = {"Hispanic": race == "Hispanic", "Not NH White (pooled: Hispanic, NH Black, NH Asian, NH other)": race != "NH White"}
    rows = [{"group": g, **group_metrics(y, p0, m)} for g, m in extra.items()]

    out = {
        "question": "Can a pre-registered mitigation fix the weak ranking for NH Black survivors (n=47, 11 events)?",
        "design": __doc__.split("Written before running. ")[1].split("Also reports")[0].strip(),
        "passCriterion": "NH Black AUROC >= 0.60, paired within-group dAUROC CI above 0, overall log loss no more than 0.005 worse",
        "weightNhBlack": W_BLACK,
        "variants": variants,
        "passed": passed,
        "decision": (f"Adopt {passed[0]}" if passed else
                     "No variant passes. Keep the current model; NH Black alerts carry a human check before outreach (humanCheck)."),
        "extraSubgroups": rows,
        "language": {"available": False,
                     "note": "The MEPS extract has no interview-language, English-proficiency or birthplace field (only RACETHX and HISPANX), "
                             "so we cannot test performance by language. Spanish- and Creole-speaking survivors are a main Miami population; "
                             "this is a known gap, not a pass."},
    }
    json.dump(out, open(os.path.join(OUT, "fairness_mitigation.json"), "w"), indent=2)
    print("decision:", out["decision"])
    for r in rows:
        print(f"{r['group'][:40]:40s} n {r['n']} events {r['events']} AUROC {r['auroc']:.2f} {np.round(r['aurocCi95'], 2)} O/E {r['oe']:.2f} {np.round(r['oeCi95'], 2)}")


if __name__ == "__main__":
    main()
