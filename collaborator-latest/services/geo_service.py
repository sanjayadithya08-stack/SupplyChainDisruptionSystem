from dataclasses import dataclass
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class GeoEvent:
    country: str
    event_type: str
    severity: str
    affected_routes: list[str]
    description: str

def _get_stub_geo_events() -> list[GeoEvent]:
    return [
        GeoEvent("Taiwan", "Earthquake", "CRITICAL", ["Trans-Pacific", "Intra-Asia"], "7.2 magnitude earthquake near major port."),
        GeoEvent("Yemen", "Conflict", "CRITICAL", ["Asia-Europe"], "Escalating tensions affecting Red Sea transit."),
        GeoEvent("France", "Strike", "HIGH", ["Intra-Europe"], "National transit workers strike planned."),
        GeoEvent("Brazil", "Policy Change", "MEDIUM", ["Latin-America-US"], "New export tariffs introduced unexpectedly."),
        GeoEvent("USA", "Cyberattack", "HIGH", ["Trans-Pacific", "Trans-Atlantic"], "Major logistics provider systems down."),
        GeoEvent("Germany", "Flooding", "MEDIUM", ["Intra-Europe"], "Inland waterways partially blocked."),
        GeoEvent("China", "Congestion", "MEDIUM", ["Trans-Pacific", "Asia-Europe"], "Shanghai port wait times increased."),
        GeoEvent("India", "Infrastructure", "LOW", ["Asia-Middle East"], "Railway upgrades causing minor detours."),
        GeoEvent("South Africa", "Power Outage", "HIGH", ["Africa-Europe"], "Rolling blackouts affecting cold storage."),
        GeoEvent("UK", "Labor Shortage", "MEDIUM", ["Intra-Europe"], "HGV driver shortage causing delays.")
    ]

def fetch_geo_events() -> list[GeoEvent]:
    """
    # TO SWAP FOR REAL API (e.g. GDELT):
    # import requests
    # url = "https://api.gdeltproject.org/api/v2/doc/doc?query=supply+chain&mode=ArtList&format=json"
    """
    try:
        return _get_stub_geo_events()
    except Exception:
        return []

def get_high_risk_countries() -> list[str]:
    try:
        return list(set([e.country for e in _get_stub_geo_events() if e.severity in ["HIGH", "CRITICAL"]]))
    except Exception:
        return []

def get_affected_routes(country: str) -> list[str]:
    try:
        routes = []
        for e in _get_stub_geo_events():
            if e.country.lower() == country.lower():
                routes.extend(e.affected_routes)
        return list(set(routes))
    except Exception:
        return []
