"""Scheduled disruption scanning, persistence, and controlled mitigation."""
from datetime import datetime
import hashlib
import json
import threading
from uuid import uuid4

from db.models_extended import ActionModel, Base, DisruptionEventModel, engine, get_session
from services.action_service import record_action
from utils.config import Config

_stop_event = threading.Event()
_worker: threading.Thread | None = None

def _ensure_table():
    Base.metadata.create_all(engine)

def _fingerprint(shipment_id: str, prediction: dict, threats: list[dict]) -> str:
    material = {
        "shipment_id": shipment_id,
        "risk": prediction.get("label"),
        "type": prediction.get("disruption_type"),
        "threats": sorted(t.get("desc", "") for t in threats),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()

def _event_to_dict(event: DisruptionEventModel) -> dict:
    return {
        "id": event.id, "shipment_id": event.shipment_id, "risk_level": event.risk_level,
        "confidence": event.confidence, "disruption_type": event.disruption_type,
        "source_summary": event.source_summary, "plan": json.loads(event.plan_json or "{}"),
        "status": event.status,
        "detected_at": event.detected_at.isoformat(), "last_seen_at": event.last_seen_at.isoformat(),
        "mitigated_at": event.mitigated_at.isoformat() if event.mitigated_at else None,
    }

def _apply_critical_response(event: dict):
    try:
        from services.critical_response_service import execute_critical_response
        execute_critical_response(event["event"], event["shipment"])
    except Exception as exc:
        record_action(
            "critical_response_failed",
            f"Automatic critical follow-up failed for {event['shipment']['id']}; operator review is required.",
            shipment_id=event["shipment"]["id"], actor="system", status="failed",
            metadata={"event_id": event["event_id"], "error": str(exc)},
        )

def compact_open_disruptions() -> int:
    """Keep one current open case per shipment; archive repeat scan variants."""
    _ensure_table()
    archived = 0
    with get_session() as session:
        rows = session.query(DisruptionEventModel).filter_by(status="open").order_by(
            DisruptionEventModel.last_seen_at.desc(), DisruptionEventModel.detected_at.desc()
        ).all()
        seen_shipments = set()
        for event in rows:
            if event.shipment_id in seen_shipments:
                event.status = "archived"
                archived += 1
            else:
                seen_shipments.add(event.shipment_id)
        if archived:
            session.commit()
    return archived

def run_scan(actor: str = "scheduler") -> dict:
    """Predict risk for every active shipment and persist high-impact findings."""
    from ml.live_threat_engine import analyze_live_shipments
    _ensure_table()
    compact_open_disruptions()
    results = analyze_live_shipments()
    now = datetime.utcnow()
    new_events, updated_events, missing_responses = [], [], []
    elevated_shipments = {
        result.get("shipment", {}).get("id")
        for result in results
        if result.get("prediction", {}).get("label") in {"HIGH", "CRITICAL"}
    }

    with get_session() as session:
        # A case is current only while today's scan still finds an elevated
        # threat. Preserve older records as archived history once it clears.
        for event in session.query(DisruptionEventModel).filter_by(status="open").all():
            if event.shipment_id not in elevated_shipments:
                event.status = "archived"

        for result in results:
            prediction = result.get("prediction", {})
            if prediction.get("label") not in {"HIGH", "CRITICAL"}:
                continue
            shipment = result["shipment"]
            threats = result.get("threats", [])
            fingerprint = _fingerprint(shipment["id"], prediction, threats)
            event = session.query(DisruptionEventModel).filter_by(fingerprint=fingerprint).first()
            current_open = session.query(DisruptionEventModel).filter_by(
                shipment_id=shipment["id"], status="open"
            ).order_by(DisruptionEventModel.last_seen_at.desc()).first()
            if current_open:
                current_open.risk_level = prediction["label"]
                current_open.confidence = float(prediction.get("confidence", 0))
                current_open.disruption_type = prediction.get("disruption_type", "logistics")
                current_open.source_summary = " | ".join(t.get("desc", "") for t in threats)[:2000]
                current_open.plan_json = json.dumps(result.get("plan") or {})
                current_open.last_seen_at = now
                updated_events.append(current_open.id)
                if (prediction.get("label") == "CRITICAL" and Config.AUTO_CRITICAL_RESPONSE_ENABLED):
                    response_token = f'"event_id": "{current_open.id}"'
                    response_exists = session.query(ActionModel).filter(
                        ActionModel.action_type.in_(["critical_response_automated", "critical_response_failed"]),
                        ActionModel.metadata_json.contains(response_token),
                    ).first()
                    if not response_exists:
                        missing_responses.append({
                            "event_id": current_open.id, "event": _event_to_dict(current_open),
                            "shipment": shipment, "prediction": prediction,
                        })
                continue
            if event:
                event.last_seen_at = now
                event.confidence = float(prediction.get("confidence", 0))
                if event.status == "archived":
                    event.status = "open"
                    event.mitigated_at = None
                    event.detected_at = now
                    new_events.append({
                        "event_id": event.id, "event": _event_to_dict(event),
                        "shipment": shipment, "prediction": prediction,
                    })
                else:
                    updated_events.append(event.id)
                    if (event.status == "open" and prediction.get("label") == "CRITICAL"
                            and Config.AUTO_CRITICAL_RESPONSE_ENABLED):
                        response_token = f'"event_id": "{event.id}"'
                        response_exists = session.query(ActionModel).filter(
                            ActionModel.action_type.in_(["critical_response_automated", "critical_response_failed"]),
                            ActionModel.metadata_json.contains(response_token),
                        ).first()
                        if not response_exists:
                            missing_responses.append({
                                "event_id": event.id, "event": _event_to_dict(event),
                                "shipment": shipment, "prediction": prediction,
                            })
                continue

            event = DisruptionEventModel(
                id=f"DSP-{uuid4().hex[:12].upper()}", fingerprint=fingerprint,
                shipment_id=shipment["id"], risk_level=prediction["label"],
                confidence=float(prediction.get("confidence", 0)),
                disruption_type=prediction.get("disruption_type", "logistics"),
                source_summary=" | ".join(t.get("desc", "") for t in threats)[:2000],
                plan_json=json.dumps(result.get("plan") or {}), status="open",
                detected_at=now, last_seen_at=now,
            )
            session.add(event)
            new_events.append({
                "event_id": event.id, "event": _event_to_dict(event),
                "shipment": shipment, "prediction": prediction,
            })
        session.commit()

    for event in new_events:
        record_action(
            "disruption_detected",
            f"{event['prediction']['label']} {event['prediction'].get('disruption_type', 'disruption')} risk detected for {event['shipment']['id']}.",
            shipment_id=event["shipment"]["id"], actor=actor,
            metadata={"event_id": event["event_id"], "prediction": event["prediction"]},
        )
        if event["prediction"].get("label") == "CRITICAL" and Config.AUTO_CRITICAL_RESPONSE_ENABLED:
            _apply_critical_response(event)
        elif Config.AUTO_MITIGATION_ENABLED:
            from services.automation_service import auto_handle_disruption
            auto_handle_disruption(
                shipment_id=event["shipment"]["id"], disruption_type=event["prediction"].get("disruption_type", "logistics"),
                risk_level=event["prediction"]["label"], supplier_id=event["shipment"]["supplier_id"],
                affected_sku=event["shipment"]["sku"],
            )
            mark_mitigated(event["event_id"], actor="automation")

    for event in missing_responses:
        _apply_critical_response(event)

    record_action("threat_scan_completed", f"Threat scan completed: {len(new_events)} new and {len(updated_events)} refreshed disruptions.",
                  actor=actor, metadata={"new": len(new_events), "refreshed": len(updated_events)})
    return {"scanned_shipments": len(results), "new_events": len(new_events), "refreshed_events": len(updated_events), "results": results}

def get_disruptions(status: str | None = None, limit: int = 100) -> list[dict]:
    _ensure_table()
    with get_session() as session:
        query = session.query(DisruptionEventModel)
        if status:
            query = query.filter(DisruptionEventModel.status == status)
        return [_event_to_dict(event) for event in query.order_by(DisruptionEventModel.last_seen_at.desc()).limit(limit).all()]

def mark_mitigated(event_id: str, actor: str = "operator", resolution: str | None = None) -> dict | None:
    _ensure_table()
    with get_session() as session:
        event = session.query(DisruptionEventModel).filter_by(id=event_id).first()
        if not event:
            return None
        event.status = "mitigated"
        event.mitigated_at = datetime.utcnow()
        session.commit()
        result = _event_to_dict(event)
    summary = (f"Response recorded for {result['shipment_id']}: {resolution}" if resolution
               else f"Disruption {event_id} marked mitigated.")
    record_action("disruption_mitigated", summary, shipment_id=result["shipment_id"], actor=actor,
                  metadata={"event_id": event_id, "resolution": resolution} if resolution else {"event_id": event_id})
    return result

def _scheduler_loop():
    while not _stop_event.is_set():
        try:
            run_scan()
        except Exception as exc:
            record_action("threat_scan_failed", f"Scheduled threat scan failed: {exc}", actor="scheduler", status="failed")
        _stop_event.wait(Config.SCAN_INTERVAL_SECONDS)

def start_scheduler():
    global _worker
    _ensure_table()
    compact_open_disruptions()
    if not Config.AUTO_SCAN_ENABLED or (_worker and _worker.is_alive()):
        return
    _stop_event.clear()
    _worker = threading.Thread(target=_scheduler_loop, name="disruption-monitor", daemon=True)
    _worker.start()

def stop_scheduler():
    _stop_event.set()
