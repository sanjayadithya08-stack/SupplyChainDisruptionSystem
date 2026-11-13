"""
Shipment Service
Handles operations related to company active shipments.
"""
import sys, os
from dataclasses import dataclass
from datetime import date, datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.supplier_service import get_all_suppliers
from services.route_service import get_all_routes
from utils.geo_coords import CITY_REGION

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

_COUNTRY_REGION = {
    "Taiwan": "east-asia", "China": "east-asia", "South Korea": "east-asia", "Japan": "east-asia",
    "Germany": "europe", "Czech Republic": "europe", "Netherlands": "europe", "France": "europe",
    "UK": "europe", "United Kingdom": "europe",
    "USA": "north-america", "United States": "north-america", "Canada": "north-america",
    "Mexico": "latin-america", "Peru": "latin-america", "Brazil": "latin-america",
    "Vietnam": "southeast-asia", "Indonesia": "southeast-asia", "Thailand": "southeast-asia",
    "Singapore": "southeast-asia", "India": "south-asia",
    "Egypt": "middle-east", "Yemen": "middle-east", "Tunisia": "middle-east",
    "Australia": "oceania", "South Africa": "global",
}

def map_country_to_region(country: str) -> str:
    return _COUNTRY_REGION.get(country, "global")

# Kept for backwards compatibility with older imports
_map_country_to_region = map_country_to_region


def get_all_shipments() -> list[Shipment]:
    from db.models import get_session, ShipmentModel
    with get_session() as s:
        rows = s.query(ShipmentModel).all()
        return [Shipment(
            id=r.id, sku=r.sku, supplier_id=r.supplier_id,
            receiver_id=r.receiver_id, route_id=r.route_id,
            status=r.status, estimated_arrival=r.estimated_arrival,
            value_usd=r.value_usd, units=r.units
        ) for r in rows]


def _progress(eta: str, transit_days: int, status: str) -> float:
    """Fraction of the voyage completed (0..1), derived from ETA and route transit time."""
    if status == "Pending":
        return 0.0
    try:
        days_left = (datetime.strptime(eta, "%Y-%m-%d").date() - date.today()).days
        frac = 1 - days_left / max(transit_days, 1)
        return round(min(max(frac, 0.05), 0.95), 3)
    except Exception:
        return 0.5


def get_enriched_shipments() -> list[dict]:
    """Returns shipments joined with supplier and route info."""
    shipments = get_all_shipments()
    suppliers = {s.id: s for s in get_all_suppliers()}
    routes = {r.id: r for r in get_all_routes()}

    enriched = []
    for shp in shipments:
        sup = suppliers.get(shp.supplier_id)
        route = routes.get(shp.route_id)
        dest = route.destination if route else "Unknown"
        enriched.append({
            "id": shp.id,
            "sku": shp.sku,
            "status": shp.status,
            "estimated_arrival": shp.estimated_arrival,
            "value_usd": shp.value_usd,
            "units": shp.units,
            "supplier_id": shp.supplier_id,
            "supplier_name": sup.name if sup else "Unknown",
            "supplier_country": sup.country if sup else "Unknown",
            # NB: the DB column is named risk_score but holds a reliability value (higher = better)
            "reliability_score": sup.risk_score if sup else 0.5,
            "route_id": shp.route_id,
            "carrier": route.carrier if route else "Unknown",
            "origin": route.origin if route else "Unknown",
            "destination": dest,
            "region": map_country_to_region(sup.country if sup else "Unknown"),
            "dest_region": CITY_REGION.get(dest, "global"),
            "receiver_id": shp.receiver_id,
            "progress": _progress(shp.estimated_arrival, route.transit_days if route else 14, shp.status),
        })
    return enriched
