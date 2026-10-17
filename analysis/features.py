"""MEPS 2017 feature engineering for C1 (acute care in 2018).

Only the 2017 file is read here. The 2018 file reuses names such as VPCS42 and K6SUM42 for 2018
measures, so the outcome is joined by the caller with exactly two columns (ID, outcome).

MEPS codes: -1 = not asked (skip pattern), -7 refused, -8 don't know, -9 not ascertained.
Yes/no items are 1 = yes, 2 = no. For yes/no items a skip (-1) means the gate question was "no",
so it counts as "no". -7/-8/-9 are missing.
"""
import numpy as np
import pandas as pd

MEPS_NUMERIC = ["AGE17X", "POVCAT17", "VPCS42", "VMCS42", "PHQ242", "K6SUM42", "CEFPHL31", "CEFPAC31",
                "CEFPIN31", "CEFFTG31", "CEFQLF31", "CEFMHL31", "CEFRLT31", "CEFMPR31", "CEFBCK31",
                "ERTOT17", "IPDIS17", "OBTOTV17", "TOTEXP17"]
MEPS_YES_NO = ["SEX", "INSCOV17", "CTRTMT31", "CBCK31", "CEFACT31", "CABREAST", "CACOLON", "CAPROSTA", "CALUNG",
               "CNCMED31", "CNCTRP31", "CFNDBT31", "CFNUNB31", "CFNPMT31", "CFMEM31", "CDLPRS31", "CDLTRT31",
               "CMNAFF31", "CINADQ31"]

FINANCIAL = ["CNCMED31", "CFNDBT31", "CFNUNB31", "CFNPMT31", "CFNSTB31", "CFNINC31", "CFNBNK31"]
DELAY = ["CDLPRS31", "CDLVST31", "CDLTRT31", "CDLFUP31", "CDLMNT31", "CDLOTH31", "CMNAFF31"]


def baseline_features(df):
    """Exactly the features of the organisers' baseline_model.py (kept verbatim for a fair comparison)."""
    X = pd.DataFrame(index=df.index)
    for c in MEPS_NUMERIC:
        X[c] = df[c].where(df[c] >= 0)
    for c in MEPS_YES_NO:
        X[c] = (df[c] == 1).astype(float).where(df[c] >= 0)
    X = X.join(pd.get_dummies(df["RACETHX"], prefix="race", dtype=float))
    return X


def num(s):
    """Negative codes -> NaN."""
    return s.where(s >= 0)


def yes(s):
    """1 = yes; 2 or -1 (skipped because gate was no) = no; -7/-8/-9 = NaN."""
    out = pd.Series(np.where(s == 1, 1.0, np.where((s == 2) | (s == -1), 0.0, np.nan)), index=s.index)
    return out


def count_yes(df, cols):
    """Number of 'yes' answers; NaN only if every item is missing."""
    m = pd.concat([yes(df[c]) for c in cols], axis=1)
    return m.sum(axis=1, min_count=1)


# Domain features: one column per idea a care team can act on. Higher = the direction named.
FEATURE_LABELS = {
    "age": "Age (years)",
    "female": "Female",
    "hispanic": "Hispanic",
    "nh_black": "Non-Hispanic Black",
    "nh_asian_other": "Non-Hispanic Asian or other race",
    "public_only": "Public insurance only",
    "uninsured": "Uninsured all of 2017",
    "low_income": "Family income below 200% of poverty",
    "not_married": "Not married",
    "er_visits_17": "ER visits in 2017 (log)",
    "hosp_stays_17": "Hospital stays in 2017 (log)",
    "office_visits_17": "Office visits in 2017 (log)",
    "rx_fills_17": "Prescription fills in 2017 (log)",
    "home_health_17": "Any home health care in 2017",
    "physical_score": "Physical health summary (VR-12 PCS, higher = better)",
    "mental_score": "Mental health summary (VR-12 MCS, higher = better)",
    "distress_k6": "Psychological distress (K6, 0-24)",
    "depression_phq2": "Depression screen (PHQ-2, 0-6)",
    "pain": "Average pain last 7 days (0-10)",
    "fatigue": "Average fatigue last 7 days (1-5)",
    "poor_physical_rating": "Self-rated physical health (1 excellent - 5 poor)",
    "fear_recurrence": "Worry cancer will come back (1-5)",
    "current_treatment": "Currently treated for cancer",
    "recurrence": "Told cancer came back",
    "activity_limited": "Activities limited by cancer",
    "financial_toxicity": "Financial hardship items (0-7)",
    "cost_delay": "Delayed or skipped care because of cost (0-7)",
    "family_caregiver": "Family member provides care",
    "ca_breast": "Breast cancer",
    "ca_colon": "Colon cancer",
    "ca_lung": "Lung cancer",
    "ca_prostate": "Prostate cancer",
    "n_cancer_types": "Number of cancer types",
    "no_saq": "Did not complete the health questionnaire",
}

CANCER_COLS = ["CABLADDR", "CABREAST", "CACERVIX", "CACOLON", "CALUNG", "CALYMPH", "CAMELANO", "CAOTHER",
               "CAPROSTA", "CASKINNM", "CASKINDK", "CAUTERUS"]


def domain_features(df):
    X = pd.DataFrame(index=df.index)
    X["age"] = num(df.AGE17X)
    X["female"] = (df.SEX == 2).astype(float)
    X["hispanic"] = (df.RACETHX == 1).astype(float)
    X["nh_black"] = (df.RACETHX == 3).astype(float)
    X["nh_asian_other"] = df.RACETHX.isin([4, 5]).astype(float)
    X["public_only"] = (df.INSCOV17 == 2).astype(float)
    X["uninsured"] = (df.INSCOV17 == 3).astype(float)
    X["low_income"] = num(df.POVCAT17).le(3).astype(float).where(num(df.POVCAT17).notna())
    X["not_married"] = (df.MARRY17X != 1).astype(float)
    X["er_visits_17"] = np.log1p(num(df.ERTOT17))
    X["hosp_stays_17"] = np.log1p(num(df.IPDIS17))
    X["office_visits_17"] = np.log1p(num(df.OBTOTV17))
    X["rx_fills_17"] = np.log1p(num(df.RXTOT17))
    X["home_health_17"] = num(df.HHTOTD17).gt(0).astype(float).where(num(df.HHTOTD17).notna())
    X["physical_score"] = num(df.VPCS42)
    X["mental_score"] = num(df.VMCS42)
    X["distress_k6"] = num(df.K6SUM42)
    X["depression_phq2"] = num(df.PHQ242)
    X["pain"] = num(df.CEFPIN31)
    X["fatigue"] = num(df.CEFFTG31)
    X["poor_physical_rating"] = num(df.CEFPHL31)
    X["fear_recurrence"] = num(df.CEFBCK31)
    X["current_treatment"] = yes(df.CTRTMT31)
    X["recurrence"] = yes(df.CBCK31)
    X["activity_limited"] = yes(df.CEFACT31)
    X["financial_toxicity"] = count_yes(df, FINANCIAL)
    X["cost_delay"] = count_yes(df, DELAY)
    X["family_caregiver"] = yes(df.CFMEM31)
    X["ca_breast"] = yes(df.CABREAST)
    X["ca_colon"] = yes(df.CACOLON)
    X["ca_lung"] = yes(df.CALUNG)
    X["ca_prostate"] = yes(df.CAPROSTA)
    X["n_cancer_types"] = pd.concat([yes(df[c]) for c in CANCER_COLS], axis=1).sum(axis=1)
    X["no_saq"] = df.VPCS42.lt(0).astype(float)
    assert list(X.columns) == list(FEATURE_LABELS), "labels out of sync"
    return X


def subgroups(df):
    """Fairness groups (2017 values, never the outcome year)."""
    age = num(df.AGE17X)
    race = df.RACETHX.map({1: "Hispanic", 2: "NH White", 3: "NH Black", 4: "NH Asian", 5: "NH other/multiple"})
    ins = df.INSCOV17.map({1: "Any private", 2: "Public only", 3: "Uninsured"})
    cancer = np.select([yes(df.CALUNG) == 1, yes(df.CACOLON) == 1, yes(df.CABREAST) == 1, yes(df.CAPROSTA) == 1],
                       ["lung", "colon", "breast", "prostate"], "other only")
    return pd.DataFrame({
        "age": pd.cut(age, [0, 49, 64, 74, 200], labels=["18-49", "50-64", "65-74", "75+ (85 = top-coded)"]).astype(str),
        "sex": df.SEX.map({1: "Male", 2: "Female"}),
        "race_ethnicity": race,
        "insurance": ins,
        "cancer_type": cancer,
    }, index=df.index)


# Final model's inputs: the compact set the autoresearch loop and nested CV converged on (runs/autoresearch/log.md).
COMPACT = ["er_visits_17", "hosp_stays_17", "rx_fills_17", "office_visits_17", "home_health_17", "age", "physical_score",
           "mental_score", "depression_phq2", "distress_k6", "poor_physical_rating"]
RAW_USE = {"hosp_nights_17": ("IPNGTD17", "Hospital nights in 2017 (log)"),
           "outpatient_visits_17": ("OPTOTV17", "Hospital outpatient visits in 2017 (log)"),
           "home_health_days_17": ("HHTOTD17", "Home health days in 2017 (log)"),
           "spending_17": ("TOTEXP17", "Total health spending in 2017 (log $)"),
           "missed_work_days_17": ("DDNWRK17", "Work days missed for illness in 2017 (log)")}
FINAL_LABELS = {**{k: FEATURE_LABELS[k] for k in COMPACT}, **{k: lab for k, (_, lab) in RAW_USE.items()}}


def final_features(df):
    """COMPACT domain features + log1p of 5 raw 2017 use items (same values as autoresearch 'compact_raw_use')."""
    X = domain_features(df)[COMPACT].copy()
    for k, (col, _) in RAW_USE.items():
        X[k] = np.log1p(df[col].where(df[col] >= 0))
    return X
