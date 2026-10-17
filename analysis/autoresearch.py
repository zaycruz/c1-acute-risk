#!/usr/bin/env python3
"""Autoresearch loop: search models x feature sets for C1, then score the *search itself* with nested CV.

Usage: .venv/bin/python -I analysis/autoresearch.py <round> [data/meps]
  round = 1 (broad), 2 (refine, candidates chosen after reading round 1), nested (honest estimate of picking the best).
Writes runs/autoresearch/round-<round>.json and appends to runs/autoresearch/log.md.

Why nested: with ~30 candidates scored on the same 466 survivors, the best CV score is optimistic (winner's curse).
The nested run repeats the whole selection inside each outer training fold and scores the pick on the outer fold,
so its number is what the search procedure would really deliver on new survivors.
"""
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV, PoissonRegressor
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import baseline_features, domain_features  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "runs", "autoresearch")
SEED = 20261017
os.makedirs(RUNS, exist_ok=True)

RAW_ITEMS = ["ADGENH42", "ADDAYA42", "ADCLIM42", "ADACLS42", "ADWKLM42", "ADEMLS42", "ADMWCF42", "ADPAIN42", "ADPCFL42",
             "ADENGY42", "ADPRST42", "ADSOCA42", "ADNERV42", "ADHOPE42", "ADREST42", "ADSAD42", "ADEFRT42", "ADWRTH42",
             "ADINTR42", "ADDPRS42", "CEFPHL31", "CEFPAC31", "CEFQLF31", "CEFMHL31", "CEFRLT31", "CEFMPR31", "CLSTRT31",
             "IPNGTD17", "OPTOTV17", "HHTOTD17", "TOTSLF17", "DDNWRK17", "EDUCYR", "POVCAT17", "TOTEXP17"]
COMPACT = ["er_visits_17", "hosp_stays_17", "rx_fills_17", "office_visits_17", "home_health_17", "age", "physical_score",
           "mental_score", "depression_phq2", "distress_k6", "poor_physical_rating"]
PRIOR_USE = ["er_visits_17", "hosp_stays_17", "rx_fills_17", "office_visits_17", "home_health_17", "age"]


def featuresets(s17):
    D = domain_features(s17)
    raw = pd.DataFrame({c: s17[c].where(s17[c] >= 0) for c in RAW_ITEMS}, index=s17.index)
    for c in ("IPNGTD17", "OPTOTV17", "HHTOTD17", "TOTSLF17", "DDNWRK17", "TOTEXP17"):
        raw[c] = np.log1p(raw[c])
    # self-supervised: factor analysis of all survey items, fitted on all 717 survivors (2017 answers only, no outcomes)
    from sklearn.decomposition import FactorAnalysis
    items = raw[[c for c in RAW_ITEMS if c.startswith(("AD", "CEF"))]].join(D[["pain", "fatigue", "fear_recurrence", "financial_toxicity", "cost_delay", "distress_k6", "depression_phq2"]])
    Zi = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(items))
    fa = FactorAnalysis(n_components=5, rotation="varimax", random_state=0).fit(Zi)
    FA = pd.DataFrame(fa.transform(Zi), index=s17.index, columns=[f"fa{i}" for i in range(5)])
    SHARED_ = ["age", "female", "hispanic", "nh_black", "nh_asian_other", "public_only", "uninsured", "low_income",
               "er_visits_17", "hosp_stays_17", "office_visits_17", "current_treatment", "pain", "ca_breast", "ca_colon", "ca_lung", "ca_prostate"]
    return {"baseline": baseline_features(s17), "domain": D,
            "prior_fa": D[PRIOR_USE].join(FA), "compact_fa": D[COMPACT].join(FA),
            "shared_compact": D[list(dict.fromkeys(SHARED_ + COMPACT))], "domain_raw": D.join(raw), "compact": D[COMPACT],
            "prior_use": D[PRIOR_USE],
            # round 2 (chosen after round 1: small sets won)
            "compact_sym": D[COMPACT + ["pain", "fatigue", "activity_limited"]],
            "compact_ctx": D[COMPACT + ["public_only", "female", "current_treatment", "n_cancer_types"]],
            "prior_phys": D[PRIOR_USE + ["physical_score", "poor_physical_rating"]],
            "compact_raw_use": D[COMPACT].join(raw[["IPNGTD17", "OPTOTV17", "HHTOTD17", "TOTEXP17", "DDNWRK17"]])}


# ---- candidate models: each returns an object with fit(X, y, counts) / predict(X) -> probability ----
class Clf:
    def __init__(self, est, impute=True, scale=True):
        steps = ([SimpleImputer(strategy="median", add_indicator=True)] if impute else []) + ([StandardScaler()] if scale else []) + [est]
        self.m = make_pipeline(*steps)

    def fit(self, X, y, c):
        self.m.fit(X, y)
        return self

    def predict(self, X):
        return self.m.predict_proba(X)[:, 1]


class Count:
    """Fit the 2018 acute-visit count (ER visits + hospital stays), a richer target than yes/no; then map the
    predicted rate to P(any) with a logistic fitted on out-of-fold rates inside the training data."""
    def __init__(self, reg):
        self.reg = reg

    def fit(self, X, y, c):
        c = c[:, 0] if c.ndim == 2 else c
        base = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), self.reg)
        oof = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=3).split(X, y):
            oof[te] = clone(base).fit(X.iloc[tr], c[tr]).predict(X.iloc[te])
        self.cal = LogisticRegression(C=1e4).fit(np.log(np.clip(oof, 1e-3, None)).reshape(-1, 1), y)
        self.m = clone(base).fit(X, c)
        return self

    def predict(self, X):
        return self.cal.predict_proba(np.log(np.clip(self.m.predict(X), 1e-3, None)).reshape(-1, 1))[:, 1]


class Avg:
    def __init__(self, *parts):
        self.parts = parts

    def fit(self, X, y, c):
        for p in self.parts:
            p.fit(X, y, c)
        return self

    def predict(self, X):
        return np.mean([p.predict(X) for p in self.parts], axis=0)


class AvgCols(Avg):
    """Average of models that each see their own column subset (None = all columns)."""
    def fit(self, X, y, c):
        for m, cols in self.parts:
            m.fit(X if cols is None else X[cols], y, c)
        return self

    def predict(self, X):
        return np.mean([m.predict(X if cols is None else X[cols]) for m, cols in self.parts], axis=0)


class AuxTarget:
    """Train on a richer 2018 target (count, nights or log cost: targets only, never predictors), then map the
    score to P(acute care) with a logistic fitted on out-of-fold scores inside the training data."""
    def __init__(self, kind, reg_factory):
        self.kind, self.reg_factory = kind, reg_factory

    def fit(self, X, y, c):
        t = c[:, {"count": 0, "nights": 1, "logcost": 2}[self.kind]]
        base = lambda: make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), self.reg_factory())
        oof = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=3).split(X, y):
            oof[te] = base().fit(X.iloc[tr], t[tr]).predict(X.iloc[te])
        self.cal = LogisticRegression(C=1e4).fit(oof.reshape(-1, 1), y)
        self.m = base().fit(X, t)
        return self

    def predict(self, X):
        return self.cal.predict_proba(self.m.predict(X).reshape(-1, 1))[:, 1]


class SyntheaPrior:
    """Logistic regression whose coefficients are shrunk toward a Synthea model (fitted on 4,033 synthetic person-years
    on the shared variables) instead of toward zero. Prior strength lam chosen by inner 5-fold CV on log loss.
    lam -> infinity = the Synthea model with a MEPS intercept; lam -> 0 = MEPS-only, unpenalised."""
    LAMS = [0.3, 1, 3, 10, 30, 100, 300]

    def __init__(self, shared):
        self.shared = shared

    @staticmethod
    def _fit(Z, y, b0, lam):
        from scipy.optimize import minimize
        n, k = Z.shape

        def f(w):
            a, b = w[0], w[1:]
            z = a + Z @ b
            ll = np.sum(np.logaddexp(0, z) - y * z) / n
            g = Z.T @ (1 / (1 + np.exp(-z)) - y) / n
            return ll + lam / n * np.sum((b - b0) ** 2), np.r_[np.sum(1 / (1 + np.exp(-z)) - y) / n, g + 2 * lam / n * (b - b0)]
        w = minimize(f, np.r_[0.0, b0], jac=True, method="L-BFGS-B").x
        return w

    def fit(self, X, y, c):
        global SYN_B
        self.imp = SimpleImputer(strategy="median").fit(X)
        Xi = pd.DataFrame(self.imp.transform(X), columns=X.columns)
        self.mu, self.sd = Xi.mean(), Xi.std().replace(0, 1)
        Z = ((Xi - self.mu) / self.sd).values
        b0 = np.array([SYN_B.get(col, 0.0) * self.sd[col] for col in X.columns])  # raw-scale Synthea coef -> MEPS-standardised scale
        best = None
        for lam in self.LAMS:
            p = np.zeros(len(y))
            for tr, te in StratifiedKFold(5, shuffle=True, random_state=1).split(Z, y):
                w = self._fit(Z[tr], y[tr], b0, lam)
                p[te] = 1 / (1 + np.exp(-(w[0] + Z[te] @ w[1:])))
            ll = log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))
            if best is None or ll < best[0]:
                best = (ll, lam)
        self.lam = best[1]
        self.w = self._fit(Z, y, b0, self.lam)
        return self

    def predict(self, X):
        Xi = pd.DataFrame(self.imp.transform(X), columns=X.columns)
        Z = ((Xi - self.mu) / self.sd).values
        return 1 / (1 + np.exp(-(self.w[0] + Z @ self.w[1:])))


class Bag:
    def __init__(self, factory, n=25):
        self.factory, self.n = factory, n

    def fit(self, X, y, c):
        rg = np.random.default_rng(0)
        self.ms = []
        for _ in range(self.n):
            i = rg.integers(0, len(y), len(y))
            self.ms.append(self.factory().fit(X.iloc[i], y[i], c[i]))
        return self

    def predict(self, X):
        return np.mean([m.predict(X) for m in self.ms], axis=0)


class Stack:
    """Level-2 logistic on out-of-fold logits of several (model, columns) parts, fitted inside the training data."""
    def __init__(self, *parts):
        self.parts = parts

    def fit(self, X, y, c):
        L = np.zeros((len(y), len(self.parts)))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=5).split(X, y):
            for j, (f, cols) in enumerate(self.parts):
                Xc = X if cols is None else X[cols]
                L[te, j] = _lg(f().fit(Xc.iloc[tr], y[tr], c[tr]).predict(Xc.iloc[te]))
        self.meta = LogisticRegression(C=1.0).fit(L, y)
        self.ms = [(f().fit(X if cols is None else X[cols], y, c), cols) for f, cols in self.parts]
        return self

    def predict(self, X):
        L = np.column_stack([_lg(m.predict(X if cols is None else X[cols])) for m, cols in self.ms])
        return self.meta.predict_proba(L)[:, 1]


def _lg(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def inner():
    return StratifiedKFold(5, shuffle=True, random_state=1)


def lr_l2(Cs=np.logspace(-3, 0, 10)):
    return Clf(LogisticRegressionCV(Cs=Cs, cv=inner(), scoring="neg_log_loss", max_iter=5000))


def lr_l1():
    return Clf(LogisticRegressionCV(Cs=np.logspace(-2.5, 0.5, 10), cv=inner(), penalty="l1", solver="liblinear", scoring="neg_log_loss", max_iter=5000))


def lr_enet():
    return Clf(LogisticRegressionCV(Cs=np.logspace(-2.5, 0.5, 8), cv=inner(), penalty="elasticnet", solver="saga", l1_ratios=[0.2, 0.5, 0.8],
                                    scoring="neg_log_loss", max_iter=5000))


def lr_fixed(C):
    return Clf(LogisticRegression(C=C, max_iter=5000))


def gbm(depth=2, lr=0.03, iters=300, leaf=30):
    return Clf(CalibratedClassifierCV(HistGradientBoostingClassifier(max_depth=depth, learning_rate=lr, max_iter=iters, min_samples_leaf=leaf,
                                                                     l2_regularization=1.0, random_state=0), method="sigmoid", cv=5),
               impute=False, scale=False)


def rf(leaf=10):
    return Clf(CalibratedClassifierCV(RandomForestClassifier(300, min_samples_leaf=leaf, max_features="sqrt", n_jobs=1, random_state=0),
                                      method="sigmoid", cv=5), scale=False)


def et(leaf=10):
    return Clf(CalibratedClassifierCV(ExtraTreesClassifier(300, min_samples_leaf=leaf, max_features="sqrt", n_jobs=1, random_state=0),
                                      method="sigmoid", cv=5), scale=False)


def spline_lr():
    """GAM-like: cubic splines on every column (binary ones pass through as near-linear), then ridge logistic."""
    return Clf(make_pipeline(SplineTransformer(n_knots=4, degree=3, knots="quantile", extrapolation="constant"),
                             LogisticRegressionCV(Cs=np.logspace(-3, 0, 8), cv=inner(), scoring="neg_log_loss", max_iter=5000)))


def poisson_glm():
    return Count(GridSearchCV(PoissonRegressor(max_iter=3000), {"alpha": [0.3, 1, 3, 10, 30]}, cv=5, scoring="neg_mean_poisson_deviance"))


def poisson_gbm():
    return Count(HistGradientBoostingRegressor(loss="poisson", max_depth=2, learning_rate=0.03, max_iter=200, min_samples_leaf=30, random_state=0))


class baseline_model(Clf):
    """The organisers' baseline_model.py pipeline, unchanged."""
    def __init__(self):
        self.m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.3, max_iter=2000))


ROUND1 = {
    "baseline|baseline": ("baseline", baseline_model),
    "lr_l2|domain": ("domain", lr_l2),          # current submission
    "lr_l2|baseline": ("baseline", lambda: Clf(LogisticRegressionCV(Cs=np.logspace(-3, 0, 10), cv=inner(), scoring="neg_log_loss", max_iter=5000))),
    "lr_l2|domain_raw": ("domain_raw", lr_l2),
    "lr_l2|compact": ("compact", lr_l2),
    "lr_l2|prior_use": ("prior_use", lr_l2),
    "lr_l1|domain": ("domain", lr_l1),
    "lr_l1|domain_raw": ("domain_raw", lr_l1),
    "lr_enet|domain_raw": ("domain_raw", lr_enet),
    "spline_lr|compact": ("compact", spline_lr),
    "spline_lr|domain": ("domain", spline_lr),
    "gbm_d2|domain": ("domain", gbm),
    "gbm_d2|domain_raw": ("domain_raw", gbm),
    "gbm_d3|domain": ("domain", lambda: gbm(depth=3, lr=0.05, iters=150, leaf=25)),
    "gbm_d1|domain": ("domain", lambda: gbm(depth=1, lr=0.05, iters=300, leaf=30)),
    "rf|domain": ("domain", rf),
    "rf|domain_raw": ("domain_raw", rf),
    "et|domain": ("domain", et),
    "poisson_glm|domain": ("domain", poisson_glm),
    "poisson_glm|compact": ("compact", poisson_glm),
    "poisson_gbm|domain": ("domain", poisson_gbm),
    "avg(lr_l2,gbm_d2)|domain": ("domain", lambda: Avg(lr_l2(), gbm())),
    "avg(lr_l2,rf)|domain": ("domain", lambda: Avg(lr_l2(), rf())),
    "avg(lr_l2,poisson_glm)|domain": ("domain", lambda: Avg(lr_l2(), poisson_glm())),
}

# Round 2: chosen after reading round 1 (log.md). Small feature sets won; refine around them.
MONO = [1, 1, 1, 1, 1, 1, -1, -1, 1, 1, 1]  # COMPACT order: more use / older / worse scores -> higher risk


def mono_gbm():
    return Clf(CalibratedClassifierCV(HistGradientBoostingClassifier(max_depth=2, learning_rate=0.03, max_iter=300, min_samples_leaf=30,
                                                                     l2_regularization=1.0, monotonic_cst=MONO, random_state=0),
                                      method="sigmoid", cv=5), impute=False, scale=False)


def ridge():
    from sklearn.linear_model import RidgeCV
    return RidgeCV(alphas=np.logspace(-1, 3, 9))


# Round 3: "outside the box" (after round 2 plateaued at AUROC ~0.70-0.71)
ROUND3 = {
    "synthea_prior|shared_compact": ("shared_compact", lambda: SyntheaPrior(None)),
    "synthea_prior|prior_use": ("prior_use", lambda: SyntheaPrior(None)),
    "aux_logcost|compact": ("compact", lambda: AuxTarget("logcost", ridge)),
    "aux_logcost|compact_raw_use": ("compact_raw_use", lambda: AuxTarget("logcost", ridge)),
    "aux_nights|compact": ("compact", lambda: AuxTarget("nights", lambda: HistGradientBoostingRegressor(loss="poisson", max_depth=2, learning_rate=0.03, max_iter=200, min_samples_leaf=30, random_state=0))),
    "lr_l2|prior_fa": ("prior_fa", lr_l2),
    "lr_l2|compact_fa": ("compact_fa", lr_l2),
    "rf|compact_fa": ("compact_fa", rf),
    "mono_gbm|compact": ("compact", mono_gbm),
    "bag(spline_lr)|prior_use": ("prior_use", lambda: Bag(spline_lr, 15)),
    "stack(rf,spline,synprior,aux_cost)": ("compact_raw_use", lambda: Stack((rf, None), (spline_lr, PRIOR_USE),
                                                                              (lambda: SyntheaPrior(None), PRIOR_USE),
                                                                              (lambda: AuxTarget("logcost", ridge), COMPACT))),
}

ROUND2 = {
    "lr_l2|compact_sym": ("compact_sym", lr_l2),
    "lr_l2|compact_ctx": ("compact_ctx", lr_l2),
    "lr_l2|prior_phys": ("prior_phys", lr_l2),
    "lr_l2|compact_raw_use": ("compact_raw_use", lr_l2),
    "lr_l2_wide|compact": ("compact", lambda: lr_l2(np.logspace(-3, 2, 12))),
    "spline_lr|prior_use": ("prior_use", spline_lr),
    "spline_lr|prior_phys": ("prior_phys", spline_lr),
    "spline_lr|compact_sym": ("compact_sym", spline_lr),
    "rf|compact": ("compact", rf),
    "rf|compact_raw_use": ("compact_raw_use", rf),
    "poisson_glm|prior_use": ("prior_use", poisson_glm),
    "avg(spline_lr,rf_raw)": ("domain_raw", lambda: AvgCols((spline_lr(), COMPACT), (rf(), None))),
    "avg(lr_l2,spline_lr)|compact": ("compact", lambda: Avg(lr_l2(), spline_lr())),
}


def load(meps):
    s17 = pd.read_csv(os.path.join(meps, "meps2017_survivors.csv")).set_index("ID")
    dev = pd.read_csv(os.path.join(meps, "meps2018_followup_dev.csv"))[["ID", "outcome_acute_care_2018", "ERTOT18", "IPDIS18", "IPNGTD18", "TOTEXP18"]].set_index("ID")
    # outcome-year columns are TARGETS only (count target for the Poisson candidates), never predictors
    y = dev.outcome_acute_care_2018.values.astype(int)
    c = (dev.ERTOT18.clip(lower=0) + dev.IPDIS18.clip(lower=0)).values.astype(float)
    c = np.column_stack([c, dev.IPNGTD18.clip(lower=0).values, np.log1p(dev.TOTEXP18.clip(lower=0).values)])
    global SYN_B
    P = pd.read_csv(os.path.join(ROOT, "analysis", "out", "synthea_panel.csv"))
    sh = ["age", "female", "hispanic", "nh_black", "nh_asian_other", "public_only", "uninsured", "low_income",
          "er_visits_17", "hosp_stays_17", "office_visits_17", "current_treatment", "pain", "ca_breast", "ca_colon", "ca_lung", "ca_prostate"]
    sm = make_pipeline(SimpleImputer(strategy="median"), LogisticRegression(C=1.0, max_iter=5000)).fit(P[sh], P.y)
    SYN_B = dict(zip(sh, sm.steps[1][1].coef_[0]))
    assert ((c[:, 0] > 0) == (y == 1)).mean() > 0.97, "count target does not match the outcome"
    F = {k: v.loc[dev.index] for k, v in featuresets(s17).items()}
    return F, y, c


def score_candidate(name, fs, factory, F, y, c, n_rep):
    X = F[fs]
    P = np.zeros((n_rep, len(y)))
    for i, (tr, te) in enumerate(RepeatedStratifiedKFold(n_splits=5, n_repeats=n_rep, random_state=SEED).split(X, y)):
        m = factory().fit(X.iloc[tr], y[tr], c[tr])
        P[i // 5, te] = m.predict(X.iloc[te])
    return name, P


def paired(y, pa, pb, rng, n=2000):
    """Bootstrap of (a - b) for AUROC and log loss; returns value, 95% CI, P(a better)."""
    da, dl = [], []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        da.append(roc_auc_score(y[i], pa[i]) - roc_auc_score(y[i], pb[i]))
        dl.append(log_loss(y[i], np.clip(pa[i], 1e-6, 1 - 1e-6)) - log_loss(y[i], np.clip(pb[i], 1e-6, 1 - 1e-6)))
    da, dl = np.array(da), np.array(dl)
    return {"dAuroc": float(roc_auc_score(y, pa) - roc_auc_score(y, pb)), "dAurocCi95": [float(np.percentile(da, 2.5)), float(np.percentile(da, 97.5))],
            "pAurocBetter": float((da > 0).mean()),
            "dLogLoss": float(log_loss(y, np.clip(pa, 1e-6, 1 - 1e-6)) - log_loss(y, np.clip(pb, 1e-6, 1 - 1e-6))),
            "dLogLossCi95": [float(np.percentile(dl, 2.5)), float(np.percentile(dl, 97.5))], "pLogLossBetter": float((dl < 0).mean())}


def run_round(rnd, cands, F, y, c, n_rep=5):
    t0 = time.time()
    res = Parallel(n_jobs=min(16, len(cands)), verbose=0)(delayed(score_candidate)(n, fs, f, F, y, c, n_rep) for n, (fs, f) in cands.items())
    preds = {n: P.mean(axis=0) for n, P in res}
    reps = {n: [float(roc_auc_score(y, P[r])) for r in range(P.shape[0])] for n, P in res}
    rng = np.random.default_rng(SEED)
    base = preds["baseline|baseline"]
    rows = []
    for n, p in preds.items():
        row = {"candidate": n, "auroc": float(roc_auc_score(y, p)), "aurocRepeatSd": float(np.std(reps[n])),
               "logLoss": float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))), "brier": float(brier_score_loss(y, p))}
        if n != "baseline|baseline":
            row["vsBaseline"] = paired(y, p, base, rng)
        rows.append(row)
    rows.sort(key=lambda r: r["logLoss"])
    out = {"round": rnd, "seconds": round(time.time() - t0), "nCandidates": len(cands), "nRepeats": n_rep, "results": rows}
    json.dump(out, open(os.path.join(RUNS, f"round-{rnd}.json"), "w"), indent=1)
    pd.DataFrame({n: p for n, p in preds.items()}).assign(y=y).to_csv(os.path.join(RUNS, f"round-{rnd}-oof.csv"), index=False)
    lines = [f"\n## Round {rnd} ({len(cands)} candidates, {n_rep}x5-fold CV, {out['seconds']} s)\n",
             "| candidate | AUROC | log loss | Brier | dAUROC vs baseline [95% CI] | P(better) | dLogLoss [95% CI] |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        v = r.get("vsBaseline")
        lines.append(f"| {r['candidate']} | {r['auroc']:.3f} | {r['logLoss']:.4f} | {r['brier']:.4f} | " +
                     (f"{v['dAuroc']:+.3f} [{v['dAurocCi95'][0]:+.3f}, {v['dAurocCi95'][1]:+.3f}] | {v['pAurocBetter']:.2f} | "
                      f"{v['dLogLoss']:+.4f} [{v['dLogLossCi95'][0]:+.4f}, {v['dLogLossCi95'][1]:+.4f}] |" if v else "ref | | |"))
    open(os.path.join(RUNS, "log.md"), "a").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return out


def nested(cands, F, y, c, outer_rep=2, tag="nested"):
    """Outer 5-fold x outer_rep. Inside each outer-train set: score every candidate with 5-fold CV on log loss, pick the best,
    refit it, predict the outer fold. The pool is every candidate looked at in rounds 1 and 2, so the selection we actually
    did is inside the evaluation. Compare the procedure's OOF predictions with the baseline on the same outer folds."""
    t0 = time.time()
    names = list(cands)
    outer = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=outer_rep, random_state=SEED + 7).split(np.zeros(len(y)), y))

    def inner_score(k, n):
        tr = outer[k][0]
        fs, f = cands[n]
        X, yt, ct = F[fs].iloc[tr], y[tr], c[tr]
        p = np.zeros(len(tr))
        for a, b in StratifiedKFold(5, shuffle=True, random_state=SEED + 1).split(X, yt):
            p[b] = f().fit(X.iloc[a], yt[a], ct[a]).predict(X.iloc[b])
        return k, n, log_loss(yt, np.clip(p, 1e-6, 1 - 1e-6))

    scores = Parallel(n_jobs=16)(delayed(inner_score)(k, n) for k in range(len(outer)) for n in names)
    picks = {}
    for k, n, ll in scores:
        if k not in picks or ll < picks[k][1]:
            picks[k] = (n, ll)

    def outer_fit(k, n):
        tr, te = outer[k]
        fs, f = cands[n]
        return k, n, f().fit(F[fs].iloc[tr], y[tr], c[tr]).predict(F[fs].iloc[te])

    jobs = [(k, picks[k][0]) for k in range(len(outer))] + [(k, "baseline|baseline") for k in range(len(outer))] + \
           [(k, "lr_l2|domain") for k in range(len(outer))]
    fits = Parallel(n_jobs=16)(delayed(outer_fit)(k, n) for k, n in jobs)
    Pp, Pb, Ps = (np.zeros((outer_rep, len(y))) for _ in range(3))
    for (k, n, pr), (kk, role) in zip(fits, [(k, "pick") for k in range(len(outer))] + [(k, "base") for k in range(len(outer))] + [(k, "sub") for k in range(len(outer))]):
        te = outer[k][1]
        {"pick": Pp, "base": Pb, "sub": Ps}[role][k // 5, te] = pr
    pp, pb, ps = Pp.mean(axis=0), Pb.mean(axis=0), Ps.mean(axis=0)
    rng = np.random.default_rng(SEED)
    m = lambda p: {"auroc": float(roc_auc_score(y, p)), "logLoss": float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))), "brier": float(brier_score_loss(y, p))}
    out = {"round": "nested", "seconds": round(time.time() - t0), "candidatePool": names, "outerFolds": len(outer),
           "picks": pd.Series([picks[k][0] for k in range(len(outer))]).value_counts().to_dict(),
           "procedure": m(pp), "baseline": m(pb), "submittedModel": m(ps),
           "procedureVsBaseline": paired(y, pp, pb, rng), "procedureVsSubmitted": paired(y, pp, ps, rng),
           "submittedVsBaseline": paired(y, ps, pb, rng)}
    json.dump(out, open(os.path.join(RUNS, f"round-{tag}.json"), "w"), indent=1)
    pd.DataFrame({"y": y, "procedure": pp, "baseline": pb, "submitted": ps}).to_csv(os.path.join(RUNS, f"round-{tag}-oof.csv"), index=False)
    f = lambda v: (f"dAUROC {v['dAuroc']:+.3f} [{v['dAurocCi95'][0]:+.3f}, {v['dAurocCi95'][1]:+.3f}] P(better) {v['pAurocBetter']:.2f}; "
                   f"d log loss {v['dLogLoss']:+.4f} [{v['dLogLossCi95'][0]:+.4f}, {v['dLogLossCi95'][1]:+.4f}] P(better) {v['pLogLossBetter']:.2f}")
    txt = (f"\n## Nested CV ({tag}) of the whole search ({len(names)} candidates, {len(outer)} outer folds, {out['seconds']} s)\n\n"
           f"- Picks per outer fold: {out['picks']}\n"
           f"- AUROC: search procedure {out['procedure']['auroc']:.3f}, submitted model {out['submittedModel']['auroc']:.3f}, baseline {out['baseline']['auroc']:.3f}\n"
           f"- Procedure vs baseline: {f(out['procedureVsBaseline'])}\n"
           f"- Procedure vs submitted model: {f(out['procedureVsSubmitted'])}\n"
           f"- Submitted model vs baseline: {f(out['submittedVsBaseline'])}\n")
    open(os.path.join(RUNS, "log.md"), "a").write(txt)
    print(txt)


def main():
    rnd = sys.argv[1]
    meps = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "meps")
    F, y, c = load(meps)
    if rnd == "1":
        run_round(1, ROUND1, F, y, c)
    elif rnd == "2":
        run_round(2, {**{k: ROUND1[k] for k in ("baseline|baseline", "lr_l2|domain")}, **ROUND2}, F, y, c)
    elif rnd == "3":
        run_round(3, {**{k: ROUND1[k] for k in ("baseline|baseline", "lr_l2|domain")}, "rf|compact_raw_use": ROUND2["rf|compact_raw_use"], **ROUND3}, F, y, c)
    elif rnd == "nested":
        pool = {**ROUND1, **ROUND2, **ROUND3}
        nested(pool, F, y, c)
    elif rnd == "nested-interpretable":
        # Pre-stated restriction: only models whose per-survivor drivers can be read off directly (linear / spline GLMs).
        pool = {k: v for k, v in {**ROUND1, **ROUND2, **ROUND3}.items() if k.split("|")[0] in ("baseline", "lr_l2", "lr_l2_wide", "lr_l1", "lr_enet", "spline_lr", "poisson_glm", "synthea_prior", "aux_logcost", "bag(spline_lr)")}
        nested(pool, F, y, c, tag="nested-interpretable")


if __name__ == "__main__":
    main()
