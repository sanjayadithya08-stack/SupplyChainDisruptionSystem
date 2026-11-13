# TechCore: Enterprise Supply Chain Intelligence
## 🚢 Comprehensive Interview Study Guide

This document is a unified study guide designed to help you explain this project perfectly in your interview. It covers everything from high-level analogies to deep architectural decisions, without code snippets, formatted cleanly so you can read it, study it, or export it to PDF.

---

## 📅 1. The Elevator Pitch (How to introduce the project)
Use this structure when the interviewer says, *"Tell me about a project you've worked on."*

> *"I developed **TechCore SupplyChain AI**, a shipment-centric logistics intelligence platform designed to move supply chain operations from a reactive state to a proactive state. Unlike generic news scrapers, the system centers strictly on the company's proprietary logistics data. It tracks active shipments, monitors trade routes, and correlates real-time global disruptions (like severe weather, labor strikes, and geopolitical conflicts) to active routes. By matching these events geographically, the system uses machine learning to predict delay probabilities and total revenue-at-risk, then applies generative AI to autonomously draft and dispatch multi-phase mitigation plans to suppliers and logistics coordinators via Email and Slack."*

---

## 👦 2. Explain It Like I'm 14 (The "Lemonade Stand" Analogy)
Use this if the interviewer asks you to simplify the concept or explain it to a non-technical stakeholder.

* **The Problem**: Imagine you run a business that sells special lemons. You order lemons from different farms in Taiwan, Mexico, and Germany, and they travel on cargo ships to your shops. If a storm hits the ocean or truck drivers go on strike, your lemons get stuck. Normally, you wouldn't know until your shops run out of lemons and customers get angry.
* **The Solution**: You build a smart assistant. 
  1. It knows exactly which shipments of lemons are on which ships and where they are going.
  2. It constantly listens to global news and weather reports.
  3. If it hears about a typhoon near Taiwan, and knows your lemons are leaving a Taiwan port today, it sounds an alarm.
  4. It calculates exactly how many days late the lemons will be.
  5. It writes a recovery plan: *"Taiwan is blocked, so order a backup batch from a farm in South Korea, and tell the local shop manager to buy lemons from the local grocery store for the next 3 days."*
  6. It emails that plan to the Taiwan farm and the local shop manager automatically.

---

## 🛠️ 3. Tech Stack & Why It Matters (The "Why" behind the "What")
Expect questions on why you chose these specific libraries over others.

| Component | Technology | Professional Rationale |
| :--- | :--- | :--- |
| **Backend API** | **FastAPI** & **Uvicorn** | Chosen for its high performance (comparable to Node.js and Go), native asynchronous (`async/await`) support, automatic interactive documentation (`/docs` using Swagger UI), and robust data validation using Pydantic. |
| **Frontend UI** | **Streamlit** | Chosen to enable rapid prototyping of data-dense, interactive dashboards directly in Python. It eliminates the overhead of managing React/Vue builds, Webpack, or NPM packages, which is ideal for internal operations tools. |
| **Database & ORM** | **SQLite** & **SQLAlchemy** | SQLite is a serverless, zero-configuration relational database stored in a single file. SQLAlchemy is a powerful Python ORM that abstracts database access, prevents SQL injection, and enables easy joins between shipments, routes, and contacts. |
| **Machine Learning** | **Scikit-Learn** & **Pandas** | Used for data wrangling and classification. The system uses a **Gradient Boosting Classifier (GBM)** because decision-tree ensembles are the gold standard for tabular data (handling mixed categorical and numerical features far better than neural networks). |
| **Generative AI** | **Google Gemini 1.5 Flash** | Used to generate unstructured contingency playbooks. Gemini 1.5 Flash offers low latency and high accuracy for structuring text summaries. |
| **Notifications** | **SMTP** (Email) & **Slack Webhooks** | Enables dual-channel notification. Emails go to external suppliers, while Slack alerts go to internal operations teams, ensuring immediate response. |

---

## 📐 4. Software Architecture & File Breakdown
A guide to where everything lives in the workspace.

### A. Folder Structure & Key Files
* [**`api/main.py`**](file:///c:/SupplyChain/api/main.py): The FastAPI entry point. Defines all REST endpoints (e.g., fetching live shipments, running threat scans, retrieving history).
* [**`api/middleware.py`**](file:///c:/SupplyChain/api/middleware.py): Implements request logging, global exception handling, and a primitive IP-based rate limiter (60 requests/minute max).
* [**`db/models.py`**](file:///c:/SupplyChain/db/models.py): Defines the core database tables (Shipments, Suppliers, Routes) and seeds the initial data.
* [**`db/models_extended.py`**](file:///c:/SupplyChain/db/models_extended.py): Adds relational tables for enterprise operations: Supplier Contacts, Customer Receivers, Inventory Safety Stocks, Purchase Orders, and Financial Tracking.
* [**`ml/live_threat_engine.py`**](file:///c:/SupplyChain/ml/live_threat_engine.py): The core correlation engine. It pulls active shipments, fetches global events, matches them by region, and runs the models.
* [**`ml/company_predict.py`**](file:///c:/SupplyChain/ml/company_predict.py): The inference wrapper that loads the company's Gradient Boosting model to evaluate structured shipping events.
* [**`ml/company_train.py`**](file:///c:/SupplyChain/ml/company_train.py): The machine learning training pipeline. Cleans data, engineers features, trains models, and outputs the serialized model (`company_model.pkl`).
* [**`ml/prevention_engine.py`**](file:///c:/SupplyChain/ml/prevention_engine.py): The GenAI integration wrapper. Sends prompt templates to Gemini 1.5 Flash to generate step-by-step contingency actions.
* [**`services/alert_service.py`**](file:///c:/SupplyChain/services/alert_service.py): Dispatches warnings via email and Slack webhooks, logging histories locally.
* [**`services/cache_service.py`**](file:///c:/SupplyChain/services/cache_service.py): Simple in-memory Time-To-Live (TTL) cache to prevent overloading external news/weather APIs.
* [**`ui/app.py`**](file:///c:/SupplyChain/ui/app.py): The 5-tab Streamlit dashboard interface.

---

## ⚙️ 5. End-to-End Workflow (How data flows)
Walk the interviewer through a single cycle of the system:

1. **Triggering**: An operations manager clicks **"Scan for Threats"** on the Streamlit UI.
2. **Database Query**: The UI sends a request to FastAPI, which queries the SQLite database for all active shipments (marked "In Transit").
3. **Data Ingestion**: The system queries external APIs:
   - NewsAPI for global headlines containing keywords like "supply chain disruption."
   - OpenWeatherMap for severe storms or natural disasters.
   - Geopolitical services for strikes, wars, or customs policy changes.
4. **Geographic Correlation**: The **Live Threat Engine** compares shipment regions (e.g. `east-asia`) with threat regions. If a match is found, an overlap is flagged.
5. **Machine Learning Inference**: For every matched shipment, details (reliability, units, revenue, threat type) are packaged into an event payload. The Gradient Boosting model predicts the disruption risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
6. **AI Plan Generation**: If the risk is `HIGH` or `CRITICAL`, the payload is sent to Google Gemini 1.5 Flash. The LLM returns a structured JSON object outlining the immediate (1h), short-term (24h), and long-term (1w) response steps.
7. **Stakeholder Notification**: The **Alert Service** dispatches:
   - An email with the recovery steps to the supplier and receiver.
   - A warning block to the operations team's Slack channel.
   - An entry in the local prediction logs.
8. **UI Presentation**: The Streamlit frontend renders the maps, charts, and actionable checkboxes for the user.

---

## 🧠 6. Machine Learning Deep-Dive (How the AI works)
Be ready to explain the two-tier AI design:

### Tier 1: The Text Classifier (Unstructured Data)
* **Purpose**: Read arbitrary news text and classify the severity of the threat.
* **Pipeline**: Text is lowercased and stripped of URLs/punctuation. A TF-IDF vectorizer extracts character and word patterns. The text is classified into risk levels.
* **Why it matters**: It converts chaotic, human-written news articles into clean, standardized inputs the database can understand.

### Tier 2: The Enterprise Predictor (Structured Data)
* **Purpose**: Evaluate the actual business impact on a shipment.
* **Feature Engineering**:
  - `cost_per_unit` = `revenue_at_risk` / `affected_units` (identifies high-value low-volume cargo).
  - `supplier_risk_index` = `(1 - supplier_reliability_score) * (delay_days + 1)` (evaluates risk factor).
  - `volume_severity` = Categorizes unit quantities into bins (`LOW` to `CRITICAL`).
  - `month` = Captures seasonality (e.g., winter storms in Europe, holiday shipping rushes).
* **Pre-processing**: Uses a `ColumnTransformer` to encode categorical text (using `OneHotEncoder`) and normalize numeric scales (using `StandardScaler`).
* **Model**: Compares Logistic Regression, Random Forest, and Gradient Boosting. Gradient Boosting is selected for its high Macro-F1 score on tabular data.

---

## 🎯 7. Top Technical Interview Questions & Answers

### Q: Why use a hybrid architecture of Classical ML + GenAI instead of just using LLMs for everything?
> **Answer**: *"Using LLMs for everything is expensive, slow, and non-deterministic. Classic Machine Learning (like Gradient Boosting) is highly deterministic and excels at processing tabular business records (prices, scores, quantities) in milliseconds for fractions of a cent. Generative AI (Gemini), on the other hand, excels at semantic understanding and text generation. We use Scikit-Learn to compute the risk numbers, and Gemini only to draft the human-readable response guides. This keeps our system fast, cheap, and auditable."*

### Q: How does the system handle API failures (like Gemini or NewsAPI going offline)?
> **Answer**: *"The application is designed with strict fallback mechanisms to ensure high availability. If the News or Weather APIs fail or run out of credits, the services gracefully load high-quality local stub data. If the Gemini API is offline, the Prevention Engine bypasses the LLM and calls a deterministic, rule-based playbook engine. This ensures the operations team never sees a broken screen."*

### Q: How do the frontend and backend communicate?
> **Answer**: *"They interact via a stateless REST API model over HTTP. The backend is a FastAPI web server running under Uvicorn, and the Streamlit frontend acts as a client that fetches data using python's `requests` library. All database records and model outputs are validated by the backend using Pydantic schemas before being serialized into JSON. This separates frontend layout code from backend database/ML pipelines."*

### Q: What security and stability features are built into the API?
> **Answer**: *"We implemented a custom Starlette middleware layer in the FastAPI backend. It does three things: log every request's HTTP status and response times, enforce a rate limiter of 60 requests per minute per IP using a simple in-memory TTL tracker to prevent API abuse, and catch all unhandled exceptions globally to return a clean 500 JSON error, ensuring a single bad query never crashes the backend server."*
