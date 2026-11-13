import os
import sys
import time
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from utils.text_preprocessing import combine_inputs
from ml.predict import predict_risk, batch_predict, PIPELINE
from ml.prevention_engine import generate_prevention_plan
from ml.model_monitor import log_prediction, get_stats
from services.news_service import fetch_headlines
from services.weather_service import fetch_weather
from services.geo_service import fetch_geo_events
from services.supplier_service import get_all_suppliers, get_alternates
from services.route_service import get_all_routes, get_alternate_routes
from services.alert_service import send_alert, get_recent_alerts, send_prevention_plan

from api.schemas import (
    PredictionResponse, CombinedInput, BatchInput, HealthResponse,
    FullAnalysisResponse, PreventionPlan, AlertRequest, OrderRequest, AutomationRequest,
    ShipmentImportRequest, DisruptionResolutionRequest
)
from api.middleware import AntigravityMiddleware

START_TIME = time.time()

app = FastAPI(title="Supply Chain Disruption Prediction & Prevention System", version="2.0.0")
app.add_middleware(AntigravityMiddleware)

@app.on_event("startup")
async def start_disruption_monitor():
    from db.models import Base as CoreBase, engine
    from db.models_extended import Base as ExtendedBase
    CoreBase.metadata.create_all(engine)
    from db.models import ensure_shipment_risk_column
    ensure_shipment_risk_column()
    ExtendedBase.metadata.create_all(engine)
    from services.shipment_import_service import ensure_sample_shipments
    ensure_sample_shipments()
    from services.monitoring_service import start_scheduler
    start_scheduler()

@app.on_event("shutdown")
async def stop_disruption_monitor():
    from services.monitoring_service import stop_scheduler
    stop_scheduler()

def _build_full_analysis(text: str, context: str = None) -> FullAnalysisResponse:
    pred = predict_risk(text)
    plan = generate_prevention_plan(pred)
    
    # Enrich plan with alternates
    if pred.get("affected_regions"):
        region = pred["affected_regions"][0]
        # Just grab the first alternate we find for demo
        alts = get_alternates("S001")
        if alts: plan["supplier_alternatives"] = [a.__dict__ for a in alts]
        
    log_prediction(pred, plan)
    
    # Auto-alert on critical
    if pred.get("label") == "CRITICAL":
        send_prevention_plan(plan, Config.ALERT_RECIPIENTS)
        
    return FullAnalysisResponse(
        prediction=PredictionResponse(**pred),
        plan=PreventionPlan(**plan),
        context=context
    )

@app.get("/", summary="Health check with system status")
async def root():
    return {"status": "online", "message": "Antigravity V2 Active"}

@app.get("/predict", response_model=PredictionResponse)
async def predict_text_only(text: str = Query(...)):
    """Predict only, no plan."""
    try:
        return predict_risk(text)
    except Exception as e:
        return PredictionResponse(label=Config.DEFAULT_RISK, confidence=0.0, disruption_type="normal", affected_regions=[], estimated_duration_days=0, error=str(e))

@app.get("/analyze", response_model=FullAnalysisResponse)
async def analyze_text(text: str = Query(...)):
    """Predict + full prevention plan."""
    try:
        return _build_full_analysis(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/combined", response_model=FullAnalysisResponse)
async def analyze_combined(payload: CombinedInput):
    try:
        combined_text = combine_inputs(payload.news, payload.weather, payload.geo)
        return _build_full_analysis(combined_text, context="Combined Signals")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze/live", response_model=FullAnalysisResponse)
async def analyze_live(region: str = Query(...)):
    try:
        news_items = fetch_headlines(query=region, max_results=5)
        news_str = ". ".join([n.headline for n in news_items])
        
        weather = fetch_weather(region)
        weather_str = f"{weather.condition}, Severity: {weather.severity}"
        
        geo_events = fetch_geo_events()
        geo_str = " ".join([e.description for e in geo_events if e.country.lower() in region.lower() or region == "global"])
            
        combined_text = combine_inputs(news_str, weather_str, geo_str)
        context_str = f"Sources Used: News({len(news_items)}), Weather({weather.condition}), Geo({len(geo_events)})"
        
        return _build_full_analysis(combined_text, context=context_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/batch")
async def analyze_batch(payload: BatchInput):
    try:
        results = []
        for text in payload.texts:
            results.append(_build_full_analysis(text))
        return {"results": results}
    except Exception as e:
        return {"error": str(e), "results": []}

# â”€â”€ Company-Specific Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.post("/company/predict")
async def company_predict_event(event: dict):
    """Predict disruption for a structured company supply chain event."""
    try:
        from ml.company_predict import predict_event
        return predict_event(event)
    except Exception as e:
        return {"label": "UNKNOWN", "error": str(e)}

@app.get("/company/history")
async def company_history():
    """Return all historical events with model predictions."""
    try:
        from ml.company_predict import predict_all_historical
        return predict_all_historical()
    except Exception as e:
        return []

@app.get("/company/dataset")
async def company_dataset():
    """Return raw company dataset as JSON."""
    try:
        import pandas as pd
        from utils.config import Config
        df = pd.read_csv(Config.DATA_DIR + "/company_dataset.csv")
        return df.to_dict(orient="records")
    except Exception as e:
        return []

@app.get("/company/stats")
async def company_stats():
    """Return aggregated stats from company dataset."""
    try:
        import pandas as pd
        from utils.config import Config
        df = pd.read_csv(Config.DATA_DIR + "/company_dataset.csv")
        total_rev = int(df["revenue_at_risk_usd"].sum())
        return {
            "total_events": int(len(df)),
            "total_revenue_at_risk": total_rev,
            "total_revenue_at_risk_usd": total_rev,
            "total_units_affected": int(df["affected_units"].sum()),
            "avg_delay_days": round(float(df[df["delay_days"] > 0]["delay_days"].mean()), 1),
            "by_label": df["label"].value_counts().to_dict(),
            "by_disruption_type": df["disruption_type"].value_counts().to_dict(),
            "by_supplier": df.groupby("supplier_name")["revenue_at_risk_usd"].sum().sort_values(ascending=False).head(5).to_dict(),
            "by_region": df.groupby("region")["revenue_at_risk_usd"].sum().sort_values(ascending=False).to_dict(),
            "worst_events": df.nlargest(5, "revenue_at_risk_usd")[["event_id","date","supplier_name","disruption_type","revenue_at_risk_usd","label"]].to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e)}

# â”€â”€ Live Shipments & Threat Radar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/shipments/live")
async def get_live_shipments():
    """Return saved company shipment records enriched from the local ledger."""
    try:
        from services.shipment_service import get_enriched_shipments
        return get_enriched_shipments()
    except Exception as e:
        return {"error": str(e)}

@app.post("/shipments/import")
async def import_company_shipments(payload: ShipmentImportRequest):
    """Import a company CSV converted to JSON rows; replace the demo ledger by default."""
    from services.shipment_import_service import import_shipments
    try:
        return import_shipments(payload.shipments, replace_existing=payload.replace_existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/shipments/threats")
async def get_shipment_threats():
    """Run a live scan and persist newly detected high-impact disruptions."""
    try:
        from services.monitoring_service import run_scan
        return run_scan(actor="operator")["results"]
    except Exception as e:
        return {"error": str(e)}

@app.get("/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    """Return one enriched shipment, or a clear 404 for an invalid id."""
    from services.shipment_service import get_enriched_shipments
    shipment = next((s for s in get_enriched_shipments() if s.get("id") == shipment_id), None)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment

# Trigger reload

@app.get("/news")
async def get_live_news(region: str = Query("global")):
    try:
        from services.news_service import fetch_by_region
        return fetch_by_region(region)
    except Exception as e:
        return []

@app.get("/news/status")
async def get_news_status():
    """Expose whether the current headlines are live, sample, or unavailable."""
    from services.news_service import get_feed_status
    return get_feed_status()

@app.get("/news/feed")
async def get_news_feed(region: str = Query("global")):
    """Return headlines and the exact live/sample status for this feed request."""
    try:
        from dataclasses import asdict
        from services.news_service import fetch_by_region_with_status
        articles, status = fetch_by_region_with_status(region)
        return {"articles": [asdict(article) for article in articles], "status": status}
    except Exception:
        return {"articles": [], "status": {"provider": "NewsAPI.org", "mode": "unavailable", "configured": bool(Config.NEWS_API_KEY), "message": "Could not load the intelligence feed."}}

@app.get("/weather")
async def get_live_weather(region: str = Query("global")):
    try:
        from services.weather_service import fetch_weather
        w = fetch_weather(region)
        return {"region": region, "condition": w.condition, "severity": w.severity, "alerts": w.alerts}
    except Exception as e:
        return {}

@app.get("/geo")
async def get_live_geo():
    try:
        from services.geo_service import fetch_geo_events
        return fetch_geo_events()
    except Exception as e:
        return []

@app.get("/suppliers")
async def list_suppliers():
    try:
        return get_all_suppliers()
    except Exception as e:
        return []

@app.get("/routes")
async def list_routes():
    try:
        return get_all_routes()
    except Exception as e:
        return []

@app.get("/alerts")
async def list_alerts():
    try:
        return get_recent_alerts(20)
    except Exception as e:
        return []

# â”€â”€ Operations: inventory, orders and mitigation automation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/inventory")
async def list_inventory():
    from services.inventory_service import get_inventory, check_low_stock
    low_stock = set(check_low_stock())
    return [{**item.__dict__, "low_stock": item.sku in low_stock} for item in get_inventory()]

@app.get("/orders")
async def list_pending_orders():
    from services.inventory_service import get_pending_orders
    return [order.__dict__ for order in get_pending_orders()]

@app.post("/orders", status_code=201)
async def create_order(payload: OrderRequest):
    from services.inventory_service import get_inventory_by_sku, place_order
    inventory = get_inventory_by_sku(payload.sku)
    if not inventory:
        raise HTTPException(status_code=404, detail="SKU is not configured in inventory")
    if inventory.supplier_id != payload.supplier_id:
        raise HTTPException(status_code=422, detail="Supplier does not match the SKU's inventory record")
    order = place_order(payload.supplier_id, payload.sku, payload.quantity, payload.unit_price,
                        payload.reason, payload.shipment_id)
    if not order:
        raise HTTPException(status_code=500, detail="Could not create purchase order")
    return order

@app.get("/contacts/suppliers/{supplier_id}")
async def list_supplier_contacts(supplier_id: str):
    from services.contact_service import get_supplier_contacts
    return [contact.__dict__ for contact in get_supplier_contacts(supplier_id)]

@app.get("/automation/status")
async def automation_status():
    from services.automation_service import get_automation_status
    return get_automation_status()

@app.get("/activity")
async def recent_activity(limit: int = Query(25, ge=1, le=100)):
    """Persistent activity timeline for actions taken in the application."""
    from services.action_service import get_recent_actions
    return [action.__dict__ for action in get_recent_actions(limit)]

@app.get("/disruptions")
async def list_disruptions(status: Optional[str] = Query(None), limit: int = Query(100, ge=1, le=200)):
    from services.monitoring_service import get_disruptions
    if status and status not in {"open", "mitigated", "archived"}:
        raise HTTPException(status_code=422, detail="status must be open, mitigated, or archived")
    return get_disruptions(status=status, limit=limit)

@app.post("/disruptions/scan")
async def scan_disruptions():
    """Manually run the same scan used by the scheduled monitor."""
    from services.monitoring_service import run_scan
    summary = run_scan(actor="operator")
    return {key: summary[key] for key in ("scanned_shipments", "new_events", "refreshed_events")}

@app.post("/disruptions/{event_id}/resolve")
async def record_disruption_resolution(event_id: str, payload: DisruptionResolutionRequest):
    """Record the operator's actual response and close a reviewed risk."""
    from services.monitoring_service import get_disruptions, mark_mitigated
    event = next((item for item in get_disruptions(status="open", limit=200) if item["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Open disruption event not found")
    resolved = mark_mitigated(event_id, actor="operator", resolution=payload.action_taken)
    return {"event": resolved, "action_taken": payload.action_taken}

@app.post("/disruptions/{event_id}/mitigate")
async def mitigate_detected_disruption(event_id: str):
    from services.monitoring_service import get_disruptions, mark_mitigated
    from services.shipment_service import get_enriched_shipments
    from services.automation_service import auto_handle_disruption
    event = next((item for item in get_disruptions(limit=200) if item["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Disruption event not found")
    if event["status"] == "mitigated":
        return event
    shipment = next((item for item in get_enriched_shipments() if item["id"] == event["shipment_id"]), None)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment for disruption event not found")
    response = auto_handle_disruption(
        shipment_id=shipment["id"], disruption_type=event["disruption_type"], risk_level=event["risk_level"],
        supplier_id=shipment["supplier_id"], affected_sku=shipment["sku"],
    )
    if response.get("status") != "automated_response_executed":
        raise HTTPException(status_code=500, detail=response.get("error", "Mitigation failed"))
    return {"event": mark_mitigated(event_id), "mitigation": response}

@app.post("/automation/mitigate")
async def mitigate_shipment(payload: AutomationRequest):
    from services.shipment_service import get_enriched_shipments
    from services.automation_service import auto_handle_disruption
    shipment = next((s for s in get_enriched_shipments() if s.get("id") == payload.shipment_id), None)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if payload.risk_level.upper() not in Config.RISK_LEVELS:
        raise HTTPException(status_code=422, detail="risk_level must be LOW, MEDIUM, HIGH, or CRITICAL")
    return auto_handle_disruption(
        shipment_id=shipment["id"], disruption_type=payload.disruption_type,
        risk_level=payload.risk_level.upper(), supplier_id=shipment["supplier_id"],
        affected_sku=shipment["sku"]
    )

@app.post("/alerts/send")
async def trigger_alert(payload: AlertRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(send_alert, payload.level, payload.message, Config.ALERT_RECIPIENTS)
        return {"status": "Alert queued"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/monitor/stats")
async def monitor_stats():
    try:
        return get_stats()
    except Exception as e:
        return {"error": "Could not fetch stats"}

@app.get("/monitor/health", response_model=HealthResponse)
async def monitor_health():
    try:
        import psutil
        uptime = time.time() - START_TIME
        artefacts_status = {
            "model.pkl": os.path.exists(Config.MODEL_PATH),
            "pipeline.pkl": os.path.exists(Config.PIPELINE_PATH),
            "company_model.pkl": os.path.exists(os.path.join(Config.ARTEFACTS_DIR, "company_model.pkl")),
            "database": os.path.exists(os.path.join(Config.DATA_DIR, "supplychain.db"))
        }
        
        sys_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('C:\\\\' if os.name == 'nt' else '/').percent
        }
        
        status = "healthy" if PIPELINE is not None else "degraded"
        return HealthResponse(
            status=status, model_loaded=PIPELINE is not None,
            uptime_seconds=round(uptime, 2), artefacts=artefacts_status,
            system_metrics=sys_metrics
        )
    except Exception as e:
        return HealthResponse(status="error", model_loaded=False, uptime_seconds=0.0, artefacts={})
