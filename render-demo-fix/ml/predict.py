import os
import joblib
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from utils.text_preprocessing import clean_text, detect_disruption_type, estimate_affected_region

PIPELINE = None
try:
    if os.path.exists(Config.PIPELINE_PATH):
        PIPELINE = joblib.load(Config.PIPELINE_PATH)
except Exception as e:
    print(f"Warning: Failed to load pipeline - {e}")

def predict_risk(text: str) -> dict:
    """Returns {label, confidence, disruption_type, affected_regions, estimated_duration_days}"""
    try:
        disruption_type = detect_disruption_type(text)
        affected_regions = estimate_affected_region(text)
        
        # Simple duration estimation heuristic
        duration_days = 0
        if "CRITICAL" in text.upper(): duration_days = 14
        elif "HIGH" in text.upper(): duration_days = 7
        elif "MEDIUM" in text.upper(): duration_days = 3
        else:
            if disruption_type == "war": duration_days = 30
            elif disruption_type == "port_strike": duration_days = 7
            elif disruption_type == "customs": duration_days = 5
            elif disruption_type == "weather": duration_days = 4
            elif disruption_type == "cyber": duration_days = 2
            elif disruption_type == "supplier": duration_days = 10
            elif disruption_type == "logistics": duration_days = 3

        if PIPELINE is None:
            return {
                "label": Config.DEFAULT_RISK,
                "confidence": 0.0,
                "disruption_type": disruption_type,
                "affected_regions": affected_regions,
                "estimated_duration_days": duration_days
            }
            
        cleaned = clean_text(text)
        prediction = PIPELINE.predict([cleaned])[0]
        probs = PIPELINE.predict_proba([cleaned])[0]
        confidence = float(max(probs))
        
        return {
            "label": str(prediction),
            "confidence": round(confidence, 4),
            "disruption_type": disruption_type,
            "affected_regions": affected_regions,
            "estimated_duration_days": duration_days
        }
    except Exception as e:
        print(f"Error in predict_risk: {e}")
        return {
            "label": Config.DEFAULT_RISK,
            "confidence": 0.0,
            "disruption_type": "normal",
            "affected_regions": ["global"],
            "estimated_duration_days": 0
        }

def batch_predict(texts: list) -> list:
    results = []
    for text in texts:
        results.append(predict_risk(text))
    return results