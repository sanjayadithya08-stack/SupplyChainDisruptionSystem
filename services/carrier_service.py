"""Optional generic carrier webhook for confirmed reroute requests."""
import re

import requests

from utils.config import Config

_REROUTE_TERMS = re.compile(r"rerout|alternate (?:port|route)|switch to .*route|switch carrier", re.I)


def execute_carrier_actions(shipment: dict, actions: list[str], cause: str, mode: str) -> dict:
    reroute_actions = [action for action in actions if _REROUTE_TERMS.search(action)]
    if not reroute_actions:
        return {"status": "not_applicable", "message": "No carrier reroute action in this plan."}
    if not Config.CARRIER_WEBHOOK_URL:
        return {
            "status": "requires_carrier_integration",
            "message": "Reroute recommended but not executed; configure CARRIER_WEBHOOK_URL to connect a carrier.",
        }

    headers = {"Content-Type": "application/json"}
    if Config.CARRIER_API_TOKEN:
        headers["Authorization"] = f"Bearer {Config.CARRIER_API_TOKEN}"
    payload = {
        "event": "shipment.reroute.requested",
        "shipment": {
            "id": shipment.get("id"), "route_id": shipment.get("route_id"),
            "carrier": shipment.get("carrier"), "origin": shipment.get("origin"),
            "destination": shipment.get("destination"), "sku": shipment.get("sku"),
        },
        "cause": cause,
        "response_mode": mode,
        "requested_actions": reroute_actions,
    }
    try:
        response = requests.post(
            Config.CARRIER_WEBHOOK_URL, json=payload, headers=headers,
            timeout=Config.CARRIER_WEBHOOK_TIMEOUT,
        )
        try:
            result = response.json()
        except ValueError:
            result = {}
        if response.ok and str(result.get("status", "")).lower() == "confirmed":
            new_route_id = result.get("route_id")
            if new_route_id:
                from db.models import get_session, RouteModel, ShipmentModel
                with get_session() as session:
                    route = session.query(RouteModel).filter(RouteModel.id == new_route_id).first()
                    row = session.query(ShipmentModel).filter(ShipmentModel.id == shipment.get("id")).first()
                    if not route or not row:
                        return {"status": "confirmation_invalid", "message": "Carrier confirmation referenced an unknown shipment or route."}
                    row.route_id = new_route_id
                    session.commit()
            return {
                "status": "confirmed",
                "message": result.get("message") or "Carrier confirmed the reroute.",
                "route_id": new_route_id or shipment.get("route_id"),
                "carrier_reference": result.get("reference"),
                "demo": bool(result.get("demo", False)),
            }
        if response.ok and str(result.get("status", "")).lower() in {"rejected", "declined"}:
            return {"status": "carrier_rejected", "message": result.get("message", "Carrier rejected the reroute request.")}
        if response.ok:
            return {"status": "awaiting_carrier_confirmation", "message": "Carrier received the request; no confirmation was returned."}
        return {"status": "carrier_request_failed", "message": f"Carrier returned HTTP {response.status_code}."}
    except requests.RequestException as exc:
        return {"status": "carrier_request_failed", "message": f"Carrier connection failed ({type(exc).__name__})."}
