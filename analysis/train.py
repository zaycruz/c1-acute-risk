#!/usr/bin/env python3
"""C1: predict acute care (any ER visit or hospital stay) in 2018 from 2017 MEPS answers.

Usage: .venv/bin/python -I analysis/train.py [data/meps]
Writes analysis/out/{oof.csv, metrics_meps.json, model.pkl} and submission/heldout_predictions.csv.

Validation: 10 x repeated stratified 5-fold CV, patient level (one row per survivor). Every model,
including the organisers' baseline, is scored on the same folds. Hyperparameters are tuned inside
each training fold (LogisticRegressionCV), never on the held-out fold. Out-of-fold (OOF) predictions are
averaged over the 10 repeats per survivor; CIs are a 2000-sample patient bootstrap of those OOF predictions,
and the model-vs-baseline differences are paired (same bootstrap sample for both).
"""
import json
import warnings
warnings.filterwarnings("ignore")
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import FINAL_LABELS, baseline_features, domain_features, final_features, subgroups  # noqa: E402
from explain import contributions  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "out")
SEED = 20261017
N_SPLITS, N_REPEATS, N_BOOT = 5, 10, 2000


def make_models():
    return {
        "baseline": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                  LogisticRegression(C=0.3, max_iter=2000)),
        "logistic": make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                                  LogisticRegressionCV(Cs=np.logspace(-3, 0, 10), cv=StratifiedKFold(5, shuffle=True, random_state=1),
                                                       scoring="neg_log_loss", max_iter=5000)),
        "gbm_calibrated": CalibratedClassifierCV(
            HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=25,
                                           l2_regularization=1.0, random_state=0),
            method="sigmoid", cv=5),
        # Final model: the pick of the nested-CV model search (runs/autoresearch/round-nested.json, 6 of 10 outer folds).
        "forest": make_pipeline(SimpleImputer(strategy="median", add_indicator=True), CalibratedClassifierCV(
            RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", n_jobs=1, random_state=0),
            method="sigmoid", cv=5)),
    }


FEATURESETS = {"baseline": "baseline", "logistic": "domain", "gbm_calibrated": "domain", "forest": "final"}
FINAL = "forest"


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def cal_intercept_slope(y, p):
    """Calibration slope (1 = ideal) and calibration-in-the-large intercept (0 = ideal)."""
    lp = logit(p).reshape(-1, 1)
    slope = LogisticRegression(C=1e6, max_iter=1000).fit(lp, y).coef_[0, 0]
    # intercept with slope fixed at 1: solve via offset by Newton steps
    a = 0.0
    for _ in range(50):
        q = 1 / (1 + np.exp(-(lp[:, 0] + a)))
        a += np.sum(y - q) / np.sum(q * (1 - q))
    return float(a), float(slope)


def metric_block(y, p):
    a, s = cal_intercept_slope(y, p)
    return {"auroc": roc_auc_score(y, p), "auprc": average_precision_score(y, p), "brier": brier_score_loss(y, p), "log_loss": log_loss(y, p),
            "cal_intercept": a, "cal_slope": s, "mean_pred": float(np.mean(p)), "obs_rate": float(np.mean(y))}


def bootstrap(y, preds, rng, n=N_BOOT, ref="baseline"):
    """preds: {name: p}. Returns per-model CIs and paired differences vs the reference model."""
    names = list(preds)
    stats = {k: [] for k in names}
    diffs = {k: [] for k in names if k != ref}
    idx_all = np.arange(len(y))
    for _ in range(n):
        idx = rng.choice(idx_all, len(y), replace=True)
        if y[idx].min() == y[idx].max():
            continue
        b = {k: metric_block(y[idx], preds[k][idx]) for k in names}
        for k in names:
            stats[k].append(b[k])
        for k in diffs:
            diffs[k].append({m: b[k][m] - b[ref][m] for m in ("auroc", "auprc", "brier", "log_loss")})

    def ci(rows, m):
        v = np.array([r[m] for r in rows])
        return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]

    out = {}
    for k in names:
        point = metric_block(y, preds[k])
        out[k] = {m: {"value": float(point[m]), "ci95": ci(stats[k], m)} for m in point if m not in ("obs_rate",)}
    deltas = {}
    for k, rows in diffs.items():
        deltas[k] = {}
        for m in ("auroc", "auprc", "brier", "log_loss"):
            v = np.array([r[m] for r in rows])
            better = (v > 0) if m in ("auroc", "auprc") else (v < 0)
            deltas[k][m] = {"value": float(metric_block(y, preds[k])[m] - metric_block(y, preds[ref])[m]),
                            "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
                            "p_better": float(better.mean())}
    return out, deltas


def calibration_curve(y, p, bins=5):
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    rows = []
    for b in sorted(set(q)):
        m = q == b
        k, n = int(y[m].sum()), int(m.sum())
        # Wilson interval for the observed rate
        z = 1.96
        ph = k / n
        den = 1 + z * z / n
        c = (ph + z * z / (2 * n)) / den
        h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
        rows.append({"bin": int(b) + 1, "n": n, "meanPredicted": float(p[m].mean()), "observed": ph,
                     "observedCi95": [float(c - h), float(c + h)]})
    return rows


def fairness(y, p, groups):
    out = []
    for col in groups.columns:
        for g, idx in groups.groupby(col).groups.items():
            m = groups.index.isin(idx)
            n, k = int(m.sum()), int(y[m].sum())
            row = {"attribute": col, "group": str(g), "n": n, "positives": k,
                   "observedRate": k / n if n else None, "meanPredicted": float(p[m].mean()) if n else None,
                   "oe": (k / n) / float(p[m].mean()) if n and p[m].mean() > 0 else None,
                   "brier": float(brier_score_loss(y[m], p[m])) if n else None,
                   "auroc": float(roc_auc_score(y[m], p[m])) if 0 < k < n else None}
            # 500-draw bootstrap within the subgroup for AUROC and O/E
            yi, pi_ = y[m], p[m]
            rg = np.random.default_rng(SEED)
            au, oe = [], []
            for _ in range(500):
                j = rg.integers(0, n, n)
                if 0 < yi[j].sum() < n:
                    au.append(roc_auc_score(yi[j], pi_[j]))
                oe.append(yi[j].mean() / pi_[j].mean())
            row["aurocCi95"] = [float(np.percentile(au, 2.5)), float(np.percentile(au, 97.5))] if len(au) > 50 else None
            row["oeCi95"] = [float(np.percentile(oe, 2.5)), float(np.percentile(oe, 97.5))]
            row["tooSmall"] = n < 30 or k < 10
            out.append(row)
    return out


def tiers_from_oof(y, p):
    """Calibrated risk tiers. watch: risk at or above the 2017-18 base rate; alert: top fifth of OOF risk."""
    watch = float(np.round(np.mean(y), 2))
    alert = float(np.round(np.quantile(p, 0.80), 2))
    res = {"watch": watch, "alert": alert, "tiers": []}
    for name, lo, hi in (("alert", alert, 1.01), ("watch", watch, alert), ("ok", -0.01, watch)):
        m = (p >= lo) & (p < hi)
        n, k = int(m.sum()), int(y[m].sum())
        res["tiers"].append({"status": name, "riskFrom": max(lo, 0.0), "riskTo": min(hi, 1.0), "n": n, "positives": k,
                             "observedRate": k / n if n else None, "shareOfAllPositives": k / int(y.sum())})
    return res


def main():
    meps = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "meps")
    os.makedirs(OUT, exist_ok=True)
    s17 = pd.read_csv(os.path.join(meps, "meps2017_survivors.csv")).set_index("ID")
    dev = pd.read_csv(os.path.join(meps, "meps2018_followup_dev.csv"))[["ID", "outcome_acute_care_2018"]].set_index("ID")
    held = pd.read_csv(os.path.join(meps, "heldout_ids.csv"))[["ID"]]
    assert not set(held.ID) & set(dev.index), "held-out and dev overlap"

    Xs = {"baseline": baseline_features(s17), "domain": domain_features(s17), "final": final_features(s17)}
    for X in Xs.values():  # leakage guard: only 2017 columns feed the model
        assert not any(c.endswith("18") or c.endswith("18X") for c in X.columns)
    y = dev.outcome_acute_care_2018.values.astype(int)
    ids = dev.index

    models = make_models()
    oof = {k: np.zeros((N_REPEATS, len(y))) for k in models}
    rskf = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)
    for i, (tr, te) in enumerate(rskf.split(np.zeros(len(y)), y)):
        r = i // N_SPLITS
        for k, mdl in models.items():
            X = Xs[FEATURESETS[k]].loc[ids]
            m = make_models()[k].fit(X.iloc[tr], y[tr])
            oof[k][r, te] = m.predict_proba(X.iloc[te])[:, 1]
    preds = {k: v.mean(axis=0) for k, v in oof.items()}
    per_repeat_auc = {k: [float(roc_auc_score(y, v[r])) for r in range(N_REPEATS)] for k, v in oof.items()}

    rng = np.random.default_rng(SEED)
    metrics, deltas = bootstrap(y, preds, rng)
    # Final model vs the model submitted before the switch (L2 logistic on 34 domain features), same folds.
    _, vs_prev = bootstrap(y, {"logistic": preds["logistic"], FINAL: preds[FINAL]}, np.random.default_rng(SEED), ref="logistic")
    for k in metrics:
        metrics[k]["auroc_per_repeat"] = {"mean": float(np.mean(per_repeat_auc[k])), "sd": float(np.std(per_repeat_auc[k]))}

    # Final model = calibrated random forest on the compact set (nested-CV pick); refit on all dev survivors.
    final = make_models()[FINAL].fit(Xs["final"].loc[ids], y)
    pd.DataFrame({"ID": ids, "y": y, **{f"p_{k}": v for k, v in preds.items()}}).to_csv(os.path.join(OUT, "oof.csv"), index=False)

    # Global factors from TreeSHAP: mean |log-odds contribution| over dev survivors, and its direction
    # (Spearman correlation of the survivor's value with its contribution: + means higher value -> higher risk).
    Xf = Xs["final"].loc[ids]
    con = contributions(final, Xf)
    factors = []
    for n_ in con.columns:
        base = n_.replace("missing:", "")
        v = Xf[base].isna().astype(float) if n_.startswith("missing:") else Xf[base]
        ok = v.notna().values
        rho = float(pd.Series(v.values[ok]).corr(pd.Series(con[n_].values[ok]), method="spearman")) if ok.sum() > 2 else 0.0
        factors.append({"feature": n_, "label": ("Missing: " if n_.startswith("missing:") else "") + FINAL_LABELS[base],
                        "meanAbsLogit": float(con[n_].abs().mean()), "direction": "raises" if rho > 0 else "lowers",
                        "spearman": rho})
    factors.sort(key=lambda f: -f["meanAbsLogit"])

    # Held-out submission: fit on all 466 dev survivors, predict in template order.
    hp = final.predict_proba(Xs["final"].loc[held.ID])[:, 1]
    sub = pd.DataFrame({"ID": held.ID, "predicted_risk": np.round(hp, 6)})
    os.makedirs(os.path.join(ROOT, "submission"), exist_ok=True)
    sub.to_csv(os.path.join(ROOT, "submission", "heldout_predictions.csv"), index=False)
    base_final = make_models()["baseline"].fit(Xs["baseline"].loc[ids], y)

    groups = subgroups(s17.loc[ids])
    out = {
        "outcome": "Any ER visit or hospital stay in 2018 (outcome_acute_care_2018)",
        "n_dev": int(len(y)), "positives_dev": int(y.sum()), "n_heldout": int(len(held)),
        "validation": f"{N_REPEATS}x repeated stratified {N_SPLITS}-fold CV on the development set, one row per survivor; "
                      f"OOF predictions averaged over repeats; {N_BOOT}-sample patient bootstrap for 95% CIs; paired bootstrap for differences.",
        "finalModel": FINAL,
        "metrics": metrics, "deltaVsBaseline": deltas, "deltaVsPrevious": {"previous": "logistic", **vs_prev[FINAL]},
        "calibrationCurve": {k: calibration_curve(y, v) for k, v in preds.items()},
        "fairness": fairness(y, preds[FINAL], groups),
        "fairnessBaseline": fairness(y, preds["baseline"], groups),
        "tiers": tiers_from_oof(y, preds[FINAL]),
        "factors": factors,
        "heldoutSummary": {"meanPredicted": float(hp.mean()), "min": float(hp.min()), "max": float(hp.max())},
    }
    with open(os.path.join(OUT, "metrics_meps.json"), "w") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(OUT, "model.pkl"), "wb") as f:
        pickle.dump({"final": final, "baseline": base_final}, f)

    for k in metrics:
        m = metrics[k]
        print(f"{k:15s} AUROC {m['auroc']['value']:.3f} {m['auroc']['ci95']}  AUPRC {m['auprc']['value']:.3f}  "
              f"Brier {m['brier']['value']:.4f}  slope {m['cal_slope']['value']:.2f}  int {m['cal_intercept']['value']:.2f}")
    for k, d in deltas.items():
        print(f"delta {k}: AUROC {d['auroc']['value']:+.3f} {d['auroc']['ci95']} p_better {d['auroc']['p_better']:.2f}; "
              f"Brier {d['brier']['value']:+.4f} {d['brier']['ci95']} p_better {d['brier']['p_better']:.2f}")
    print("tiers", out["tiers"])
    for f_ in factors[:12]:
        print(f"  {f_['label']:55s} mean|logit| {f_['meanAbsLogit']:.3f}  {f_['direction']} (rho {f_['spearman']:+.2f})")


if __name__ == "__main__":
    main()
