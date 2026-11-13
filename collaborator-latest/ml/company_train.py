"""
Company-Specific Multi-Feature Supply Chain Disruption Predictor.
Trains on structured features (not just text) to predict disruption labels.
Features: supplier reliability, affected units, revenue at risk,
          delay days, region, disruption type history, product line, route risk.
"""
import os, sys, json
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, f1_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

COMPANY_MODEL_PATH   = os.path.join(Config.ARTEFACTS_DIR, "company_model.pkl")
COMPANY_ENCODER_PATH = os.path.join(Config.ARTEFACTS_DIR, "company_encoders.pkl")
COMPANY_REPORT_PATH  = os.path.join(Config.ARTEFACTS_DIR, "company_training_report.json")
COMPANY_DATASET      = os.path.join(Config.DATA_DIR, "company_dataset.csv")

CAT_FEATURES = ["supplier_country", "product_line", "disruption_type", "region", "route_id"]
NUM_FEATURES = ["affected_units", "delay_days", "revenue_at_risk_usd", "supplier_reliability_score"]

def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Financial exposure per unit
    df["cost_per_unit"] = (df["revenue_at_risk_usd"] / (df["affected_units"] + 1)).round(2)
    # Risk score (low reliability = high risk)
    df["supplier_risk_index"] = (1 - df["supplier_reliability_score"]) * (df["delay_days"] + 1)
    # Volume severity
    df["volume_severity"] = pd.cut(
        df["affected_units"],
        bins=[0, 2000, 7000, 15000, 999999],
        labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ).astype(str)
    # Month (seasonality)
    df["month"] = pd.to_datetime(df["date"]).dt.month
    # Is normal (no disruption)
    df["is_normal"] = (df["disruption_type"] == "normal").astype(int)
    return df

def train():
    print("=" * 55)
    print("  TechCore Industries — Company Model Training")
    print("=" * 55)

    df = pd.read_csv(COMPANY_DATASET)
    print(f"\n  Dataset: {len(df)} events | {df['label'].value_counts().to_dict()}")

    df = _engineer_features(df)

    all_cat = CAT_FEATURES + ["volume_severity"]
    all_num = NUM_FEATURES + ["cost_per_unit", "supplier_risk_index", "month", "is_normal"]

    X = df[all_cat + all_num]
    y = df["label"]

    preprocessor = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), all_cat),
        ("num", StandardScaler(), all_num),
    ])

    models = {
        "GradientBoosting": GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.08, random_state=42),
        "RandomForest":     RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42),
        "LogisticRegression": LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0),
    }

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    best_name, best_f1, best_pipe = None, -1, None
    results = {}

    for name, clf in models.items():
        pipe = Pipeline([("pre", preprocessor), ("clf", clf)])
        cv_scores = cross_val_score(pipe, X_train, y_train, cv=StratifiedKFold(n_splits=5), scoring="f1_macro")
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        f1 = f1_score(y_test, preds, average="macro", zero_division=0)
        results[name] = {"cv_mean": round(float(cv_scores.mean()), 4), "test_f1": round(f1, 4),
                         "report": classification_report(y_test, preds, output_dict=True, zero_division=0)}
        print(f"  {name:<22} CV F1: {cv_scores.mean():.4f}  Test F1: {f1:.4f}")
        if f1 > best_f1:
            best_f1, best_name, best_pipe = f1, name, pipe

    print(f"\n  [OK] Best Model: {best_name} (Test F1={best_f1:.4f})")
    os.makedirs(Config.ARTEFACTS_DIR, exist_ok=True)
    joblib.dump(best_pipe, COMPANY_MODEL_PATH)

    encoders = {"cat_features": all_cat, "num_features": all_num, "label_classes": list(y.unique())}
    joblib.dump(encoders, COMPANY_ENCODER_PATH)

    report = {"best_model": best_name, "best_f1": best_f1, "all_models": results}
    with open(COMPANY_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"  Model saved -> {COMPANY_MODEL_PATH}")
    print("=" * 55)

if __name__ == "__main__":
    train()
