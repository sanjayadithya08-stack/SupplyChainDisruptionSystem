<div align="center">
  <h1>🚢 Supply Chain Control Center</h1>
  <p><i>A shipment tracking and disruption response workspace that can use your company's own CSV data.</i></p>
  
  ![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
  ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
  ![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.3+-orange.svg)
  ![SQLite](https://img.shields.io/badge/SQLite-3.0+-blue.svg)
</div>

---

## 🌟 Overview

The Supply Chain Control Center starts with a bundled 120-shipment company dataset, 22 suppliers, and a mix of LOW, MEDIUM, HIGH, and CRITICAL baseline risks and shipment statuses. Home, Disruption Center, Shipments, Network Map, Actions & History, and Live Intelligence share the same workspace data. No dataset upload is needed for the current demo.

---

## 🚀 Key Features

- **📦 Built-in Shipments**: The sample ledger loads automatically and includes status, supplier, route, ETA, units, and shipment value.
- **🔍 Disruption Scans**: Check the active shipment list and show cause, risk, recommended actions, and shipment exposure.
- **🗺️ Connected Network Map**: Show suppliers and routes linked to the current shipment ledger, with open case risk reflected on affected entities.
- **✅ Shared Response History**: Record completed actions, review resolved cases, and follow configured critical-risk notifications from the same workspace.

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
├── ui/
│   ├── app.py                    <- Premium 6-Tab Command Center
│   └── components.py             <- Modern CSS & UI Component Library
├── utils/
│   └── config.py                 <- Master Configuration & Environment
└── logs/                         <- Automated Alert & Audit Trails
```

---

## 🛠️ Setup & Execution

### 1. Installation
```bash
# Activate your environment and install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Ensure your `.env` file contains the necessary keys for full functionality:
- `NEWS_API_KEY`: For live intelligence feed.
- `GEMINI_API_KEY`: For AI-generated executive summaries.
- `SLACK_WEBHOOK_URL`: For automated team notifications.

### 3. Launching the Platform
Start both the backend intelligence engine and the frontend command center:
```bash
python run.py all
```
Access the dashboard at `http://localhost:8501`.

### 4. Use the built-in company dataset
The API loads the bundled sample shipment ledger automatically on a fresh workspace. Open **Control Center** to review shipments and open cases, **Shipments** for risk-linked tracking details, **Network Map** for affected suppliers and routes, and **Actions & History** for resolved responses and the activity record. Use the shared refresh control after another user or process changes the workspace.

Each deployment is a single local company workspace. It is not a shared multi-company service; keep the database and `.env` private to the company running the deployment.

---

## 🧠 Intelligence Workflow

1. **Ingest**: The system monitors the internal SQLite database for all shipments marked "In Transit".
2. **Scan**: It polls live global APIs for news, weather, and geopolitical events.
3. **Correlate**: The **Live Threat Engine** identifies overlaps between external events and active shipment regions/routes.
4. **Predict**: The Gradient Boosting model calculates the probability of delay and total revenue at risk.
5. **Respond**: New CRITICAL findings create a cause-specific follow-up and notify available supplier and receiver contacts. Risks remain open for an operator to review and close.

## ⚙️ Operational workflow

The Operations tab completes the day-to-day response loop: it shows inventory health, creates validated purchase orders for configured SKUs, and provides a simple open-risk/completed-response view. Each scan, import, alert, purchase order, automated critical follow-up, and response is retained in the SQLite `actions` audit table and displayed in the Operations **Activity Log**. Automatic purchase-order mitigation remains disabled by default.

The API exposes the same functions for integrations:

- `GET /inventory`, `GET /orders`, `POST /orders`
- `GET /contacts/suppliers/{supplier_id}`
- `GET /automation/status`, `POST /automation/mitigate`
- `GET /activity` for the persistent action history

## 🤖 Automated monitoring

On API startup, the disruption monitor runs continuously (default: every 300 seconds). It evaluates active shipments against live NewsAPI headlines and weather only when a weather API key is configured. Local sample weather fixtures are not treated as current events. The monitor stores elevated findings, refreshes one open case per shipment, and archives cases when a subsequent scan no longer confirms the risk. New CRITICAL findings automatically start a cause-specific follow-up and email configured contacts. To send email, add `supplier_email` and `receiver_email` to the company CSV and configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD`. If an address or SMTP setup is missing, the dashboard and activity log show that the notice was saved locally and needs setup. The workflow requests information or review; it does not place orders, alter bookings, or close risks automatically. Configure the monitor in `.env`:

```env
AUTO_SCAN_ENABLED=true
SCAN_INTERVAL_SECONDS=300
AUTO_MITIGATION_ENABLED=false
AUTO_CRITICAL_RESPONSE_ENABLED=true
```

Set `AUTO_MITIGATION_ENABLED=true` only after confirming recipients, approval rules, and purchase-order controls: it executes mitigation for newly detected events automatically.
