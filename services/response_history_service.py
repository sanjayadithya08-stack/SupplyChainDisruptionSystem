"""Persist automated threat responses for the operator's action history."""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from utils.config import Config

HISTORY_PATH = os.path.join(Config.LOGS_DIR, "response_history.jsonl")


def record_response(entry: dict) -> dict:
    if Config.DATABASE_URL:
        entry.setdefault("response_id", str(uuid.uuid4()))
        entry.setdefault("outcome", "in_progress")
        entry.setdefault("updated_at", entry.get("timestamp", datetime.now(timezone.utc).isoformat()))
        from services.event_store import write_event
        write_event("response", entry["response_id"], entry)
        return entry
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    entry.setdefault("response_id", str(uuid.uuid4()))
    entry.setdefault("outcome", "in_progress")
    entry.setdefault("updated_at", entry.get("timestamp", datetime.now(timezone.utc).isoformat()))
    with open(HISTORY_PATH, "a", encoding="utf-8") as history:
        history.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def get_response_history(limit: int = 30) -> list[dict]:
    if Config.DATABASE_URL:
        from services.event_store import list_events
        return list_events("response", limit)
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as history:
            entries = [json.loads(line) for line in history if line.strip()]
        return list(reversed(entries[-max(1, limit):]))
    except (OSError, json.JSONDecodeError):
        return []


def _recent_dispatch_entries(hours: int = 24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for entry in get_response_history(10000):
        if not entry.get("shipment_id") or not entry.get("cause"):
            continue
        try:
            timestamp = datetime.fromisoformat(str(entry.get("timestamp", "")).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            if timestamp >= cutoff:
                yield entry
        except (TypeError, ValueError):
            continue


def get_recent_dispatch_keys(hours: int = 24) -> set[tuple[str, str]]:
    """Return shipment/cause pairs with a response dispatched in the cooldown window."""
    return {
        (str(entry["shipment_id"]), str(entry["cause"]).strip().lower())
        for entry in _recent_dispatch_entries(hours)
    }


def find_recent_dispatch(shipment_id: str, cause: str, hours: int = 24) -> dict | None:
    """Find a recent response for this shipment and cause, regardless of risk label."""
    normalized_cause = str(cause).strip().lower()
    for entry in _recent_dispatch_entries(hours):
        channel = str(entry.get("notification_channel", "log"))
        if channel == "log" or channel.startswith("not ") or channel.startswith("already sent") or channel.startswith("duplicate suppressed"):
            continue
        if (str(entry["shipment_id"]) == str(shipment_id)
                and str(entry["cause"]).strip().lower() == normalized_cause):
            return entry
    return None


def find_recent_delivery(shipment_id: str, cause: str, risk: str, hours: int = 24) -> dict | None:
    """Return an already delivered matching alert to prevent duplicate messages."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for entry in get_response_history(10000):
        if entry.get("shipment_id") != shipment_id or entry.get("cause") != cause or entry.get("risk") != risk:
            continue
        channel = str(entry.get("notification_channel", "log"))
        if channel == "log" or channel.startswith("not ") or channel.startswith("already sent") or channel.startswith("duplicate suppressed"):
            continue
        try:
            timestamp = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            if timestamp >= cutoff:
                return entry
        except (TypeError, ValueError):
            continue
    return None


def find_recent_carrier_confirmation(shipment_id: str, cause: str, risk: str, hours: int = 24) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for entry in get_response_history(10000):
        if entry.get("shipment_id") != shipment_id or entry.get("cause") != cause or entry.get("risk") != risk:
            continue
        if (entry.get("carrier_execution") or {}).get("status") != "confirmed":
            continue
        try:
            timestamp = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            if timestamp >= cutoff:
                return entry
        except (TypeError, ValueError):
            continue
    return None


def update_response_outcome(response_id: str, outcome: str, note: str = "") -> dict | None:
    allowed = {"in_progress", "completed", "rejected"}
    if outcome not in allowed:
        raise ValueError("Outcome must be in_progress, completed, or rejected")
    if Config.DATABASE_URL:
        from services.event_store import update_event
        for entry in get_response_history(10000):
            if entry.get("response_id") == response_id:
                return update_event("response", response_id, {
                    "outcome": outcome, "outcome_note": (note or "").strip()[:500],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
        return None
    if not os.path.exists(HISTORY_PATH):
        return None
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as history:
            entries = [json.loads(line) for line in history if line.strip()]
        found = None
        for entry in entries:
            if entry.get("response_id") == response_id:
                entry["outcome"] = outcome
                entry["outcome_note"] = (note or "").strip()[:500]
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                found = entry
        if found:
            temp_path = HISTORY_PATH + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as history:
                for entry in entries:
                    history.write(json.dumps(entry, ensure_ascii=False) + "\n")
            os.replace(temp_path, HISTORY_PATH)
        return found
    except (OSError, json.JSONDecodeError):
        return None
