"""Train an experimental port-weather impact model from CyPort interactions.

This is separate from the company shipment classifier: CyPort labels port-level
cyclone impact, not shipment delays or company shipment severity.
"""
import json
import os
import sys

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from utils.config import Config

SOURCE = os.path.join(Config.DATA_DIR, 'source_snapshots', 'cyport_interaction.csv')
MODEL_PATH = os.path.join(Config.ARTEFACTS_DIR, 'port_weather_impact_model.pkl')
REPORT_PATH = os.path.join(Config.ARTEFACTS_DIR, 'port_weather_impact_report.json')
FEATURES = [
    'WIND', 'PRESSURE', 'DISTANCE', 'Wind_speed', 'Surge_height', 'Rainfall',
    'SSHS', 'IF_LANDFALL_CLOSE2PORT', 'IF_LANDFALL', 'Port_ranking',
    'D_normal', 'C_normal', 'B_normal', 'E_normal',
    'Coast_Gulf_of_Mexico', 'Coast_Atlantic', 'Coast_Pacific',
]


def train():
    df = pd.read_csv(SOURCE)
    y = (pd.to_numeric(df['total_impact'], errors='coerce').fillna(0) > 0).astype(int)
    X = df[FEATURES].apply(pd.to_numeric, errors='coerce')
    groups = df['SID'].astype(str)

    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(split.split(X, y, groups=groups))
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('classifier', RandomForestClassifier(
            n_estimators=400, class_weight='balanced_subsample',
            min_samples_leaf=3, random_state=42, n_jobs=-1,
        )),
    ])
    model.fit(X.iloc[train_idx], y.iloc[train_idx])
    prediction = model.predict(X.iloc[test_idx])
    probability = model.predict_proba(X.iloc[test_idx])[:, 1]
    report = {
        'model': 'RandomForestClassifier',
        'target': 'CyPort total_impact > 0 (observed port impact)',
        'features': FEATURES,
        'source': 'CyPort CC BY 4.0, https://github.com/ChenchenMobility/Maritime-Data-CyPort',
        'source_rows': int(len(df)),
        'source_positive_rows': int(y.sum()),
        'train_rows': int(len(train_idx)),
        'test_rows': int(len(test_idx)),
        'train_cyclones': int(groups.iloc[train_idx].nunique()),
        'test_cyclones': int(groups.iloc[test_idx].nunique()),
        'split': 'held out complete cyclone IDs to limit storm leakage',
        'metrics': {
            'balanced_accuracy': round(float(balanced_accuracy_score(y.iloc[test_idx], prediction)), 4),
            'precision': round(float(precision_score(y.iloc[test_idx], prediction, zero_division=0)), 4),
            'recall': round(float(recall_score(y.iloc[test_idx], prediction, zero_division=0)), 4),
            'f1': round(float(f1_score(y.iloc[test_idx], prediction, zero_division=0)), 4),
            'average_precision': round(float(average_precision_score(y.iloc[test_idx], probability)), 4),
        },
        'limitation': 'Port-level U.S. tropical-cyclone impact only; not a shipment delay or multi-cause company model.',
    }
    joblib.dump({'pipeline': model, 'features': FEATURES, 'target': report['target']}, MODEL_PATH)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f'Model saved: {MODEL_PATH}')


if __name__ == '__main__':
    train()
