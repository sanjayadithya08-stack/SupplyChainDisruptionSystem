"""
Shipment Service
Handles operations related to company active shipments.
"""
import sys, os
from dataclasses import dataclass
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.supplier_service import get_all_suppliers
from services.route_service import get_all_routes

@dataclass
class Shipment:
    id: str
    sku: str
    supplier_id: str
    receiver_id: str
    route_id: str
    status: str
    estimated_arrival: str
    value_usd: float
    units: int
    risk_level: str = "LOW"

def get_all_shipments() -> list[Shipment]:
    try:
        from db.models import get_session, ShipmentModel
        with get_session() as s:
            rows = s.query(ShipmentModel).all()
            return [Shipment(
                id=r.id, sku=r.sku, supplier_id=r.supplier_id,
                receiver_id=r.receiver_id, route_id=r.route_id,
                status=r.status, estimated_arrival=r.estimated_arrival,
                value_usd=r.value_usd, units=r.units, risk_level=getattr(r, "risk_level", "LOW") or "LOW"
            ) for r in rows]
    except Exception as e:
        return [{"error": f"DB Error: {str(e)}"}]

def get_enriched_shipments() -> list[dict]:
    """Returns shipments joined with supplier and route info."""
    shipments = get_all_shipments()
    if shipments and isinstance(shipments[0], dict) and "error" in shipments[0]:
        return shipments
    suppliers = {s.id: s for s in get_all_suppliers()}
    routes = {r.id: r for r in get_all_routes()}
    
    enriched = []
    for shp in shipments:
        sup = suppliers.get(shp.supplier_id)
        route = routes.get(shp.route_id)
        enriched.append({
            "id": shp.id,
            "sku": shp.sku,
            "status": shp.status,
            "estimated_arrival": shp.estimated_arrival,
            "value_usd": shp.value_usd,
            "units": shp.units,
            "risk_level": shp.risk_level,
            "supplier_id": shp.supplier_id,
            "supplier_name": sup.name if sup else "Unknown",
            "supplier_country": sup.country if sup else "Unknown",
            # SupplierModel.risk_score represents supplier reliability (0.0 to 1.0, where higher is more reliable), matching company_dataset.csv.
            "supplier_risk_score": sup.risk_score if sup else 0.8,
            "reliability_score": round(float(sup.risk_score if sup else 0.8), 2),
            "route_id": shp.route_id,
            "origin": route.origin if route else "Unknown",
            "destination": route.destination if route else "Unknown",
            "region": _map_country_to_region(sup.country if sup else "Unknown"),
            "receiver_id": shp.receiver_id
        })
    return enriched

def _map_country_to_region(country: str) -> str:
    key = str(country or "").strip().casefold()
    cmap = {
        "taiwan": "east-asia", "china": "east-asia", "south korea": "east-asia", "japan": "east-asia",
        "north korea": "east-asia", "mongolia": "east-asia",
        "germany": "europe", "czech republic": "europe", "netherlands": "europe", "france": "europe",
        "united kingdom": "europe", "uk": "europe", "italy": "europe", "spain": "europe",
        "poland": "europe", "belgium": "europe", "switzerland": "europe", "sweden": "europe",
        "norway": "europe", "denmark": "europe", "portugal": "europe", "turkey": "europe",
        "usa": "north-america", "united states": "north-america", "canada": "north-america",
        "mexico": "latin-america", "peru": "latin-america", "brazil": "latin-america",
        "argentina": "latin-america", "chile": "latin-america", "colombia": "latin-america",
        "vietnam": "southeast-asia", "indonesia": "southeast-asia", "thailand": "southeast-asia",
        "singapore": "southeast-asia", "malaysia": "southeast-asia", "philippines": "southeast-asia",
        "india": "south-asia", "pakistan": "south-asia", "bangladesh": "south-asia", "sri lanka": "south-asia",
        "egypt": "middle-east", "yemen": "middle-east", "saudi arabia": "middle-east",
        "united arab emirates": "middle-east", "uae": "middle-east", "israel": "middle-east",
        "jordan": "middle-east", "iraq": "middle-east", "iran": "middle-east", "qatar": "middle-east",
        "australia": "oceania", "new zealand": "oceania",
    }
    return cmap.get(key, "global")
