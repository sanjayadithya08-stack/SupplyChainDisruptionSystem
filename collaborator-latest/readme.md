<div align="center">
  <h1>🚢 TechCore: Enterprise Supply Chain Intelligence</h1>
  <p><i>A production-grade, autonomous platform for tracking active shipments, predicting disruptions, and executing automated mitigation plans.</i></p>
  
  ![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
  ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
  ![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.3+-orange.svg)
  ![SQLite](https://img.shields.io/badge/SQLite-3.0+-blue.svg)
</div>

---

## 🌟 Overview

**TechCore SupplyChain AI** is a shipment-centric intelligence platform designed to move logistics from reactive to proactive. Unlike generic news trackers, this system centers strictly on your company's operational data—tracking every active shipment, correlating global events (weather, strikes, geopolitical) to specific transit routes, and autonomously notifying stakeholders when revenue is at risk.

---

## 🌐 New: TechCore Orbit — 3D Command Center

The API now serves a WebGL command center at **`http://localhost:8000/`**:

- **Interactive 3D globe** — dotted landmasses, all 15 trade lanes drawn as animated arcs coloured by risk (bending through Suez / the Cape where they actually route), every shipment moving along its lane at its real voyage progress, and pulsing geopolitical hotspots. Hover for details, click to inspect, drag to orbit.
- **Shipments** — searchable, sortable ledger; click a row to fly the camera to that cargo.
- **Threat Radar** — one-click scan that recolours the globe by predicted risk and shows each shipment's signals and prevention plan. Alerts are only dispatched when you press *Dispatch alerts*.
- **Analytics** — an orbitable 3D bar chart of revenue at risk by region, disruption mix, monthly trend and model accuracy.
- **Intelligence** — AI disruption analyzer for any headline plus the live news feed.
- **System** — CPU / memory / disk gauges, model artefacts, channel status, alert log and broadcast form.

The original Streamlit console still runs on port 8501.

---

## 🚀 Key Features

- **📦 Live Shipment Ledger**: Real-time tracking of active cargo, SKU-level value in transit, and dynamic ETA monitoring.
- **📡 AI Threat Radar**: An automated engine that cross-references live news, weather, and geo-signals against active shipment routes to predict disruptions using a Gradient Boosting ML model.
- **📧 Autonomous Mitigation**: Automatically dispatches prevention plans and risk alerts to the **Sender (Supplier)** and **Receiver** via Email/Slack when critical threats are detected.
- **📰 Live Intelligence Feed**: A curated, real-time disruption feed with direct links to original sources and AI-assigned severity levels.
- **🩺 System Monitor**: Real-time health dashboard tracking API status, model load state, and server resource utilization (CPU, RAM, Disk).
- **📈 Company Analytics**: Historical analysis of supplier reliability, revenue-at-risk trends, and disruption frequency.

---

## 📂 Project Structure

```text
C:\SupplyChain\
├── api/
│   ├── main.py                   <- FastAPI Endpoints (Shipments, Threats, News)
│   ├── schemas.py                <- Pydantic Models for system communication
├── db/
│   ├── models.py                 <- SQLAlchemy Models (Shipments, Suppliers, Routes)
├── data/
│   └── supplychain.db            <- SQLite Production Database
├── ml/
│   ├── live_threat_engine.py     <- Core Correlation Engine (Threats + Shipments)
│   ├── company_predict.py        <- ML Inference (Gradient Boosting)
│   ├── prevention_engine.py      <- Action plan generator
│   └── train_model.py            <- Training pipeline for TechCore data
├── services/
│   ├── shipment_service.py       <- Active shipment management
│   ├── alert_service.py          <- Automated dispatch (Email/Slack/Log)
│   ├── news_service.py           <- Live Global Intelligence API
│   ├── weather_service.py        <- Real-time Weather monitoring
│   └── geo_service.py            <- Geopolitical event tracking
├── web/                          <- 3D command center (Three.js, served at /)
│   ├── index.html · styles.css · app.js
│   ├── globe.js                  <- WebGL globe, arcs, shipments, events
│   └── bars3d.js                 <- 3D analytics chart
├── ui/
│   ├── app.py                    <- Streamlit 6-Tab Console
│   └── components.py             <- Modern CSS & UI Component Library
├── utils/
│   └── config.py                 <- Master Configuration & Environment
└── logs/                         <- Automated Alert & Audit Trails
```

---

## 🛠️ Setup & Execution

### 1. Installation
Use **Python 3.10 – 3.12** (the pinned pandas / scikit-learn wheels are not available for 3.13+).
```bash
python -m venv venv
venv\Scriptsctivate          # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```
> **Windows tip:** keep the project in a short path such as `C:\SupplyChain`. Very long paths exceed Windows' 260-character limit and scikit-learn fails to install correctly.

### 2. Configuration
Ensure your `.env` file contains the necessary keys for full functionality:
- `NEWS_API_KEY`: For live intelligence feed.
- `GEMINI_API_KEY`: For AI-generated executive summaries.
- `SLACK_WEBHOOK_URL`: For automated team notifications.

### 3. Launching the Platform
Start both the backend intelligence engine and the frontend command centers:
```bash
python run.py all
```
- 3D command center: `http://localhost:8000/`
- Streamlit console: `http://localhost:8501/`
- API docs: `http://localhost:8000/docs`

On first launch the API trains any missing ML models (~30 s) and reseeds the database if the sample shipments' ETAs are in the past. You can also do this by hand:
```bash
python run.py train   # text risk model + company event model
python run.py seed    # fresh shipments relative to today
python run.py check   # verify artefacts and API health
```

---

## 🩹 Fixes in v2.1

| Problem | Fix |
|---|---|
| Model files are gitignored and `run.py train` never trained the company model, so every threat prediction was `UNKNOWN` | `train` now trains both models; the API trains anything missing on startup |
| `psutil` missing from requirements → `/monitor/health` always errored | Added; health also degrades gracefully without it |
| Stub news filter matched the whole query string (e.g. "supply chain disruption") against headlines → threat engine received zero news signals | Token/region matching, falling back to the full feed |
| Geopolitical events were all tagged `global`, so every event hit every shipment | Events mapped to the region of their country; shipments match on origin *or* destination region |
| 60 req/min rate limit was tripped by the Streamlit UI itself (~10 calls per refresh) | Loopback exempt, limit configurable (`RATE_LIMIT_PER_MINUTE`, default 300) |
| `GET /shipments/threats` emailed every risky shipment's contacts on every scan | Read-only by default and cached for 60 s; dispatch via `POST /shipments/threats/notify` |
| Seeded shipment ETAs were all in the past | Auto-reseed when stale, deterministic seed, `run.py seed` |
| Japan / Netherlands suppliers had no region | Added to the region map |
| `gemini-1.5-flash` is retired | Model configurable via `GEMINI_MODEL` (default `gemini-2.5-flash`); malformed LLM plans fall back to rules |
| `.env.example` placeholder values were treated as real keys | Placeholders are ignored |
| `/analyze` always suggested alternates for supplier S001 | Alternates come from suppliers in the affected regions |
| Streamlit System tab shadowed the `sys` module; threat tab crashed on API errors | Fixed |
| No CORS | Enabled for the API |

---

## 🧠 Intelligence Workflow

1. **Ingest**: The system monitors the internal SQLite database for all shipments marked "In Transit".
2. **Scan**: It polls live global APIs for news, weather, and geopolitical events.
3. **Correlate**: The **Live Threat Engine** identifies overlaps between external events and active shipment regions/routes.
4. **Predict**: The Gradient Boosting model calculates the probability of delay and total revenue at risk.
5. **Mitigate**: If risk is HIGH/CRITICAL, the system autonomously emails the specific Supplier and Receiver with an immediate action plan.