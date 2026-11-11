import streamlit as st
import requests
import sys, os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from ui.components import (
    THEME, DISRUPTION_COLORS, load_premium_css, section_header, stat_card,
    render_risk_card, render_prevention_plan, render_confidence_bar,
    render_route_map, render_supplier_table, render_alert_card,
    render_health_badge, render_donut_chart, risk_badge, status_badge, empty_state
)

st.set_page_config(
    page_title="Supply Chain Control Center",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)
load_premium_css()

_host = "127.0.0.1" if Config.API_HOST == "0.0.0.0" else Config.API_HOST
API = f"http://{_host}:{Config.API_PORT}"

# ── API Helpers ────────────────────────────────────────────────────────────────
def api_get(path, params=None, timeout=6):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def api_post(path, json=None, timeout=10):
    try:
        r = requests.post(f"{API}{path}", json=json, timeout=timeout)
        return r.json() if 200 <= r.status_code < 300 else None
    except:
        return None

def get_risk_color_local(risk):
    return {
        "LOW": THEME["green"], "MEDIUM": THEME["amber"],
        "HIGH": THEME["orange"], "CRITICAL": THEME["red"]
    }.get(str(risk).upper(), THEME["muted"])

def action_guidance(action):
    """Directional operational guidance; intentionally avoids claiming savings."""
    text = str(action).casefold()
    if any(word in text for word in ("reroute", "air freight", "expedite", "backup carrier", "switch to inland")):
        return "May shorten transit or avoid the disrupted lane", "Higher transport cost is possible; confirm a carrier quote"
    if any(word in text for word in ("buffer", "safety stock", "pre-position", "inventory", "replenishment")):
        return "May protect service while supply is delayed", "Requires inventory, storage, or working capital"
    if any(word in text for word in ("alternate supplier", "secondary supplier", "tier-2", "dual-source", "diversification")):
        return "Can reduce dependence on the affected supplier", "Supplier qualification and purchase costs may apply"
    if any(word in text for word in ("notify", "contact", "alert", "monitor", "check", "assess", "review", "verify", "escalate")):
        return "Improves visibility and coordination; may not remove the delay by itself", "Usually low direct cost; staff time required"
    return "Could reduce exposure; confirm feasibility with the carrier or supplier", "Depends on the chosen provider and execution"

def render_disruption_case(event, shipment, is_open, activity):
    risk = str(event.get("risk_level", "HIGH")).upper()
    event_type = str(event.get("disruption_type", "supply chain")).replace("_", " ").title()
    shipment_id = event.get("shipment_id", "Shipment")
    plan = event.get("plan") or {}
    event_actions = [a for a in activity if a.get("action_type") == "disruption_mitigated"
                     and (a.get("metadata") or {}).get("event_id") == event.get("id")]
    auto_responses = [a for a in activity if a.get("action_type") == "critical_response_automated"
                      and (a.get("metadata") or {}).get("event_id") == event.get("id")]
    failed_responses = [a for a in activity if a.get("action_type") == "critical_response_failed"
                        and (a.get("metadata") or {}).get("event_id") == event.get("id")]
    title = f"{'🔴' if risk == 'CRITICAL' else '🟠'} {risk}  ·  {shipment_id}  ·  {event_type}"
    with st.expander(title, expanded=False):
        overview, exposure = st.columns([1.35, 1], gap="large")
        with overview:
            st.markdown("**Cause**")
            st.caption(f"Detected as {event_type.lower()} disruption · {float(event.get('confidence', 0) or 0):.0%} model confidence")
            st.write(event.get("source_summary") or "No external cause details were attached to this finding.")
        with exposure:
            st.markdown("**Shipment impact at a glance**")
            st.write(f"**{shipment.get('sku', 'SKU not supplied')}** · {shipment.get('supplier_name', 'Supplier not supplied')}")
            st.write(f"{shipment.get('origin', 'Origin')} → {shipment.get('destination', 'Destination')} · ETA {shipment.get('estimated_arrival', 'Not supplied')}")
            st.metric("Shipment value exposed", f"${float(shipment.get('value_usd', 0) or 0):,.0f}")
            st.caption("Exposure is shipment value, not a forecast of financial loss.")

        if auto_responses:
            response_meta = auto_responses[0].get("metadata") or {}
            st.markdown("#### Automatic critical response")
            st.success(response_meta.get("automated_action", "Cause-specific follow-up created."))
            supplier_status = response_meta.get("supplier_notification") or {}
            customer_status = response_meta.get("customer_notification") or {}
            notify_cols = st.columns(2)
            for notify_col, label, result in (
                (notify_cols[0], "Supplier alert", supplier_status),
                (notify_cols[1], "Customer alert", customer_status),
            ):
                status = result.get("status", "not_configured")
                status_label = {"sent": "Email sent", "partially_sent": "Some emails failed", "failed": "Delivery failed", "not_configured": "Not configured"}.get(status, status.replace("_", " ").title())
                with notify_col:
                    st.markdown(f"**{label}:** {status_label}")
                    detail = result.get("detail")
                    if detail:
                        st.caption(detail)
                    elif status == "failed":
                        st.caption("Check SMTP settings; this notice was logged locally.")
                    elif status == "not_configured":
                        st.caption("Add this contact's email and configure SMTP to send notices.")
                    elif status == "sent":
                        st.caption(f"Sent to {result.get('sent_count', result.get('contacts', 1))} configured contact(s).")
                    elif status == "partially_sent":
                        st.caption(f"Sent to {result.get('sent_count', 0)} of {result.get('contacts', 0)} configured contact(s).")
            st.caption("The automatic step requests confirmation or recovery options. It does not change bookings or close the disruption.")
        elif failed_responses:
            st.error("Automatic follow-up failed. This critical disruption needs operator attention.")

        st.markdown("#### Alternative actions")
        horizon_names = [("immediate_actions", "Now"), ("short_term_actions", "Next 24 hours"), ("long_term_actions", "Longer term")]
        action_sets = [(label, plan.get(key) or []) for key, label in horizon_names]
        action_sets = [(label, items) for label, items in action_sets if items]
        if action_sets:
            horizon_tabs = st.tabs([label for label, _ in action_sets])
            for tab, (label, actions) in zip(horizon_tabs, action_sets):
                with tab:
                    cards = st.columns(min(3, max(1, len(actions))))
                    for index, action in enumerate(actions):
                        impact, tradeoff = action_guidance(action)
                        with cards[index % len(cards)]:
                            with st.container(border=True):
                                st.markdown(f"**Option {index + 1}**")
                                st.write(action)
                                st.caption(f"**Likely effect:** {impact}")
                                st.caption(f"**Trade-off:** {tradeoff}")
        else:
            st.info("No action plan is attached. Run a disruption scan to generate response options.")

        st.markdown("#### Outcome")
        if is_open:
            with st.form(f"center_resolution_{event.get('id', '')}"):
                action_choices = [action for _, actions in action_sets for action in actions]
                action_choices = ["Select the action your team completed…"] + list(dict.fromkeys(action_choices))
                action_choices += ["Supplier contacted", "Shipment rerouted", "Inventory buffer arranged",
                                   "Reviewed; no operational change", "Other action"]
                selected_action = st.selectbox("Action completed", action_choices,
                                               key=f"center_action_{event.get('id', '')}")
                response_detail = st.text_input("Notes (optional)", key=f"center_note_{event.get('id', '')}")
                if st.form_submit_button("Record completed action", type="primary"):
                    if selected_action == "Select the action your team completed…":
                        st.error("Choose an action your team actually completed before recording the outcome.")
                        pass
                    else:
                        response_text = selected_action + (f" — {response_detail.strip()}" if response_detail.strip() else "")
                        outcome = api_post(f"/disruptions/{event.get('id')}/resolve", {"action_taken": response_text})
                        if outcome and outcome.get("event", {}).get("status") == "mitigated":
                            st.session_state["last_center_update"] = f"Recorded action for {shipment_id}. The case is now resolved."
                            st.rerun()
                        st.error("Could not record the action. This disruption remains open.")
        elif event_actions:
            resolution = (event_actions[0].get("metadata") or {}).get("resolution")
            st.success(f"Recorded action: {resolution or event_actions[0].get('summary', 'Response logged.')}")
            st.caption("Case closed. Closure records the review outcome; it does not mean the shipment value was recovered.")
        else:
            st.info("This case is closed, but no completed action is available in the recent activity record.")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    health = api_get("/monitor/health")
    api_available = health is not None
    model_ready = api_available and health.get("model_loaded", False)
    status_color = (
        THEME["green"] if model_ready else
        THEME["amber"] if api_available else THEME["red"]
    )
    status_label = "ONLINE" if model_ready else "DEGRADED" if api_available else "OFFLINE"
    uptime = round(health.get("uptime_seconds", 0) / 60, 1) if health else 0

    st.markdown(f"""
        <div style="padding:20px 16px 16px;border-bottom:1px solid {THEME['border']};margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <span style="font-size:1.8rem;">🚢</span>
                <div>
                    <div style="color:{THEME['text']};font-weight:800;font-size:1rem;letter-spacing:-0.01em;">Supply Chain</div>
                    <div style="color:{THEME['muted']};font-size:0.7rem;letter-spacing:0.04em;">OPERATIONS WORKSPACE</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;background:{status_color}15;
                        border:1px solid {status_color}35;border-radius:20px;padding:5px 12px;">
                <div style="width:7px;height:7px;border-radius:50%;background:{status_color};"></div>
                <span style="color:{status_color};font-size:0.72rem;font-weight:700;letter-spacing:0.06em;">API {status_label}</span>
                {f'<span style="color:{THEME["muted"]};font-size:0.68rem;margin-left:auto;">{uptime}m</span>' if health else ''}
            </div>
        </div>
    """, unsafe_allow_html=True)

    if api_available and not model_ready:
        st.caption("API is reachable, but its prediction model is unavailable.")

    # Navigation
    nav_color = THEME["muted"]
    st.markdown(
        f"<div style='color:{nav_color};font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;padding:0 12px;margin-bottom:6px;'>Navigation</div>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "nav",
        options=[
            "🏠  Home",
            "🚨  Disruption Center",
            "📦  Shipments",
            "🗺️  Network Map",
            "⚙️  Actions & History",
            "📰  Live Intelligence",
        ],
        label_visibility="collapsed",
        key="main_nav"
    )

    st.caption("Pages read the saved shipment ledger, disruption cases, and alerts from the local API.")
    if st.button("↻ Reload workspace records", use_container_width=True, key="refresh_workspace_data"):
        st.rerun()
    st.caption("Reloads saved records; it does not request GPS or carrier updates.")

    # Sidebar footer
    now_str = datetime.now().strftime("%b %d, %Y  %H:%M")
    st.markdown(f"""
        <div style="position:fixed;bottom:0;left:0;width:220px;padding:14px 16px;
                    border-top:1px solid {THEME['border']};background:{THEME['bg2']};">
            <div style="color:{THEME['muted']};font-size:0.68rem;">🕒 {now_str}</div>
            <div style="color:{THEME['muted']};font-size:0.65rem;margin-top:3px;">Shipment tracking · Threat response</div>
        </div>
    """, unsafe_allow_html=True)

# ── Top Banner ─────────────────────────────────────────────────────────────────
st.markdown(f"""
    <div style="background:linear-gradient(90deg,{THEME['accent']}22,{THEME['cyan']}15,transparent);
                border:1px solid {THEME['border']};border-radius:12px;
                padding:16px 24px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;">
        <div>
            <h1 style="margin:0;color:{THEME['text']};font-size:1.4rem;font-weight:800;letter-spacing:-0.02em;">
                {page.split('  ', 1)[1] if '  ' in page else page}
            </h1>
            <div style="color:{THEME['muted']};font-size:0.78rem;margin-top:3px;">
                Shipment tracking · Threat monitoring · Action history
            </div>
        </div>
        <div style="text-align:right;">
            <div style="color:{THEME['muted']};font-size:0.72rem;">{datetime.now().strftime('%A, %B %d %Y')}</div>
            <div style="color:{THEME['cyan']};font-size:0.78rem;font-weight:600;">{datetime.now().strftime('%H:%M IST')}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Home
# ══════════════════════════════════════════════════════════════════════════════
if "🏠" in page:
    section_header("Home", "Active shipment tracking and the latest operational alerts.", "🏠")
    center_shipments = api_get("/shipments/live") or []
    open_events = api_get("/disruptions", params={"status": "open", "limit": 200}) or []
    alert_rows = api_get("/alerts", params={"limit": 8}) or []
    center_by_id = {item.get("id"): item for item in center_shipments}
    event_by_shipment = {event.get("shipment_id"): event for event in open_events}
    active_center_shipments = [item for item in center_shipments if str(item.get("status", "")).casefold() != "delivered"]
    alert_rows = alert_rows if isinstance(alert_rows, list) else []
    critical_count = sum(1 for event in open_events if str(event.get("risk_level", "")).upper() == "CRITICAL")
    delayed_count = sum(1 for item in active_center_shipments if str(item.get("status", "")).casefold() == "delayed")
    home_metrics = st.columns(4)
    with home_metrics[0]: stat_card("Active shipments", str(len(active_center_shipments)), "📦", THEME["cyan"])
    with home_metrics[1]: stat_card("Delayed", str(delayed_count), "⏳", THEME["amber"] if delayed_count else THEME["green"])
    with home_metrics[2]: stat_card("Open disruptions", str(len(open_events)), "🚨", THEME["red"] if open_events else THEME["green"])
    with home_metrics[3]: stat_card("Critical risks", str(critical_count), "🔴", THEME["red"] if critical_count else THEME["green"])

    st.markdown(f"#### Active shipments · {len(active_center_shipments)}")
    if active_center_shipments:
        for row_start in range(0, len(active_center_shipments), 2):
            shipment_cards = st.columns(2, gap="small")
            for card, shipment in zip(shipment_cards, active_center_shipments[row_start:row_start + 2]):
                status_text = str(shipment.get("status", "Unknown"))
                status_color = {"In Transit": THEME["cyan"], "Delayed": THEME["red"], "Pending": THEME["amber"]}.get(status_text, THEME["muted"])
                event = event_by_shipment.get(shipment.get("id"))
                with card:
                    with st.container(border=True):
                        header_cols = st.columns([1.6, 1])
                        header_cols[0].markdown(f"**{shipment.get('id', 'Shipment')}**")
                        header_cols[1].markdown(f"<span style='color:{status_color};font-weight:700'>{status_text}</span>", unsafe_allow_html=True)
                        st.markdown(f"{shipment.get('sku', 'SKU')} · {shipment.get('supplier_name', 'Supplier not supplied')}")
                        st.caption(f"{shipment.get('origin', 'Origin')} → {shipment.get('destination', 'Destination')}")
                        st.caption(f"ETA {shipment.get('estimated_arrival', 'Not supplied')} · {int(shipment.get('units', 0) or 0):,} units · ${float(shipment.get('value_usd', 0) or 0):,.0f}")
                        if event:
                            st.warning(f"{str(event.get('risk_level', 'HIGH')).upper()} · {str(event.get('disruption_type', 'Disruption')).replace('_', ' ').title()}")
    else:
        empty_state("There are no active shipments in the built-in company dataset.", "📭")
    st.caption(f"Data source: built-in company dataset · {len(center_shipments)} shipments · updated from the shared workspace")

    st.markdown("#### Latest alerts & messages")
    if alert_rows:
        for alert in alert_rows[:8]:
            render_alert_card(str(alert.get("level", "INFO")).upper(), alert.get("message", ""), alert.get("timestamp", ""), alert.get("channel", "log"))
    else:
        st.info("No alert messages have been recorded yet. Scan results and response notices will appear here.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Disruption Center
# ══════════════════════════════════════════════════════════════════════════════
elif "🚨" in page:
    section_header("Disruption Center", "Scan the company shipment dataset, review causes, and manage response plans.", "🚨")
    open_events = api_get("/disruptions", params={"status": "open", "limit": 200}) or []
    closed_events = api_get("/disruptions", params={"status": "mitigated", "limit": 200}) or []
    center_shipments = api_get("/shipments/live") or []
    center_activity = api_get("/activity", params={"limit": 100}) or []
    center_by_id = {item.get("id"): item for item in center_shipments}
    center_message = st.session_state.pop("last_center_update", None)
    if center_message:
        st.success(center_message)
    if st.button("🔍 Scan shipments for disruptions", type="primary"):
        with st.spinner("Checking active shipments for disruption signals…"):
            scan_result = api_post("/disruptions/scan", timeout=60)
        if scan_result:
            st.session_state["center_scan_message"] = (
                f"Scan complete: checked {scan_result.get('scanned_shipments', 0)} shipments; "
                f"found {scan_result.get('new_events', 0)} new disruptions."
            )
            st.rerun()
        st.error("The scan could not be completed. Check that the API is online.")

    scan_message = st.session_state.pop("center_scan_message", None)
    if scan_message:
        st.info(scan_message)

    active_ids = {event.get("shipment_id") for event in open_events}
    exposure_total = sum(float(center_by_id.get(sid, {}).get("value_usd", 0) or 0) for sid in active_ids)
    critical_count = sum(1 for event in open_events if str(event.get("risk_level", "")).upper() == "CRITICAL")
    summary_cols = st.columns(4)
    with summary_cols[0]: stat_card("Open disruptions", f"{len(open_events):,}", "🚨", THEME["red"] if open_events else THEME["green"])
    with summary_cols[1]: stat_card("Critical cases", f"{critical_count:,}", "🔴", THEME["red"] if critical_count else THEME["green"])
    with summary_cols[2]: stat_card("Shipments affected", f"{len(active_ids):,}", "📦", THEME["cyan"])
    with summary_cols[3]: stat_card("Shipment value exposed", f"${exposure_total:,.0f}", "💰", THEME["amber"])
    st.caption("Exposure is the value of affected shipments. It is not a forecast of loss or savings.")

    st.markdown("#### Response plans")
    st.caption("Each case includes immediate, next 24-hour, and longer-term options. Critical follow-ups and notification delivery are shown inside the case; operational alternatives remain recommendations until your team records the action taken.")
    filter_cols = st.columns([1, 2])
    with filter_cols[0]: center_risk_filter = st.selectbox("Priority", ["All", "CRITICAL", "HIGH"], key="center_priority")
    with filter_cols[1]: center_search = st.text_input("Find a shipment, supplier, or cause", key="center_search")

    def filter_center_events(events):
        visible = []
        for event in events:
            shipment = center_by_id.get(event.get("shipment_id"), {})
            if center_risk_filter != "All" and str(event.get("risk_level", "")).upper() != center_risk_filter:
                continue
            searchable = " ".join(str(value or "") for value in (
                event.get("shipment_id"), event.get("disruption_type"), event.get("source_summary"),
                shipment.get("supplier_name"), shipment.get("sku"), shipment.get("origin"), shipment.get("destination")
            )).casefold()
            if center_search.strip().casefold() not in searchable:
                continue
            visible.append(event)
        return visible

    active_tab, resolved_tab = st.tabs([f"Needs attention · {len(open_events)}", f"Resolved · {len(closed_events)}"])
    with active_tab:
        visible_open = filter_center_events(open_events)
        if visible_open:
            st.caption(f"Showing {len(visible_open)} disruptions")
            for event in visible_open:
                render_disruption_case(event, center_by_id.get(event.get("shipment_id"), {}), True, center_activity)
        else:
            empty_state("No disruptions match these filters. Run a scan to look for new issues.", "✅")
    with resolved_tab:
        visible_closed = filter_center_events(closed_events)
        if visible_closed:
            for event in visible_closed:
                render_disruption_case(event, center_by_id.get(event.get("shipment_id"), {}), False, center_activity)
        else:
            empty_state("Resolved cases and recorded actions will appear here.", "📋")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Live Shipments
# ══════════════════════════════════════════════════════════════════════════════
elif "📦" in page:
    section_header("Shipments", "Shipment ledger from the built-in company dataset, with linked disruption risks and response details.", "📦")

    if not health:
        st.error("⚠️ API unreachable — cannot fetch shipment records. Make sure the backend is running.")
        st.stop()

    shipments = api_get("/shipments/live", timeout=25)
    if not isinstance(shipments, list):
        detail = shipments.get("error", "The API returned no shipment list.") if isinstance(shipments, dict) else "The shipment API did not respond."
        st.error(f"Could not load shipment records: {detail}")
        st.stop()
    open_events = api_get("/disruptions", params={"status": "open", "limit": 200}) or []
    event_by_shipment = {event.get("shipment_id"): event for event in open_events}

    # Validate response
    if shipments and isinstance(shipments, list) and not isinstance(shipments[0], str) and "error" not in str(shipments[0]):
        active = [s for s in shipments if s.get("status") != "Delivered"]
        val_transit = sum(s.get("value_usd", 0) for s in active)
        delays = sum(1 for s in active if s.get("status") == "Delayed")
        pending = sum(1 for s in active if s.get("status") == "Pending")
        in_transit = sum(1 for s in active if s.get("status") == "In Transit")

        summary_cols = st.columns(4)
        with summary_cols[0]: stat_card("Active Shipments", str(len(active)), "📦", THEME["cyan"], f"{in_transit} in transit")
        with summary_cols[1]: stat_card("Value in Transit", f"${val_transit/1_000_000:.1f}M", "💰", THEME["green"])
        with summary_cols[2]: stat_card("Delayed", str(delays), "⚠️", THEME["red"] if delays else THEME["green"])
        with summary_cols[3]: stat_card("Pending", str(pending), "⏳", THEME["amber"])
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # Search / filter bar
        fcol1, fcol2, fcol3 = st.columns([2, 2, 1])
        with fcol1:
            search_q = st.text_input("🔍 Search shipment / SKU / supplier", placeholder="e.g. SHP-001, SKU-MC01, Global MicroTech", label_visibility="collapsed")
        with fcol2:
            filter_status = st.selectbox("Status", ["All", "In Transit", "Delayed", "Pending", "Delivered"], label_visibility="collapsed")
        with fcol3:
            if st.button("↻ Reload", use_container_width=True, help="Fetch the saved shipment records and linked risks from the local API"):
                st.rerun()

        # Keep completed shipments visible in the ledger. The headline cards
        # still focus on active work, while the table represents the full upload.
        df_ship = pd.DataFrame(shipments)
        df_ship["risk_level"] = df_ship.apply(lambda row: event_by_shipment.get(row["id"], {}).get("risk_level", row.get("risk_level", "LOW")), axis=1)
        df_ship["disruption_cause"] = df_ship["id"].map(lambda shipment_id: str(event_by_shipment.get(shipment_id, {}).get("disruption_type", "")).replace("_", " ").title() or "—")
        df_ship["next_action"] = df_ship["id"].map(lambda shipment_id: (event_by_shipment.get(shipment_id, {}).get("plan") or {}).get("immediate_actions", ["Review shipment status"])[0] if shipment_id in event_by_shipment else "No action needed")
        if search_q:
            mask = df_ship.apply(lambda row: search_q.lower() in str(row.values).lower(), axis=1)
            df_ship = df_ship[mask]
        if filter_status != "All":
            df_ship = df_ship[df_ship["status"] == filter_status]

        # Format columns
        df_disp = df_ship.copy()
        if "value_usd" in df_disp.columns:
            df_disp["value_usd"] = df_disp["value_usd"].apply(lambda x: f"${x:,.0f}")
        if "units" in df_disp.columns:
            df_disp["units"] = df_disp["units"].apply(lambda x: f"{x:,}")

        df_disp["route"] = df_disp.apply(lambda row: f"{row.get('origin', '—')} → {row.get('destination', '—')}", axis=1)
        display_cols = [c for c in ["id", "status", "risk_level", "sku", "supplier_name", "route", "estimated_arrival", "units", "value_usd"] if c in df_disp.columns]

        st.markdown(f"#### Shipment details · {len(df_disp)} records")
        st.caption("Saved company records from the local workspace database. Use the selector below for cause, supplier, customer, and response details.")
        table_df = df_disp[display_cols].rename(columns={
            "id": "Shipment ID", "status": "Status", "risk_level": "Risk", "sku": "SKU",
            "supplier_name": "Supplier", "route": "Route", "estimated_arrival": "ETA",
            "units": "Units", "value_usd": "Shipment value",
        })
        with st.container(height=520, border=True):
            st.table(table_df)
        st.caption(f"Showing {len(df_disp)} of {len(shipments)} shipments in the dataset")
        shipment_lookup = {row.get("id"): row for row in shipments}
        selected_id = st.selectbox(
            "Open full shipment details",
            options=df_disp["id"].tolist() if not df_disp.empty else [],
            format_func=lambda shipment_id: f"{shipment_id} · {shipment_lookup.get(shipment_id, {}).get('status', 'Unknown')} · {shipment_lookup.get(shipment_id, {}).get('supplier_name', 'Supplier')} ",
            key="shipment_detail_select",
        ) if not df_disp.empty else None
        if selected_id:
            selected = shipment_lookup.get(selected_id, {})
            linked = event_by_shipment.get(selected_id, {})
            detail_cols = st.columns(2)
            with detail_cols[0]:
                st.markdown(f"**{selected.get('sku', 'SKU')} · {selected.get('supplier_name', 'Supplier')}**")
                st.write(f"Supplier country: {selected.get('supplier_country', '—')}")
                st.write(f"Route: {selected.get('origin', '—')} → {selected.get('destination', '—')}")
                st.write(f"Customer / receiver: {selected.get('receiver_id', '—')}")
            with detail_cols[1]:
                st.write(f"Status: **{selected.get('status', '—')}** · ETA {selected.get('estimated_arrival', '—')}")
                st.write(f"Units: **{int(selected.get('units', 0) or 0):,}** · Value: **${float(selected.get('value_usd', 0) or 0):,.0f}**")
                if linked:
                    linked_plan = linked.get("plan") or {}
                    next_step = (linked_plan.get("immediate_actions") or ["Review the open disruption"])[0]
                    st.warning(f"{str(linked.get('risk_level', 'HIGH')).upper()} · {str(linked.get('disruption_type', 'Disruption')).replace('_', ' ').title()} · {next_step}")
                else:
                    st.success("No open disruption linked to this shipment.")
    elif not shipments:
        empty_state("The shipment API returned no records. The bundled company dataset should load automatically when the API starts.", "📭")
    else:
        empty_state("The shipment response could not be displayed. Reload the page or check the API.", "⚠️")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Network Map
# ══════════════════════════════════════════════════════════════════════════════
elif "🗺️" in page:
    section_header("Supply Chain Network Map", "Global supplier hubs and trade routes with risk overlays", "🗺️")

    refresh_col, _ = st.columns([1, 4])
    if refresh_col.button("↻ Refresh network data", use_container_width=True):
        st.rerun()

    suppliers_result = api_get("/suppliers")
    routes_result = api_get("/routes")
    shipments = api_get("/shipments/live") or []
    open_events = api_get("/disruptions", params={"status": "open", "limit": 200}) or []
    suppliers = suppliers_result if isinstance(suppliers_result, list) else []
    routes = routes_result if isinstance(routes_result, list) else []

    # Keep the map scoped to entities used by this built-in company ledger so
    # unrelated seed/master rows cannot look like missing or mismatched data.
    used_supplier_ids = {shipment.get("supplier_id") for shipment in shipments}
    used_route_ids = {shipment.get("route_id") for shipment in shipments}
    if suppliers_result is not None:
        suppliers = [supplier for supplier in suppliers if supplier.get("id") in used_supplier_ids]
    if routes_result is not None:
        routes = [route for route in routes if route.get("id") in used_route_ids]

    if suppliers_result is None:
        st.error("Could not load suppliers from the workspace API. Check that the API is online, then refresh this page.")
    elif not suppliers:
        st.warning("The built-in supplier list is empty. Refresh the workspace data; if it stays empty, restart the API to reload the bundled company dataset.")
    else:
        st.caption(f"Showing {len(suppliers)} suppliers linked to this company's shipment dataset.")

    risk_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    shipment_by_id = {shipment.get("id"): shipment for shipment in shipments}
    supplier_risk, supplier_cases, route_risk = {}, {}, {}
    route_reliability: dict[str, list[float]] = {}
    for shipment in shipments:
        rid = shipment.get("route_id")
        if rid:
            route_reliability.setdefault(rid, []).append(float(shipment.get("reliability_score", 0.75) or 0.75))
    for event in open_events:
        shipment = shipment_by_id.get(event.get("shipment_id"), {})
        severity = str(event.get("risk_level", "HIGH")).upper()
        supplier_id = shipment.get("supplier_id")
        route_id = shipment.get("route_id")
        if supplier_id:
            supplier_cases[supplier_id] = supplier_cases.get(supplier_id, 0) + 1
            if risk_rank.get(severity, 0) > risk_rank.get(supplier_risk.get(supplier_id, "LOW"), 0):
                supplier_risk[supplier_id] = severity
        if route_id and risk_rank.get(severity, 0) > risk_rank.get(route_risk.get(route_id, "LOW"), 0):
            route_risk[route_id] = severity
    for supplier in suppliers:
        sid = supplier.get("id")
        supplier["open_disruptions"] = supplier_cases.get(sid, 0)
        base_score = float(supplier.get("risk_score", 0) or 0)
        base_risk = "LOW" if base_score >= 0.85 else "MEDIUM" if base_score >= 0.70 else "HIGH" if base_score >= 0.55 else "CRITICAL"
        supplier["active_risk"] = supplier_risk.get(sid, base_risk)
    for route in routes:
        scores = route_reliability.get(route.get("id"), [])
        reliability = sum(scores) / len(scores) if scores else 0.75
        base_route_risk = "LOW" if reliability >= 0.85 else "MEDIUM" if reliability >= 0.70 else "HIGH" if reliability >= 0.55 else "CRITICAL"
        route["risk_level"] = route_risk.get(route["id"], base_route_risk)

    if suppliers:
        high_risk = sum(1 for s in suppliers if s.get("active_risk") in {"HIGH", "CRITICAL"})
        med_risk  = sum(1 for s in suppliers if s.get("active_risk") == "MEDIUM")
        low_risk  = sum(1 for s in suppliers if s.get("active_risk") == "LOW")
        critical_routes = sum(1 for r in routes if r.get("risk_level") == "CRITICAL")

        m1, m2, m3, m4, m5 = st.columns(5)
        with m1: stat_card("Total Suppliers", str(len(suppliers)), "🏭", THEME["cyan"])
        with m2: stat_card("High Risk", str(high_risk), "🔴", THEME["red"])
        with m3: stat_card("Medium Risk", str(med_risk), "🟡", THEME["amber"])
        with m4: stat_card("Low Risk", str(low_risk), "🟢", THEME["green"])
        with m5: stat_card("Critical Routes", str(critical_routes), "⚠️", THEME["red"])

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.caption(f"Open disruption cases: {len(open_events)} · Their risk is reflected against linked suppliers and routes below.")
    sup_tab, route_tab = st.tabs([f"🏭 Suppliers ({len(suppliers)})", "🛳️ Trade Routes & Map"])
    with sup_tab:
        render_supplier_table(suppliers)
    with route_tab:
        render_route_map(routes, shipments)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Operations
# ══════════════════════════════════════════════════════════════════════════════
elif "⚙️" in page:
    section_header("Actions & History", "Review open risks, completed responses, and recorded notifications.", "⚙️")

    ops_notice = st.session_state.pop("ops_notice", None)
    if ops_notice:
        st.success(ops_notice)

    open_events = api_get("/disruptions", params={"status": "open", "limit": 200}) or []
    completed_events = api_get("/disruptions", params={"status": "mitigated", "limit": 200}) or []
    shipments = api_get("/shipments/live") or []
    activity = api_get("/activity", params={"limit": 100}) or []
    shipments_by_id = {shipment.get("id"): shipment for shipment in shipments}
    affected_ids = {event.get("shipment_id") for event in open_events}
    critical = sum(1 for event in open_events if str(event.get("risk_level", "")).upper() == "CRITICAL")

    metric_cols = st.columns(4)
    with metric_cols[0]: stat_card("Open cases", str(len(open_events)), "🚨", THEME["red"] if open_events else THEME["green"])
    with metric_cols[1]: stat_card("Critical cases", str(critical), "🔴", THEME["red"] if critical else THEME["green"])
    with metric_cols[2]: stat_card("Shipments affected", str(len(affected_ids)), "📦", THEME["amber"])
    with metric_cols[3]: stat_card("Completed responses", str(len(completed_events)), "✅", THEME["green"])

    scan_col, _ = st.columns([1, 4])
    if scan_col.button("🔍 Scan shipments", type="primary", use_container_width=True):
        with st.spinner("Checking the built-in shipment dataset for disruptions…"):
            scan = api_post("/disruptions/scan", timeout=60)
        if scan:
            st.session_state["ops_notice"] = (
                f"Scan complete: checked {scan.get('scanned_shipments', 0)} shipments; "
                f"found {scan.get('new_events', 0)} new risks. All pages now use the refreshed cases."
            )
            st.rerun()
        st.error("The scan could not be completed. Check the API connection.")

    needs_tab, completed_tab, activity_tab = st.tabs([
        f"Needs attention ({len(open_events)})",
        f"Resolved ({len(completed_events)})",
        f"Action history ({len(activity)})",
    ])
    with needs_tab:
        if open_events:
            for event in open_events:
                render_disruption_case(event, shipments_by_id.get(event.get("shipment_id"), {}), True, activity)
        else:
            empty_state("No open cases. Run a scan to check the current shipment dataset.", "✅")

    with completed_tab:
        if completed_events:
            for event in completed_events:
                render_disruption_case(event, shipments_by_id.get(event.get("shipment_id"), {}), False, activity)
        else:
            empty_state("Completed case responses will appear here.", "📋")

    with activity_tab:
        if activity:
            activity_df = pd.DataFrame(activity)
            friendly_action = {
                "threat_scan_completed": "Threat scan completed",
                "disruption_detected": "Risk identified",
                "disruption_mitigated": "Risk response recorded",
                "mitigation_executed": "Response action recorded",
                "critical_response_automated": "Critical response started",
                "critical_response_failed": "Critical response failed",
                "recipient_alert_sent": "Supplier/customer email sent",
                "recipient_alert_logged": "Supplier/customer email setup needed",
            }
            activity_df["action_type"] = activity_df["action_type"].map(friendly_action).fillna(
                activity_df["action_type"].astype(str).str.replace("_", " ").str.title()
            )
            activity_df["status"] = activity_df["status"].astype(str).str.title()
            activity_df = activity_df.rename(columns={
                "created_at": "When", "action_type": "Activity", "status": "Status",
                "summary": "What happened", "shipment_id": "Shipment", "actor": "Recorded by",
            })
            if "When" in activity_df.columns:
                activity_df["When"] = pd.to_datetime(activity_df["When"], errors="coerce").dt.strftime("%b %d, %Y  %H:%M")
            display_cols = [col for col in ["When", "Activity", "Status", "What happened", "Shipment", "Recorded by"] if col in activity_df]
            history_table = activity_df[display_cols]
            history_table.index = [""] * len(history_table)
            with st.container(height=520, border=True):
                st.table(history_table)
        else:
            empty_state("Actions and notifications will appear here after a scan or case response.", "📋")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Live Intelligence
# ══════════════════════════════════════════════════════════════════════════════
elif "📰" in page:
    section_header("Live Intelligence", "Regional headlines and workspace alerts that may affect your supply chain.", "📰")
    regions = {
        "Global": "global", "East Asia": "east-asia", "Europe": "europe",
        "North America": "north-america", "Southeast Asia": "southeast-asia",
        "Middle East": "middle-east", "South Asia": "south-asia",
    }
    region_cols = st.columns([2, 1, 3])
    with region_cols[0]:
        selected_region = st.selectbox("Region", list(regions), key="intel_region")
    with region_cols[1]:
        if st.button("↻ Refresh intelligence", use_container_width=True, key="refresh_intelligence"):
            st.rerun()
    with region_cols[2]:
        st.caption("Headlines are regional context. Confirm an event before changing shipment plans.")

    news_feed = api_get("/news/feed", params={"region": regions[selected_region]}) or {}
    news_items = news_feed.get("articles", []) if isinstance(news_feed, dict) else []
    news_status = news_feed.get("status", {}) if isinstance(news_feed, dict) else {}
    alert_rows = api_get("/alerts") or []
    if news_status.get("mode") == "live":
        st.success(f"Live NewsAPI.org feed · {news_status.get('message', 'Headlines loaded')}")
    elif news_status.get("mode") == "sample":
        st.warning(f"Sample intelligence is being shown. {news_status.get('message', 'Live headlines are unavailable.')}")
    else:
        st.info(news_status.get("message", "News feed status is not available."))
    news_col, alerts_col = st.columns([1.7, 1], gap="large")
    with news_col:
        st.markdown(f"#### Supply chain headlines · {selected_region}")
        if isinstance(news_items, list) and news_items:
            for item in news_items[:12]:
                severity = str(item.get("severity_hint", "INFO")).upper()
                badge_color = get_risk_color_local(severity)
                with st.container(border=True):
                    st.markdown(f"<span style='color:{badge_color};font-weight:700'>{severity}</span> · **{item.get('category', 'Industry update')}**", unsafe_allow_html=True)
                    st.markdown(f"**{item.get('headline', 'Untitled update')}**")
                    st.caption(f"{item.get('source', 'Source unavailable')} · {item.get('region', selected_region)} · {str(item.get('published_at', ''))[:19]}")
                    if item.get("url"):
                        st.markdown(f"[Open source article]({item['url']})")
        else:
            empty_state("No headlines are available for this region right now.", "🗞️")
        st.caption("Live headlines are sourced from NewsAPI.org. If the live service is unavailable, the status above identifies any sample headlines.")
    with alerts_col:
        st.markdown("#### Workspace alerts")
        if isinstance(alert_rows, list) and alert_rows:
            for alert in alert_rows[:10]:
                render_alert_card(str(alert.get("level", "INFO")).upper(), alert.get("message", ""), alert.get("timestamp", ""), alert.get("channel", "log"))
        else:
            st.info("No alerts are logged yet. Scan or respond to a disruption to add workspace activity.")
