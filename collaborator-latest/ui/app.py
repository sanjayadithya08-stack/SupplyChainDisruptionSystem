import streamlit as st
import requests
import sys, os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from ui.components import (
    THEME, load_premium_css, section_header, stat_card,
    render_risk_card, render_prevention_plan, render_confidence_bar,
    render_route_map, render_supplier_table, render_alert_card,
    render_health_badge, render_donut_chart
)

st.set_page_config(
    page_title="TechCore SupplyChain AI",
    page_icon="🚢", layout="wide",
    initial_sidebar_state="collapsed"
)
load_premium_css()

_host = "127.0.0.1" if Config.API_HOST == "0.0.0.0" else Config.API_HOST
API = f"http://{_host}:{Config.API_PORT}"

def api_get(path, params=None, timeout=6):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except: return None

def api_post(path, json=None, timeout=10):
    try:
        r = requests.post(f"{API}{path}", json=json, timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except: return None

health = api_get("/monitor/health")

def get_risk_color_local(risk):
    return {"LOW": THEME["green"], "MEDIUM": THEME["amber"], "HIGH": "#ff6b35", "CRITICAL": THEME["red"]}.get(str(risk).upper(), THEME["muted"])

# ── Topbar ─────────────────────────────────────────────────────────────────────
col_logo, col_status = st.columns([3, 1])
with col_logo:
    st.markdown(f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">
            <span style="font-size:2.2rem;">🏭</span>
            <div>
                <h1 style="margin:0;background:linear-gradient(90deg,{THEME['cyan']},{THEME['blue']});
                           -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                           font-size:1.7rem;font-weight:800;">TechCore SupplyChain AI</h1>
                <p style="margin:0;color:{THEME['muted']};font-size:0.8rem;">
                    Enterprise Shipment Tracking & Threat Intelligence
                </p>
            </div>
        </div>""", unsafe_allow_html=True)
with col_status:
    if health:
        status = health.get("status", "unknown")
        uptime = round(health.get("uptime_seconds", 0) / 60, 1)
        c = THEME["green"] if status == "healthy" else THEME["amber"]
        st.markdown(f"""
            <div style="text-align:right;margin-top:6px;">
                <div style="color:{c};font-weight:700;font-size:0.85rem;">● {status.upper()}</div>
                <div style="color:{THEME['muted']};font-size:0.72rem;">API · {uptime}m uptime</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:right;color:{THEME['red']};font-weight:700;font-size:0.85rem;margin-top:10px;'>● API OFFLINE</div>", unsafe_allow_html=True)

st.markdown(f"<hr style='border-color:{THEME['border']};margin:0.6rem 0 1rem;'>", unsafe_allow_html=True)

if not health:
    st.error("⚠️ API unreachable. Cannot fetch live shipment data.")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📦 Live Shipments", "📡 Threat Radar", "🗺️ Network Map", "📈 Analytics", "📊 System Monitor", "📰 Live Intelligence"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Live Shipments
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("Active Global Shipments", "Real-time tracking of in-transit cargo and estimated arrivals")
    
    shipments = api_get("/shipments/live") or []
    
    if shipments and isinstance(shipments, list):
        k1, k2, k3, k4 = st.columns(4)
        active = [s for s in shipments if s.get("status", "") != "Delivered"]
        val_transit = sum(s.get("value_usd", 0) for s in active)
        delays = sum(1 for s in active if s["status"] == "Delayed")
        
        with k1: stat_card("Active Shipments", str(len(active)), "📦", THEME["cyan"])
        with k2: stat_card("Value in Transit", f"${val_transit/1_000_000:.1f}M", "💰", THEME["green"])
        with k3: stat_card("Delayed", str(delays), "⚠️", THEME["amber"] if delays > 0 else THEME["green"])
        with k4: stat_card("Pending", str(sum(1 for s in active if s["status"] == "Pending")), "⏳", THEME["purple"])
        
        df_ship = pd.DataFrame(shipments)
        df_ship["value_usd"] = df_ship["value_usd"].apply(lambda x: f"${x:,.0f}")
        
        def style_status(val):
            c = THEME["green"] if val == "In Transit" else THEME["red"] if val == "Delayed" else THEME["amber"] if val == "Pending" else THEME["muted"]
            return f"color:{c};font-weight:700;"
            
        display_cols = ["id", "sku", "supplier_name", "origin", "destination", "estimated_arrival", "units", "value_usd", "status"]
        st.dataframe(df_ship[display_cols].style.map(style_status, subset=["status"]), use_container_width=True, height=400)
    else:
        st.info("No active shipments found.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Threat Radar (AI Live Engine)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    section_header("Live Threat Radar", "Cross-references global news, weather, and geopolitical events against your active shipments")
    
    col_scan = st.columns([1, 5])[0]
    if col_scan.button("📡 Scan for Threats", type="primary", use_container_width=True):
        with st.spinner("Analyzing global events and matching against shipment routes..."):
            threats_data = api_get("/shipments/threats", timeout=20)
            
        if not isinstance(threats_data, list):
            st.error("Threat scan failed." + (f" {threats_data.get('error')}" if isinstance(threats_data, dict) else ""))
        else:
            st.success("Scan complete!")
            st.markdown("---")
            
            for item in threats_data:
                shp = item["shipment"]
                threats = item["threats"]
                pred = item["prediction"]
                plan = item["plan"]
                
                risk_color = get_risk_color_local(pred["label"])
                
                with st.expander(f"📦 {shp['id']} ({shp['sku']}) — {shp['supplier_name']} to {shp['destination']} | Risk: {pred['label']}", expanded=(pred["label"] in ["HIGH", "CRITICAL"])):
                    c1, c2 = st.columns([1, 1.5])
                    with c1:
                        st.markdown(f"**Shipment Value:** ${shp['value_usd']:,.0f} | **Units:** {shp['units']:,}")
                        st.markdown(f"**Status:** {shp['status']} | **ETA:** {shp['estimated_arrival']}")
                        st.markdown(f"**Route:** {shp['route_id']} ({shp['origin']} → {shp['destination']})")
                        
                        st.markdown("<br><b>Detected Regional Threats:</b>", unsafe_allow_html=True)
                        if threats:
                            for t in threats:
                                tc = THEME["red"] if t["severity"] == "CRITICAL" else THEME["amber"]
                                st.markdown(f"<div style='background:{tc}22;padding:8px;border-left:3px solid {tc};margin-bottom:5px;font-size:0.85rem;'>[{t['source']}] {t['desc']}</div>", unsafe_allow_html=True)
                        else:
                            st.success("No active threats detected for this route.")
                            
                    with c2:
                        if plan:
                            if item.get("alert_sent"):
                                st.markdown(f"<div style='background:{THEME['green']}22;color:{THEME['green']};padding:8px 12px;border-radius:6px;font-size:0.85rem;font-weight:600;margin-bottom:12px;border:1px solid {THEME['green']}44;'>✅ Automated Mitigations Sent to {shp['supplier_id']} (Sender) and {shp['receiver_id']} (Receiver)</div>", unsafe_allow_html=True)
                            render_prevention_plan(plan, uid=shp["id"])
                        else:
                            st.info("No prevention plan required. Risk is low.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Network Map
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    section_header("Supply Chain Network Map", "Monitor suppliers and trade routes")
    sup_tab, route_tab = st.tabs(["🏭 Suppliers", "🛳️ Trade Routes"])
    with sup_tab:
        suppliers = api_get("/suppliers") or []
        if suppliers:
            high_risk = sum(1 for s in suppliers if s.get("risk_score", 0) >= 0.7)
            med_risk  = sum(1 for s in suppliers if 0.4 <= s.get("risk_score", 0) < 0.7)
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Total Suppliers", len(suppliers))
            sm2.metric("🔴 High Risk", high_risk)
            sm3.metric("🟡 Medium Risk", med_risk)
        render_supplier_table(suppliers)
    with route_tab:
        routes = api_get("/routes") or []
        shipments = shipments if isinstance(shipments, list) else []
        if routes:
            critical = sum(1 for r in routes if r.get("risk_level") == "CRITICAL")
            rm1, rm2 = st.columns(2)
            rm1.metric("Total Routes", len(routes))
            rm2.metric("🔴 Critical Routes", critical)
        render_route_map(routes, shipments)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Analytics (Company Intel)
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    section_header("Historical Disruption Analytics", "AI-driven insights from past company disruptions")
    cstats = api_get("/company/stats", timeout=6) or {}

    if cstats:
        k1, k2, k3, k4 = st.columns(4)
        with k1: stat_card("Total Historical Events", str(cstats.get("total_events", 0)), "📋", THEME["cyan"])
        with k2: stat_card("Historical Revenue at Risk", f"${cstats.get('total_revenue_at_risk',0)/1_000_000:.1f}M", "💰", THEME["red"])
        with k3: stat_card("Avg Delay", f"{cstats.get('avg_delay_days', 0)}d", "⏱️", THEME["amber"])
        with k4: stat_card("Historical Units Affected", f"{cstats.get('total_units_affected',0):,}", "📦", THEME["purple"])

    ci1, ci2, ci3 = st.tabs(["📈 Overview", "🔍 Event History", "⚠️ Supplier Risk"])

    with ci1:
        if cstats:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"<div style='color:{THEME['cyan']};font-weight:700;font-size:0.82rem;text-transform:uppercase;margin-bottom:10px;'>By Disruption Type</div>", unsafe_allow_html=True)
                for dtype, cnt in cstats.get("by_disruption_type", {}).items():
                    pct = int(cnt / max(cstats.get("total_events", 1), 1) * 100)
                    color = {"normal": THEME["green"], "port_strike": THEME["amber"], "weather": THEME["blue"],
                             "war": THEME["red"], "cyber": THEME["purple"], "supplier": "#ff6b35",
                             "logistics": THEME["cyan"], "customs": "#ffb020"}.get(dtype, THEME["muted"])
                    st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                            <div style="width:110px;color:{THEME['text']};font-size:0.83rem;">{dtype.replace('_',' ').title()}</div>
                            <div style="flex:1;background:{THEME['border']};border-radius:4px;height:10px;">
                                <div style="background:{color};width:{pct}%;height:10px;border-radius:4px;"></div>
                            </div>
                            <span style="color:{THEME['muted']};font-size:0.8rem;">{cnt}</span>
                        </div>""", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"<div style='color:{THEME['cyan']};font-weight:700;font-size:0.82rem;text-transform:uppercase;margin-bottom:10px;'>Top 5 Worst Events by Revenue</div>", unsafe_allow_html=True)
                for e in cstats.get("worst_events", []):
                    c = get_risk_color_local(e.get("label", "LOW"))
                    st.markdown(f"""
                        <div style="background:{THEME['card']};border-left:4px solid {c};border:1px solid {c}44;
                                    border-radius:8px;padding:10px 14px;margin-bottom:8px;">
                            <div style="display:flex;justify-content:space-between;">
                                <span style="color:{THEME['text']};font-weight:600;font-size:0.85rem;">{e['supplier_name']}</span>
                                <span style="color:{c};font-weight:700;">${e['revenue_at_risk_usd']:,}</span>
                            </div>
                            <div style="color:{THEME['muted']};font-size:0.75rem;margin-top:3px;">{e['date']} · {e['disruption_type']} · {e['label']}</div>
                        </div>""", unsafe_allow_html=True)

    with ci2:
        history = api_get("/company/history", timeout=10) or []
        if history:
            df_h = pd.DataFrame(history)
            acc = round(sum(1 for r in history if r.get("correct")) / len(history) * 100, 1)
            ha1, ha2, ha3 = st.columns(3)
            ha1.metric("Total Events", len(history))
            ha2.metric("Model Accuracy", f"{acc}%")
            ha3.metric("Mismatches", sum(1 for r in history if not r.get("correct")))
            filter_l = st.selectbox("Filter by Risk", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
            if filter_l != "All": df_h = df_h[df_h["actual"] == filter_l]
            def sr(val): c = get_risk_color_local(val); return f"background:{c}25;color:{c};font-weight:700;"
            def sc(val): return f"color:{THEME['green']};" if val else f"color:{THEME['red']};"
            cols = ["event_id","date","supplier_name","disruption_type","affected_units","delay_days","revenue_at_risk_usd","actual","label","confidence","correct"]
            avail = [c for c in cols if c in df_h.columns]
            st.dataframe(df_h[avail].style.map(sr, subset=[c for c in ["actual","label"] if c in avail]).map(sc, subset=["correct"] if "correct" in avail else []), use_container_width=True, height=400)

    with ci3:
        raw = api_get("/company/dataset", timeout=6) or []
        if raw:
            df_r = pd.DataFrame(raw)
            df_s = df_r.groupby("supplier_name").agg(
                total_events=("event_id","count"),
                critical=("label", lambda x: (x=="CRITICAL").sum()),
                high=("label", lambda x: (x=="HIGH").sum()),
                revenue_at_risk=("revenue_at_risk_usd","sum"),
                avg_delay=("delay_days","mean"),
                reliability=("supplier_reliability_score","mean"),
                country=("supplier_country","first"),
            ).reset_index().round(2).sort_values("revenue_at_risk", ascending=False)
            def srv(v): return f"color:{THEME['red']};font-weight:700;" if v > 2_000_000 else (f"color:{THEME['amber']};" if v > 500_000 else "")
            def scc(v): return f"color:{THEME['red']};font-weight:700;" if v > 2 else ""
            st.dataframe(df_s.style.map(srv, subset=["revenue_at_risk"]).map(scc, subset=["critical"]), use_container_width=True, height=400)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — System Monitor
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    section_header("System Monitor & Command Center", "Real-time health and alert broadcasting")

    col_refresh = st.columns([1, 5])[0]
    if col_refresh.button("🔄 Refresh", use_container_width=True):
        st.rerun()

    st.markdown(f"<div style='color:{THEME['cyan']};font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 10px;'>System Health</div>", unsafe_allow_html=True)
    if health:
        h1, h2, h3, h4 = st.columns(4)
        status = health.get("status", "unknown")
        uptime_m = round(health.get("uptime_seconds", 0) / 60, 1)
        arts = health.get("artefacts", {})
        sys_m = health.get("system_metrics", {})
        
        with h1: stat_card("API Status", status.upper(), "🟢" if status == "healthy" else "🔴", THEME["green"] if status == "healthy" else THEME["red"])
        with h2: stat_card("Uptime", f"{uptime_m}m", "⏱️", THEME["cyan"])
        with h3: stat_card("Model", "Loaded" if health.get("model_loaded") else "Missing", "🤖", THEME["green"] if health.get("model_loaded") else THEME["red"])
        with h4: stat_card("Artefacts", f"{sum(arts.values())}/{len(arts)}", "📦", THEME["purple"])
        
        if sys_m:
            st.markdown(f"<div style='color:{THEME['muted']};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>Server Resources</div>", unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            with s1:
                cpu = sys_m.get('cpu_percent', 0)
                st.progress(cpu / 100, text=f"💻 CPU Load: {cpu}%")
            with s2:
                mem = sys_m.get('memory_percent', 0)
                st.progress(mem / 100, text=f"🧠 Memory: {mem}%")
            with s3:
                disk = sys_m.get('disk_percent', 0)
                st.progress(disk / 100, text=f"💾 Disk: {disk}%")
    
    st.markdown(f"<div style='color:{THEME['cyan']};font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 10px;'>Recent Alerts & Broadcast</div>", unsafe_allow_html=True)
    al1, al2 = st.columns([2, 1], gap="large")
    with al1:
        alerts = api_get("/alerts") or []
        if alerts:
            for a in alerts[:8]:
                render_alert_card(a.get("level","INFO"), a.get("message",""), a.get("timestamp",""), a.get("channel","log"))
        else:
            st.markdown(f"<p style='color:{THEME['muted']};font-style:italic;'>No alerts logged yet.</p>", unsafe_allow_html=True)
    with al2:
        st.markdown(f"<div style='color:{THEME['text']};font-weight:600;font-size:0.88rem;margin-bottom:12px;'>📣 Broadcast Manual Alert</div>", unsafe_allow_html=True)
        with st.form("alert_form", clear_on_submit=True):
            lvl = st.selectbox("Level", ["INFO", "WARNING", "CRITICAL", "EMERGENCY"])
            msg = st.text_area("Message", height=90, placeholder="Describe the situation…")
            if st.form_submit_button("📡 Broadcast", use_container_width=True):
                if msg.strip():
                    api_post("/alerts/send", {"level": lvl, "message": msg})
                    st.success("Broadcast dispatched!")
                else:
                    st.warning("Enter a message first.")

        slack_status = "Slack [ON]" if Config.SLACK_WEBHOOK_URL else "Slack [OFF]"
        email_status = "Email [ON]" if Config.SMTP_USER else "Email [OFF]"
        st.caption(f"Channels active: {slack_status} | {email_status} | Log [ON]")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Live Intelligence
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    section_header("Live Global Intelligence", "Real-time news monitoring for possible disruptions")
    
    col_news_refresh, _ = st.columns([1, 5])
    if col_news_refresh.button("🔄 Fetch Latest News", use_container_width=True):
        st.rerun()
        
    with st.spinner("Fetching global news..."):
        news = api_get("/news") or []
        
    if not news:
        st.info("No news fetched or API unreachable.")
    else:
        st.markdown("<div style='display:flex;flex-direction:column;gap:16px;'>", unsafe_allow_html=True)
        for n in news:
            sev = n.get('severity_hint', 'LOW')
            color = get_risk_color_local(sev)
            url = n.get('url', '#')
            target = "target='_blank'" if url != '#' and url != '' else ""
            link_html = f'''<a href="{url}" {target} style="display:inline-block;background:{THEME['cyan']}15;color:{THEME['cyan']};
                                          padding:6px 14px;border-radius:6px;font-size:0.85rem;font-weight:600;
                                          text-decoration:none;border:1px solid {THEME['cyan']}44;transition:all 0.2s;">
                        Read Article 🔗
                    </a>''' if target else ""
            
            # Format published_at
            try:
                dt = pd.to_datetime(n.get('published_at', ''))
                date_str = dt.strftime("%b %d, %Y - %H:%M")
            except:
                date_str = n.get('published_at', '')
            
            st.markdown(f"""
                <div style="background:{THEME['card']};border-left:4px solid {color};
                            border-radius:8px;padding:16px;width:100%;box-shadow:0 2px 5px rgba(0,0,0,0.2);">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                        <div style="font-weight:700;font-size:1.1rem;color:{THEME['text']};max-width:80%;">{n.get('headline')}</div>
                        <div style="background:{color}22;color:{color};padding:4px 10px;border-radius:12px;font-size:0.7rem;font-weight:800;letter-spacing:0.05em;">{sev}</div>
                    </div>
                    <div style="color:{THEME['muted']};font-size:0.8rem;margin-bottom:12px;display:flex;gap:12px;">
                        <span>🏢 {n.get('source')}</span>
                        <span>🏷️ {n.get('category', '').title()}</span>
                        <span>🌍 {n.get('region', '').title()}</span>
                        <span>📅 {date_str}</span>
                    </div>
                    {link_html}
                </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)