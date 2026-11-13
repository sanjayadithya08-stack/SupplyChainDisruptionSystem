"""
Live Threat Engine
Cross-references live external events (news, weather, geo) with ACTIVE shipments
and uses the company-specific ML model to predict true impact on the business.
"""
import sys, os, time
from datetime import date
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.shipment_service import get_enriched_shipments, map_country_to_region
from services.news_service import fetch_headlines
from services.weather_service import fetch_weather
from services.geo_service import fetch_geo_events
from ml.company_predict import predict_event

KNOWN_TYPES = {"port_strike", "weather", "war", "cyber", "logistics", "supplier", "customs"}
SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

# Maps free-form geo/news categories onto the model's disruption vocabulary
_TYPE_ALIASES = {
    "strike": "port_strike", "labor shortage": "logistics", "conflict": "war",
    "geopolitical": "war", "cyberattack": "cyber", "earthquake": "weather",
    "flooding": "weather", "congestion": "logistics", "power outage": "logistics",
    "infrastructure": "logistics", "policy change": "customs",
}

SKU_PRODUCT_LINE = {
    "MC": "Semiconductors", "CT": "Consumer Tech", "AP": "Auto Parts", "FB": "Fabrics",
    "PL": "Plastics", "CH": "Chemicals", "RM": "Raw Materials", "PH": "Pharmaceuticals",
}

_SCAN_CACHE = {"ts": 0.0, "data": None}
SCAN_CACHE_TTL = 60  # seconds


def _normalise_type(t: str) -> str:
    t = (t or "").lower()
    if t in KNOWN_TYPES:
        return t
    return _TYPE_ALIASES.get(t, "logistics")


def _expected_delay(dtype: str, eff_rank: int) -> float:
    """Type-specific delay (route_service playbook), stretched for CRITICAL signals."""
    from services.route_service import estimate_delay
    base = estimate_delay("", dtype) or 3
    return float(round(base * (1.6 if eff_rank >= SEVERITY_RANK["CRITICAL"] else 1.0)))


def _product_line(sku: str) -> str:
    try:
        return SKU_PRODUCT_LINE.get(sku.split("-")[1][:2], "Unknown")
    except Exception:
        return "Unknown"


def _extract_threats():
    """Fetch live signals from all services."""
    threats = []

    for n in fetch_headlines("", max_results=20):
        if n.severity_hint in ("HIGH", "CRITICAL"):
            threats.append({"source": "News", "region": n.region, "type": _normalise_type(n.category),
                            "desc": n.headline, "severity": n.severity_hint})

    regions = ["us-west-coast", "us-east-coast", "north-america", "latin-america", "europe",
               "middle-east", "south-asia", "southeast-asia", "east-asia", "oceania"]
    for r in regions:
        w = fetch_weather(r)
        if w.severity in ("HIGH", "CRITICAL"):
            threats.append({"source": "Weather", "region": r, "type": "weather",
                            "desc": f"{w.condition} in {r}", "severity": w.severity})

    for g in fetch_geo_events():
        if g.severity in ("HIGH", "CRITICAL"):
            threats.append({"source": "Geopolitical", "region": map_country_to_region(g.country),
                            "type": _normalise_type(g.event_type),
                            "desc": f"{g.country}: {g.description}", "severity": g.severity})
    return threats


def _threat_matches(threat: dict, shp: dict) -> bool:
    return threat["region"] in (shp["region"], shp.get("dest_region"), "global")


def analyze_live_shipments(notify: bool = False, use_cache: bool = True):
    """
    1. Gets all active shipments.
    2. Gets all live external threats.
    3. Finds overlaps (by origin/destination region).
    4. Runs the ML model to predict actual risk.
    5. Optionally (notify=True) dispatches prevention plans to sender + receiver.
    """
    if use_cache and not notify and _SCAN_CACHE["data"] is not None \
            and time.time() - _SCAN_CACHE["ts"] < SCAN_CACHE_TTL:
        return _SCAN_CACHE["data"]

    shipments = get_enriched_shipments()
    threats = _extract_threats()
    today = date.today().isoformat()
    results = []

    for shp in shipments:
        if shp.get("status") == "Delivered":
            continue

        matched = [t for t in threats if _threat_matches(t, shp)]
        if not matched:
            results.append({"shipment": shp, "threats": [], "plan": None, "alert_sent": False,
                            "prediction": {"label": "LOW", "confidence": 1.0, "disruption_type": "normal"}})
            continue

        # Regional signals drive the prediction; worldwide ("global") signals are diffuse,
        # so they only count one severity level lower than a regional hit.
        def weight(t):
            rank = SEVERITY_RANK.get(t["severity"], 0)
            return rank - 1 if t["region"] == "global" else rank
        worst = max(matched, key=weight)
        eff = weight(worst)
        if eff < SEVERITY_RANK["HIGH"]:
            results.append({"shipment": shp, "threats": matched, "plan": None, "alert_sent": False,
                            "prediction": {"label": "MEDIUM" if eff == 1 else "LOW", "confidence": 0.6,
                                           "disruption_type": worst["type"]}})
            continue
        event_payload = {
            "supplier_country": shp["supplier_country"],
            "product_line": _product_line(shp["sku"]),
            "disruption_type": worst["type"],
            "region": shp["region"],
            "route_id": shp["route_id"],
            "supplier_reliability_score": shp["reliability_score"],
            "affected_units": shp["units"],
            "delay_days": _expected_delay(worst["type"], eff),
            "revenue_at_risk_usd": shp["value_usd"],
            "date": today,
            "supplier_name": shp["supplier_name"],
        }
        prediction = predict_event(event_payload)

        plan, alert_sent = None, False
        if prediction["label"] in ("HIGH", "CRITICAL"):
            from ml.prevention_engine import generate_prevention_plan
            plan = generate_prevention_plan({
                "label": prediction["label"],
                "disruption_type": event_payload["disruption_type"],
                "affected_regions": [shp["region"]],
                "estimated_duration_days": event_payload["delay_days"],
            }, allow_llm=notify)
            plan["target_shipment"] = shp["id"]
            if notify:
                from services.alert_service import send_prevention_plan
                recipients = [f"{shp['supplier_id']}@supplier.example.com",
                              f"{shp['receiver_id']}@company.example.com"]
                alert_sent = send_prevention_plan(plan, recipients)

        results.append({"shipment": shp, "threats": matched, "prediction": prediction,
                        "plan": plan, "alert_sent": alert_sent})

    if not notify:
        _SCAN_CACHE.update(ts=time.time(), data=results)
    return results
