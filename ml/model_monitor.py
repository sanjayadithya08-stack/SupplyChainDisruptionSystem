import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

def log_prediction(prediction: dict, plan: dict):
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "prediction": prediction,
            "plan_priority": plan.get("priority", "Unknown"),
            "immediate_actions": len(plan.get("immediate_actions", []))
        }

        if Config.DATABASE_URL:
            import uuid
            from services.event_store import write_event
            write_event("prediction", str(uuid.uuid4()), log_entry)
        else:
            with open(Config.PREDICTIONS_LOG_PATH, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Error writing to predictions.log: {e}")

def get_stats() -> dict:
    stats = {level: 0 for level in Config.RISK_LEVELS}
    stats[Config.DEFAULT_RISK] = 0
    stats["total"] = 0
    disruptions = {}

    try:
        if Config.DATABASE_URL:
            from services.event_store import list_events
            entries = list(reversed(list_events("prediction", 10000)))
        else:
            if not os.path.exists(Config.PREDICTIONS_LOG_PATH):
                return stats
            with open(Config.PREDICTIONS_LOG_PATH, "r") as f:
                entries = f.readlines()
        for line in entries:
            if not isinstance(line, dict) and not line.strip():
                continue
            try:
                entry = line if isinstance(line, dict) else json.loads(line)
                pred = entry.get("prediction", {})
                risk = pred.get("label", Config.DEFAULT_RISK)
                dtype = pred.get("disruption_type", "Unknown")

                if risk in stats: stats[risk] += 1
                else: stats[risk] = 1

                disruptions[dtype] = disruptions.get(dtype, 0) + 1
                stats["total"] += 1
            except Exception:
                pass

        stats["disruptions"] = disruptions
        return stats
    except Exception as e:
        print(f"Error reading stats: {e}")
        return stats

def get_recent(n: int = 5) -> list:
    recent = []
    try:
        if Config.DATABASE_URL:
            from services.event_store import list_events
            return list_events("prediction", n)
        if not os.path.exists(Config.PREDICTIONS_LOG_PATH):
            return recent
        with open(Config.PREDICTIONS_LOG_PATH, "r") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if not line.strip(): continue
            try:
                recent.append(json.loads(line))
                if len(recent) >= n: break
            except:
                pass
        return recent
    except Exception as e:
        print(f"Error reading recent: {e}")
        return recent
