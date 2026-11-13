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


def _mark_eligible_shipments_delivered(today: date | None = None) -> None:
    """Close shipments past ETA unless their stored status says they are disrupted."""
    from db.models import get_session, ShipmentModel

    deadline = (today or date.today()).isoformat()
    with get_session() as s:
        rows = s.query(ShipmentModel).filter(
            ShipmentModel.estimated_arrival < deadline,
            ShipmentModel.status != "Delivered",
        ).all()
        changed = False
        for row in rows:
            status = (row.status or "").strip().lower()
            if "delay" in status or "disrupt" in status:
                continue
            row.status = "Delivered"
            changed = True
        if changed:
            s.commit()


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
    """Refresh shipment lifecycle, then return active shipments with supplier and route info."""
    _mark_eligible_shipments_delivered()
    shipments = get_all_shipments()
    suppliers = {s.id: s for s in get_all_suppliers()}
    routes = {r.id: r for r in get_all_routes()}
    from services.contact_service import get_supplier_contacts, get_receivers
    contacts_by_supplier = {}
    for contact in get_supplier_contacts():
        contacts_by_supplier.setdefault(contact.supplier_id, []).append({
            "contact_name": contact.contact_name, "email": contact.email, "phone": contact.phone or "",
            "role": contact.role or "", "alert_level": contact.alert_level, "verified": bool(contact.verified),
        })
    receivers_by_id = {receiver.id: receiver for receiver in get_receivers()}

    enriched = []
    for shp in shipments:
        if shp.status == "Delivered":
            continue
        sup = suppliers.get(shp.supplier_id)
        route = routes.get(shp.route_id)
        receiver = receivers_by_id.get(shp.receiver_id)
        dest = route.destination if route else "Unknown"
        progress = _progress(shp.estimated_arrival, route.transit_days if route else 14, shp.status)
        via_ports = route.via_ports if route else []
        if isinstance(via_ports, str):
            via_ports = via_ports.split(",")
        stops = [route.origin, *(via_ports or []), dest] if route else ["Unknown", dest]
        route_regions = {
            region for region in (
                map_country_to_region(sup.country if sup else "Unknown"),
                *(CITY_REGION.get(stop.strip()) for stop in stops),
            ) if region and region != "global"
        }
        if not route_regions:
            route_regions.add("global")
        stop_index = min(int(progress * max(len(stops) - 1, 1)), len(stops) - 1)
        tracking_status = "Delayed in transit" if "delay" in (shp.status or "").lower() else (
            "Preparing for dispatch" if shp.status == "Pending" else "In transit"
        )
        milestones = ["Booking confirmed", "Picked up by carrier", "Departed origin", "In transit", "Arrived at destination"]
        completed_milestones = max(1, min(len(milestones) - 1, int(progress * (len(milestones) - 1)) + 1))
        try:
            eta_date = datetime.strptime(shp.estimated_arrival, "%Y-%m-%d").date()
            transit_days = max(route.transit_days if route else 14, 1)
            start_date = eta_date.fromordinal(eta_date.toordinal() - transit_days)
            tracking_events = [
                {"event": milestones[i], "date": start_date.fromordinal(start_date.toordinal() + round(transit_days * i / (len(milestones) - 1))).isoformat()}
                for i in range(completed_milestones)
            ]
        except (TypeError, ValueError):
            tracking_events = [{"event": "Booking confirmed", "date": shp.estimated_arrival}]
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
            "route_regions": sorted(route_regions),
            "receiver_id": shp.receiver_id,
            "receiver": ({
                "id": receiver.id, "name": receiver.name, "city": receiver.city,
                "country": receiver.country, "tier": receiver.tier,
                "contact_email": receiver.contact_email or "", "contact_phone": receiver.contact_phone or "",
                "contact_verified": bool(receiver.contact_verified), "sla_delivery_days": receiver.sla_delivery_days,
            } if receiver else {"id": shp.receiver_id, "name": "Unknown receiver", "contact_email": "", "contact_verified": False}),
            "supplier_contacts": contacts_by_supplier.get(shp.supplier_id, []),
            "contact_data_note": "Demo supplier and receiver contacts are fictional and unverified. With demo alerts enabled, shipment alerts go only to the configured demo inbox.",
            "progress": progress,
            "tracking_reference": f"DEMO-{shp.id}",
            "tracking_source": "Demo simulation",
            "tracking_status": tracking_status,
            "current_location": stops[stop_index],
            "tracking_updated_at": datetime.now().astimezone().isoformat(timespec="minutes"),
            "tracking_events": tracking_events,
        })
    return enriched
