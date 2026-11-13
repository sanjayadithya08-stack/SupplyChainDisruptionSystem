import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from utils.text_preprocessing import combine_inputs
from utils.geo_coords import get_coords, route_path, CITY_REGION
from ml import predict as text_model
from ml.prevention_engine import generate_prevention_plan
from ml.model_monitor import log_prediction, get_stats
from services.news_service import fetch_headlines
from services.weather_service import fetch_weather
from services.geo_service import fetch_geo_events
from services.supplier_service import get_all_suppliers, get_alternates, get_suppliers_by_region
from services.route_service import get_all_routes
from services.alert_service import send_alert, get_recent_alerts, send_prevention_plan

from api.schemas import (
    PredictionResponse, CombinedInput, BatchInput, HealthResponse,
    FullAnalysisResponse, PreventionPlan, AlertRequest
)
from api.middleware import AntigravityMiddleware

START_TIME = time.time()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fresh clones have no trained models and stale shipment ETAs - fix both on boot.
    try:
        from utils.bootstrap import ensure_ready
        ensure_ready()
        text_model.reload_pipeline()
    except Exception as e:
        print(f"[bootstrap] Warning: {e}")
    yield


app = FastAPI(title="Supply Chain Disruption Prediction & Prevention System",
              version="2.1.0", lifespan=lifespan)
app.add_middleware(AntigravityMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _jsonable(items):
    return [asdict(i) if is_dataclass(i) else i for i in items]


def _build_full_analysis(text: str, context: str = None, notify: bool = True) -> FullAnalysisResponse:
    pred = text_model.predict_risk(text)
    plan = generate_prevention_plan(pred)

    # Suggest alternates for suppliers located in the affected regions
    alts = []
    for region in pred.get("affected_regions", []):
        for sup in get_suppliers_by_region(region):
            alts.extend(asdict(a) for a in get_alternates(sup.id))
    if alts:
        plan["supplier_alternatives"] = list({a["id"]: a for a in alts}.values())[:5]

    log_prediction(pred, plan)

    if notify and pred.get("label") == "CRITICAL":
        send_prevention_plan(plan, Config.ALERT_RECIPIENTS)

    return FullAnalysisResponse(
        prediction=PredictionResponse(**pred),
        plan=PreventionPlan(**plan),
        context=context
    )


@app.get("/api", summary="Health check with system status")
async def api_root():
    return {"status": "online", "message": "Antigravity V2 Active", "web": "/"}


@app.get("/predict", response_model=PredictionResponse)
async def predict_text_only(text: str = Query(..., min_length=1)):
    """Predict only, no plan."""
    try:
        return text_model.predict_risk(text)
    except Exception as e:
        return PredictionResponse(label=Config.DEFAULT_RISK, confidence=0.0, disruption_type="normal",
                                  affected_regions=[], estimated_duration_days=0, error=str(e))


@app.get("/analyze", response_model=FullAnalysisResponse)
async def analyze_text(text: str = Query(..., min_length=1)):
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

        from services.shipment_service import map_country_to_region
        geo_events = fetch_geo_events()
        geo_str = " ".join(e.description for e in geo_events
                           if region == "global" or map_country_to_region(e.country) == region)

        combined_text = combine_inputs(news_str, weather_str, geo_str)
        context_str = f"Sources Used: News({len(news_items)}), Weather({weather.condition}), Geo({len(geo_events)})"
        return _build_full_analysis(combined_text, context=context_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/batch")
async def analyze_batch(payload: BatchInput):
    try:
        return {"results": [_build_full_analysis(t, notify=False) for t in payload.texts]}
    except Exception as e:
        return {"error": str(e), "results": []}


# ── Company-Specific Endpoints ─────────────────────────────────────────────────
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
    except Exception:
        return []


def _company_df():
    import pandas as pd
    return pd.read_csv(os.path.join(Config.DATA_DIR, "company_dataset.csv"))


@app.get("/company/dataset")
async def company_dataset():
    """Return raw company dataset as JSON."""
    try:
        return _company_df().to_dict(orient="records")
    except Exception:
        return []


@app.get("/company/stats")
async def company_stats():
    """Return aggregated stats from company dataset."""
    try:
        df = _company_df()
        delayed = df[df["delay_days"] > 0]["delay_days"]
        by_month = df.assign(month=df["date"].str[:7]).groupby("month")["revenue_at_risk_usd"].sum()
        return {
            "total_events": int(len(df)),
            "total_revenue_at_risk": int(df["revenue_at_risk_usd"].sum()),
            "total_units_affected": int(df["affected_units"].sum()),
            "avg_delay_days": round(float(delayed.mean()), 1) if len(delayed) else 0.0,
            "by_label": df["label"].value_counts().to_dict(),
            "by_disruption_type": df["disruption_type"].value_counts().to_dict(),
            "by_supplier": df.groupby("supplier_name")["revenue_at_risk_usd"].sum().sort_values(ascending=False).head(5).to_dict(),
            "by_region": df.groupby("region")["revenue_at_risk_usd"].sum().sort_values(ascending=False).to_dict(),
            "by_month": {k: int(v) for k, v in by_month.items()},
            "worst_events": df.nlargest(5, "revenue_at_risk_usd")[["event_id", "date", "supplier_name", "disruption_type", "revenue_at_risk_usd", "label"]].to_dict(orient="records"),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── Live Shipments & Threat Radar ──────────────────────────────────────────────
@app.get("/shipments/live")
async def get_live_shipments():
    """Return all shipments with enriched data."""
    try:
        from services.shipment_service import get_enriched_shipments
        return get_enriched_shipments()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/shipments/threats")
async def get_shipment_threats(notify: bool = Query(False, description="Dispatch plans to sender/receiver")):
    """Run the live threat engine on active shipments. Read-only unless notify=true."""
    try:
        from ml.live_threat_engine import analyze_live_shipments
        return analyze_live_shipments(notify=notify)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/shipments/threats/notify")
async def notify_shipment_threats():
    """Run the threat engine and dispatch prevention plans for HIGH/CRITICAL shipments."""
    from ml.live_threat_engine import analyze_live_shipments
    results = analyze_live_shipments(notify=True)
    return {"alerts_sent": sum(1 for r in results if r.get("alert_sent")), "scanned": len(results)}


@app.get("/network")
async def network():
    """Geo-referenced view of hubs, routes and shipments for the 3D globe."""
    try:
        from services.shipment_service import get_enriched_shipments
        routes = get_all_routes()
        hubs = {}
        for r in routes:
            for city in (r.origin, r.destination):
                c = get_coords(city)
                hubs[city] = {"name": city, "lat": c["lat"], "lon": c["lon"],
                              "region": CITY_REGION.get(city, "global")}
        geo = [{**asdict(g), **get_coords(g.country)} for g in fetch_geo_events()]
        return {
            "hubs": list(hubs.values()),
            "routes": [{**asdict(r), "path": route_path(r.origin, r.destination, r.via_ports)} for r in routes],
            "shipments": get_enriched_shipments(),
            "events": geo,
            "suppliers": [{**asdict(s), **get_coords(s.country)} for s in get_all_suppliers()],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/news")
async def get_live_news(region: str = Query("global")):
    try:
        from services.news_service import fetch_by_region
        return _jsonable(fetch_by_region(region))
    except Exception:
        return []


@app.get("/weather")
async def get_live_weather(region: str = Query("global")):
    try:
        w = fetch_weather(region)
        return {"region": region, "condition": w.condition, "severity": w.severity,
                "wind_kph": w.wind_kph, "visibility_km": w.visibility_km, "alerts": w.alerts}
    except Exception:
        return {}


@app.get("/geo")
async def get_live_geo():
    try:
        return _jsonable(fetch_geo_events())
    except Exception:
        return []


@app.get("/suppliers")
async def list_suppliers():
    try:
        return _jsonable(get_all_suppliers())
    except Exception:
        return []


@app.get("/routes")
async def list_routes():
    try:
        return _jsonable(get_all_routes())
    except Exception:
        return []


@app.get("/alerts")
async def list_alerts():
    try:
        return _jsonable(get_recent_alerts(20))
    except Exception:
        return []


@app.post("/alerts/send")
async def trigger_alert(payload: AlertRequest, background_tasks: BackgroundTasks):
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message must not be empty")
    background_tasks.add_task(send_alert, payload.level, payload.message, Config.ALERT_RECIPIENTS)
    return {"status": "Alert queued"}


@app.get("/monitor/stats")
async def monitor_stats():
    try:
        return get_stats()
    except Exception:
        return {"error": "Could not fetch stats"}


@app.get("/monitor/health", response_model=HealthResponse)
async def monitor_health():
    uptime = time.time() - START_TIME
    artefacts_status = {
        "pipeline.pkl": os.path.exists(Config.PIPELINE_PATH),
        "company_model.pkl": os.path.exists(Config.COMPANY_MODEL_PATH),
        "dataset.csv": os.path.exists(Config.DATASET_PATH),
    }
    sys_metrics = {}
    try:
        import psutil
        sys_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage(os.path.abspath(os.sep)).percent,
        }
    except Exception:
        pass  # psutil is optional; health should still report
    loaded = text_model.PIPELINE is not None
    return HealthResponse(
        status="healthy" if loaded and all(artefacts_status.values()) else "degraded",
        model_loaded=loaded, uptime_seconds=round(uptime, 2),
        artefacts=artefacts_status, system_metrics=sys_metrics,
        channels={"slack": bool(Config.SLACK_WEBHOOK_URL), "email": bool(Config.SMTP_USER),
                  "gemini": bool(Config.GEMINI_API_KEY), "news_api": bool(Config.NEWS_API_KEY),
                  "weather_api": bool(Config.WEATHER_API_KEY)},
    )


# ── 3D Web Command Center ──────────────────────────────────────────────────────
if os.path.isdir(Config.WEB_DIR):
    @app.get("/", include_in_schema=False)
    async def web_index():
        return FileResponse(os.path.join(Config.WEB_DIR, "index.html"), headers={"Cache-Control": "no-cache"})

    class _WebFiles(StaticFiles):
        # Always revalidate so a redeploy is picked up immediately (ETags keep it cheap)
        async def get_response(self, path, scope):
            resp = await super().get_response(path, scope)
            resp.headers["Cache-Control"] = "no-cache"
            return resp

    app.mount("/", _WebFiles(directory=Config.WEB_DIR), name="web")
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return await api_root()
