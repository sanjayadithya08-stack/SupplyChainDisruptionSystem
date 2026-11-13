"""Local mock carrier API for demonstrating reroutes without changing real shipments."""
from fastapi import FastAPI, Header, HTTPException
from db.models import RouteModel, get_session
from utils.config import Config

app = FastAPI(title="Supply Chain Mock Carrier", version="1.0.0")
_RISK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

@app.get("/health")
def health():
    return {"status": "healthy", "mode": "demo_only"}

@app.post("/carrier/reroute")
def request_reroute(payload: dict, authorization: str | None = Header(default=None)):
    """Confirm only a catalogued, same-origin/destination route with lower risk."""
    if Config.CARRIER_API_TOKEN and authorization != f"Bearer {Config.CARRIER_API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid mock carrier token")
    shipment = payload.get("shipment") or {}
    shipment_id = shipment.get("id", "unknown")
    route_id = shipment.get("route_id")
    session = get_session()
    try:
        current = session.query(RouteModel).filter(RouteModel.id == route_id).first()
        if not current:
            return {"status": "rejected", "message": "Mock carrier cannot find the current route."}
        alternatives = session.query(RouteModel).filter(
            RouteModel.origin == current.origin,
            RouteModel.destination == current.destination,
            RouteModel.id != current.id,
        ).all()
        safer = [route for route in alternatives if _RISK.get((route.risk_level or "").upper(), 99) < _RISK.get((current.risk_level or "").upper(), 99)]
        if not safer:
            return {"status": "rejected", "message": "No safer same-origin/same-destination demo route is available."}
        chosen = sorted(safer, key=lambda route: (_RISK.get((route.risk_level or "").upper(), 99), route.transit_days))[0]
        return {
            "status": "confirmed", "route_id": chosen.id,
            "reference": f"MOCK-{shipment_id}-{chosen.id}",
            "demo": True,
            "message": f"Mock carrier confirmed a demo reroute to {chosen.id} ({chosen.via_ports}). No real carrier was contacted.",
        }
    finally:
        session.close()
