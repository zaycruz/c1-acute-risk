#!/usr/bin/env python3
"""
Reference baseline for Challenge 3: predict acute care use in 2018 from 2017 MEPS survey data alone.

This baseline does NOT use the Synthea records. It is a reference point for judging whether your
integration adds predictive value, not a prescribed approach.

Outcome: outcome_acute_care_2018 = any ER visit or hospital stay in 2018.
Model:   logistic regression on 2017 demographics, cancer status, patient-reported measures,
         financial and practical needs, and 2017 health care use.

Usage (from the release folder):
    python baseline_model.py --meps meps --out baseline_submission.csv
Writes a submission file with one row per held-out ID: ID, predicted_risk.
"""
import argparse
import os

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NUMERIC = ["AGE17X", "POVCAT17",
           # patient-reported measures (VR-12 summaries, PHQ-2, K6, PROMIS Global Health items, fear of recurrence)
           "VPCS42", "VMCS42", "PHQ242", "K6SUM42", "CEFPHL31", "CEFPAC31", "CEFPIN31", "CEFFTG31",
           "CEFQLF31", "CEFMHL31", "CEFRLT31", "CEFMPR31", "CEFBCK31",
           # 2017 health care use
           "ERTOT17", "IPDIS17", "OBTOTV17", "TOTEXP17"]
YES_NO = ["SEX", "INSCOV17", "CTRTMT31", "CBCK31", "CEFACT31", "CABREAST", "CACOLON", "CAPROSTA", "CALUNG",
          # financial and practical needs
          "CNCMED31", "CNCTRP31", "CFNDBT31", "CFNUNB31", "CFNPMT31", "CFMEM31", "CDLPRS31", "CDLTRT31",
          "CMNAFF31", "CINADQ31"]


def features(df):
    X = pd.DataFrame(index=df.index)
    for c in NUMERIC:
        X[c] = df[c].where(df[c] >= 0)                     # MEPS negative codes = missing
    for c in YES_NO:
        X[c] = (df[c] == 1).astype(float).where(df[c] >= 0)
    X = X.join(pd.get_dummies(df["RACETHX"], prefix="race", dtype=float))
    return X


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meps", default="meps", help="folder with the MEPS release files")
    ap.add_argument("--out", default="baseline_submission.csv")
    a = ap.parse_args()

    s17 = pd.read_csv(os.path.join(a.meps, "meps2017_survivors.csv"))
    dev = pd.read_csv(os.path.join(a.meps, "meps2018_followup_dev.csv"))[["ID", "outcome_acute_care_2018"]]
    held = pd.read_csv(os.path.join(a.meps, "heldout_ids.csv"))[["ID"]]

    X = features(s17).set_index(s17.ID)
    train = dev.set_index("ID")
    Xtr, ytr = X.loc[train.index], train.outcome_acute_care_2018
    model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.3, max_iter=2000))

    cv = cross_val_score(model, Xtr, ytr, cv=StratifiedKFold(5, shuffle=True, random_state=0), scoring="roc_auc")
    print(f"development set: n={len(ytr)}, outcome rate {ytr.mean():.1%}, "
          f"cross-validated AUROC {cv.mean():.3f} (+/- {cv.std():.3f})")

    model.fit(Xtr, ytr)
    pred = pd.DataFrame({"ID": held.ID, "predicted_risk": model.predict_proba(X.loc[held.ID])[:, 1]})
    pred.to_csv(a.out, index=False)
    print(f"wrote {len(pred)} held-out predictions to {a.out}")


if __name__ == "__main__":
    main()
