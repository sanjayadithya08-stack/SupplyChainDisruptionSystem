"""
Live Threat Engine
Cross-references live external events (news, weather, geo) with ACTIVE shipments
and uses the company-specific ML model to predict true impact on the business.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.shipment_service import get_enriched_shipments, _map_country_to_region
from services.news_service import fetch_headlines, get_feed_status
from services.weather_service import fetch_weather
from ml.company_predict import predict_event
from datetime import date
from utils.config import Config

def _extract_threats():
    """Fetch live signals from all services."""
    threats = []
    
    # News
    news = fetch_headlines("supply chain disruption", max_results=20)
    feed_is_live = get_feed_status().get("mode") == "live"
    for n in news:
        if feed_is_live and n.severity_hint in ["HIGH", "CRITICAL"]:
            threats.append({
                "source": "News", "region": n.region, "type": n.category,
                "desc": n.headline, "severity": n.severity_hint,
                "global_impact": (
                    n.region == "global" and n.severity_hint == "CRITICAL"
                    and (n.category == "cyber" or "global shipping" in n.headline.casefold()
                         or "global supply chain" in n.headline.casefold())
                )
            })
            
    # Weather
    regions = ["us-west-coast", "us-east-coast", "north-america", "latin-america", 
               "europe", "middle-east", "south-asia", "southeast-asia", "east-asia", "global"]
    # Use weather as a threat signal only when an external weather key is set.
    # The local fallback weather fixtures describe sample scenarios, not current
    # conditions, so they must not create live disruption cases on every scan.
    if Config.WEATHER_API_KEY:
        for r in regions:
            w = fetch_weather(r)
            if w.severity in ["HIGH", "CRITICAL"]:
                threats.append({
                    "source": "Weather", "region": r, "type": "weather",
                    "desc": f"{w.condition} in {r}", "severity": w.severity,
                    "global_impact": False,
                })
            
    return threats

def analyze_live_shipments():
    """
    1. Gets all active shipments.
    2. Gets all live external threats.
    3. Finds overlaps (by region).
    4. Runs the ML model to predict actual risk.
    """
    shipments = get_enriched_shipments()
    threats = _extract_threats()
    
    results = []
    
    for shp in shipments:
        if shp["status"] == "Delivered":
            continue
            
        # Find relevant threats (match by region or global)
        matched_threats = [
            t for t in threats
            if t["region"] == shp["region"] or (t["region"] == "global" and t.get("global_impact", False))
        ]
        
        if not matched_threats:
            results.append({
                "shipment": shp,
                "threats": [],
                "prediction": {"label": "LOW", "confidence": 1.0, "disruption_type": "normal"},
                "plan": None
            })
            continue
            
        # Take worst threat for simulation
        worst_threat = max(matched_threats, key=lambda x: 1 if x["severity"]=="HIGH" else 2)
        
        # Build event payload for ML model
        event_payload = {
            "supplier_country": shp["supplier_country"],
            "product_line": "Unknown", # Could map from sku
            "disruption_type": worst_threat["type"] if worst_threat["type"] in ["port_strike","weather","war","cyber","logistics","supplier","customs"] else "logistics",
            "region": shp["region"],
            "route_id": shp["route_id"],
            "supplier_reliability_score": shp["reliability_score"],
            "affected_units": shp["units"],
            "delay_days": 7.0 if worst_threat["severity"] == "HIGH" else 14.0,
            "revenue_at_risk_usd": shp["value_usd"],
            "date": date.today().isoformat(),
            "supplier_name": shp["supplier_name"]
        }
        
        prediction = predict_event(event_payload)
        
        # Generate prevention plan if risk is elevated
        plan = None
        alert_sent = False
        if prediction["label"] in ["HIGH", "CRITICAL"]:
            from ml.prevention_engine import generate_prevention_plan
            plan = generate_prevention_plan({
                "label": prediction["label"],
                "disruption_type": event_payload["disruption_type"],
                "affected_regions": [shp["region"]],
                "estimated_duration_days": event_payload["delay_days"]
            })
            
            # Alerting is opt-in because a scan can contain many matches. The
            # Operations tab provides an explicit, audited mitigation action.
            if Config.AUTO_MITIGATION_ENABLED:
                from services.alert_service import send_prevention_plan
                recipients = [
                    f"{shp['supplier_id']}@supplier.example.com",
                    f"{shp['receiver_id']}@company.example.com"
                ]
                plan["target_shipment"] = shp["id"]
                alert_sent = send_prevention_plan(plan, recipients)
            
        results.append({
            "shipment": shp,
            "threats": matched_threats,
            "prediction": prediction,
            "plan": plan,
            "alert_sent": alert_sent
        })
        
    return results
