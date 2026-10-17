"""Per-survivor explanations for the final model (imputer -> sigmoid-calibrated random forest).

Each of the 5 calibration folds holds a forest f_k and a sigmoid p = expit(-(a_k * f_k + b_k)), so the fold's
calibrated log-odds is linear in the forest score. TreeSHAP splits f_k exactly into per-feature parts, and
multiplying by -a_k turns them into exact log-odds contributions for that fold. We report the mean over folds.
The final risk is the mean of the fold probabilities (not of the log-odds), so contributions sum to the risk's
log-odds only approximately; they rank drivers, they do not reconstruct the number to the decimal.
"""
import numpy as np
import pandas as pd
import shap


def feature_names(model, columns):
    imp = model.steps[0][1]
    return list(columns) + [f"missing:{columns[j]}" for j in imp.indicator_.features_]


def contributions(model, X):
    """DataFrame (survivors x features + missing indicators) of calibrated log-odds contributions."""
    imp, cal = model.steps[0][1], model.steps[-1][1]
    Z = imp.transform(X)
    parts = []
    for cc in cal.calibrated_classifiers_:
        sv = shap.TreeExplainer(cc.estimator).shap_values(Z, check_additivity=False)
        sv = sv[..., 1] if np.ndim(sv) == 3 else sv[1]
        parts.append(-cc.calibrators[0].a_ * sv)
    return pd.DataFrame(np.mean(parts, axis=0), index=X.index, columns=feature_names(model, list(X.columns)))
