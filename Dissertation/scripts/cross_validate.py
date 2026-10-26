"""5-fold stratified cross-validation of the three candidate classifiers on the full labeled dataset.

Usage (from the Dissertation/ folder):  python scripts/cross_validate.py
Output: reports/cross_validation_metrics.csv

Note: this is a re-implementation. The original notebook/script behind Table 7 of the report
is not in the repository, so figures agree closely (F1 ~0.96) but not to the last decimal.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pandas as pd
from imblearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_validate

from src.feature_engineering import FeatureEngineer
from src.ml_pipeline import RequirementMLPipeline
from src.preprocessing import DataPreprocessor

df = pd.read_excel(os.path.join(ROOT, "data", "Jira_Requirements_Master_Dataset.xls"))
df = FeatureEngineer.engineer_features(DataPreprocessor.clean_data(df))
X, y = df[["Combined", "vague_term_density"]], df["Label_Numeric"].astype(int)

rows = []
for name in RequirementMLPipeline().models:
    base = RequirementMLPipeline()  # fresh preprocessor/SMOTE per model
    pipe = Pipeline([("prep", base.preprocessor), ("smote", base.smote), ("clf", base.models[name])])
    cv = cross_validate(pipe, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=42),
                        scoring=["accuracy", "precision", "recall", "f1"])
    rows.append({"Model": name, **{m: round(cv[f"test_{m}"].mean(), 4) for m in ("accuracy", "precision", "recall", "f1")},
                 "F1_std": round(cv["test_f1"].std(), 4)})

out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv(os.path.join(ROOT, "reports", "cross_validation_metrics.csv"), index=False)
