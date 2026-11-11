"""
Upgrade 3: DB-backed Route Service.
Falls back to hardcoded list if DB is unavailable.
"""
from dataclasses import dataclass
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class Route:
    id: str
    origin: str
    destination: str
    via_ports: list
    carrier: str
    transit_days: int
    risk_level: str

def _from_db() -> list[Route]:
    try:
        from db.models import get_session, RouteModel
        with get_session() as s:
            rows = s.query(RouteModel).all()
            return [Route(
                id=r.id, origin=r.origin, destination=r.destination,
                via_ports=r.via_ports.split(","),
                carrier=r.carrier, transit_days=r.transit_days, risk_level=r.risk_level
            ) for r in rows]
    except Exception as e:
        print(f"[RouteService] DB unavailable, using stub: {e}")
        return []

_FALLBACK = [
    Route("R1","Shanghai","Los Angeles",["Trans-Pacific"],"Maersk",14,"MEDIUM"),
    Route("R2","Shenzhen","Seattle",["Trans-Pacific"],"MSC",16,"LOW"),
    Route("R3","Rotterdam","New York",["Trans-Atlantic"],"Hapag-Lloyd",10,"LOW"),
    Route("R4","Mumbai","Rotterdam",["Suez Canal","Red Sea"],"CMA CGM",22,"CRITICAL"),
    Route("R5","Mumbai","Rotterdam",["Cape of Good Hope"],"CMA CGM",35,"MEDIUM"),
    Route("R6","Tokyo","Los Angeles",["Trans-Pacific"],"ONE",12,"LOW"),
    Route("R7","Singapore","Hamburg",["Suez Canal"],"Evergreen",26,"HIGH"),
    Route("R8","Veracruz","Houston",["Gulf of Mexico"],"ZIM",4,"LOW"),
]

def get_all_routes() -> list[Route]:
    db = _from_db()
    return db if db else _FALLBACK

def get_alternate_routes(origin: str, destination: str) -> list[Route]:
    all_r = get_all_routes()
    primary = [r for r in all_r if r.origin == origin and r.destination == destination]
    if not primary:
        return []
    return [r for r in all_r if r.destination == destination and r.id != primary[0].id]

def estimate_delay(route_id: str, disruption_type: str) -> int:
    delay = {"port_strike": 7, "weather": 4, "war": 14, "cyber": 2, "logistics": 3, "customs": 5}
    return delay.get(disruption_type, 0)
