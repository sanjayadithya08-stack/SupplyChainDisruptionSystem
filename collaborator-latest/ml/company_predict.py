"""
Company-Specific Predictor.
Accepts structured supply chain event data and predicts disruption label + financial impact.
"""
import os, sys
import pandas as pd
import joblib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

COMPANY_MODEL_PATH   = Config.COMPANY_MODEL_PATH
COMPANY_ENCODER_PATH = Config.COMPANY_ENCODER_PATH

_MODEL    = None
_ENCODERS = None

def _load():
    global _MODEL, _ENCODERS
    if _MODEL is not None: return True
    try:
        if os.path.exists(COMPANY_MODEL_PATH) and os.path.exists(COMPANY_ENCODER_PATH):
            _MODEL    = joblib.load(COMPANY_MODEL_PATH)
            _ENCODERS = joblib.load(COMPANY_ENCODER_PATH)
            return True
    except Exception as e:
        print(f"[CompanyPredict] Load failed: {e}")
    return False

def _engineer(row: dict) -> dict:
    units    = float(row.get("affected_units", 0))
    delay    = float(row.get("delay_days", 0))
    revenue  = float(row.get("revenue_at_risk_usd", 0))
    rel      = float(row.get("supplier_reliability_score", 0.8))
    dtype    = row.get("disruption_type", "normal")

    cost_per_unit       = round(revenue / (units + 1), 2)
    supplier_risk_index = round((1 - rel) * (delay + 1), 4)
    month               = int(str(row.get("date", "2024-01-01")).split("-")[1]) if row.get("date") else 1
    is_normal           = 1 if dtype == "normal" else 0

    if units < 2000:   vol = "LOW"
    elif units < 7000: vol = "MEDIUM"
    elif units < 15000:vol = "HIGH"
    else:              vol = "CRITICAL"

    return {
        "supplier_country":           row.get("supplier_country", "Unknown"),
        "product_line":               row.get("product_line", "Unknown"),
        "disruption_type":            dtype,
        "region":                     row.get("region", "global"),
        "route_id":                   str(row.get("route_id", "R1")),
        "volume_severity":            vol,
        "affected_units":             units,
        "delay_days":                 delay,
        "revenue_at_risk_usd":        revenue,
        "supplier_reliability_score": rel,
        "cost_per_unit":              cost_per_unit,
        "supplier_risk_index":        supplier_risk_index,
        "month":                      month,
        "is_normal":                  is_normal,
    }

def predict_event(event: dict) -> dict:
    """
    Predict disruption label for a structured supply chain event.
    event keys: supplier_country, product_line, disruption_type, region,
                route_id, affected_units, delay_days, revenue_at_risk_usd,
                supplier_reliability_score, date
    """
    fallback = {
        "label": "UNKNOWN", "confidence": 0.0,
        "revenue_at_risk_usd": event.get("revenue_at_risk_usd", 0),
        "delay_days": event.get("delay_days", 0),
        "affected_units": event.get("affected_units", 0),
        "supplier": event.get("supplier_name", "Unknown"),
        "product_line": event.get("product_line", "Unknown"),
        "disruption_type": event.get("disruption_type", "normal"),
        "region": event.get("region", "global"),
        "model": "fallback"
    }
    if not _load():
        return fallback
    try:
        engineered = _engineer(event)
        df = pd.DataFrame([engineered])
        pred  = _MODEL.predict(df)[0]
        proba = _MODEL.predict_proba(df)[0]
        conf  = round(float(max(proba)), 4)
        return {
            "label": str(pred), "confidence": conf,
            "revenue_at_risk_usd": event.get("revenue_at_risk_usd", 0),
            "delay_days": event.get("delay_days", 0),
            "affected_units": event.get("affected_units", 0),
            "supplier": event.get("supplier_name", "Unknown"),
            "product_line": event.get("product_line", "Unknown"),
            "disruption_type": event.get("disruption_type", "normal"),
            "region": event.get("region", "global"),
            "model": "company_model"
        }
    except Exception as e:
        print(f"[CompanyPredict] Inference error: {e}")
        return fallback

def predict_all_historical() -> list[dict]:
    """Run predictions over the full company dataset (one batched model call)."""
    try:
        path = os.path.join(Config.DATA_DIR, "company_dataset.csv")
        df = pd.read_csv(path)
        rows = df.to_dict(orient="records")
        if not _load():
            preds, confs, model = ["UNKNOWN"] * len(rows), [0.0] * len(rows), "fallback"
        else:
            X = pd.DataFrame([_engineer(r) for r in rows])
            preds = [str(p) for p in _MODEL.predict(X)]
            confs = [round(float(max(p)), 4) for p in _MODEL.predict_proba(X)]
            model = "company_model"
        out = []
        for r, label, conf in zip(rows, preds, confs):
            out.append({
                "label": label, "confidence": conf,
                "revenue_at_risk_usd": float(r["revenue_at_risk_usd"]),
                "delay_days": float(r["delay_days"]),
                "affected_units": float(r["affected_units"]),
                "supplier": r.get("supplier_name", "Unknown"),
                "product_line": r.get("product_line", "Unknown"),
                "disruption_type": r.get("disruption_type", "normal"),
                "region": r.get("region", "global"),
                "model": model,
                "event_id": r["event_id"], "date": r["date"], "actual": r["label"],
                "correct": label == r["label"], "sku": r.get("sku", ""),
                "supplier_name": r.get("supplier_name", ""),
            })
        return out
    except Exception as e:
        print(f"[CompanyPredict] Historical batch error: {e}")
        return []
