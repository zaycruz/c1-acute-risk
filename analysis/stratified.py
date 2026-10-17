#!/usr/bin/env python3
"""Stratified check of the nested CV: does the search rank better *within* prior-use groups?

Usage: python -I analysis/stratified.py [data/meps]     (run autoresearch.py nested and nested-interpretable first)
Writes runs/autoresearch/stratified.json. The README's "+0.094 [-0.002, +0.206]" is prior.search.

Groups: no ER visit or hospital stay in 2017 (n=326) vs one or more (n=140). Paired bootstrap, resampled
within each group, 2,000 draws, seed 7.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import domain_features  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "runs", "autoresearch")


def strat_auc(yy, pp, gg):
    a = [roc_auc_score(yy[gg == g], pp[gg == g]) for g in (0, 1)]
    return np.mean(a), a


def main():
    meps = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "meps")
    s17 = pd.read_csv(os.path.join(meps, "meps2017_survivors.csv")).set_index("ID")
    dev = pd.read_csv(os.path.join(meps, "meps2018_followup_dev.csv")).set_index("ID")
    D = domain_features(s17).loc[dev.index]
    g = ((D.er_visits_17 > 0) | (D.hosp_stays_17 > 0)).values.astype(int)
    N = pd.read_csv(os.path.join(RUNS, "round-nested-oof.csv"))
    NI = pd.read_csv(os.path.join(RUNS, "round-nested-interpretable-oof.csv"))
    y, b = N.y.values, N.baseline.values
    rng = np.random.default_rng(7)
    out = {"groups": {"noPrior": {"n": int((g == 0).sum()), "events": int(y[g == 0].sum())},
                      "prior": {"n": int((g == 1).sum()), "events": int(y[g == 1].sum())}}}
    for name, p in [("search", N.procedure.values), ("interpretable", NI.procedure.values), ("submitted", N.submitted.values)]:
        draws = {"noPrior": [], "prior": [], "meanWithin": []}
        for _ in range(2000):
            i = np.concatenate([rng.choice(np.where(g == k)[0], (g == k).sum()) for k in (0, 1)])
            sa, (a0, a1) = strat_auc(y[i], p[i], g[i])
            sb, (b0, b1) = strat_auc(y[i], b[i], g[i])
            draws["noPrior"].append(a0 - b0); draws["prior"].append(a1 - b1); draws["meanWithin"].append(sa - sb)
        sa, (a0, a1) = strat_auc(y, p, g)
        sb, (b0, b1) = strat_auc(y, b, g)
        point = {"noPrior": (a0, b0), "prior": (a1, b1), "meanWithin": (sa, sb)}
        for k, (va, vb) in point.items():
            v = np.array(draws[k])
            out.setdefault(k, {})[name] = {"model": float(va), "baseline": float(vb), "delta": float(va - vb),
                                           "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
                                           "pBetter": float((v > 0).mean())}
            print(f"{name:13s} {k:10s} d {va - vb:+.3f} [{np.percentile(v, 2.5):+.3f}, {np.percentile(v, 97.5):+.3f}]")
    json.dump(out, open(os.path.join(RUNS, "stratified.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
