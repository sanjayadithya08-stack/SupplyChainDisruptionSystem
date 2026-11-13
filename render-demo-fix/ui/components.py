import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── Dark Theme Palette ─────────────────────────────────────────────────────────
THEME = {
    "bg":       "#0d1117",
    "bg2":      "#161b22",
    "card":     "#1c2333",
    "card2":    "#21262d",
    "border":   "#30363d",
    "border2":  "#3d444d",
    "cyan":     "#38bdf8",
    "blue":     "#3b82f6",
    "green":    "#22c55e",
    "amber":    "#f59e0b",
    "red":      "#ef4444",
    "purple":   "#a855f7",
    "orange":   "#f97316",
    "pink":     "#ec4899",
    "text":     "#e6edf3",
    "text2":    "#c9d1d9",
    "muted":    "#7d8590",
    "accent":   "#1f6feb",
    "glow_cyan":  "rgba(56,189,248,0.12)",
    "glow_green": "rgba(34,197,94,0.12)",
    "glow_red":   "rgba(239,68,68,0.12)",
    "glow_amber": "rgba(245,158,11,0.12)",
}

RISK_COLORS = {
    "LOW":      THEME["green"],
    "MEDIUM":   THEME["amber"],
    "HIGH":     THEME["orange"],
    "CRITICAL": THEME["red"],
    "UNKNOWN":  THEME["muted"],
}

RISK_GLOW = {
    "LOW":      THEME["glow_green"],
    "MEDIUM":   THEME["glow_amber"],
    "HIGH":     "rgba(249,115,22,0.12)",
    "CRITICAL": THEME["glow_red"],
    "UNKNOWN":  "rgba(125,133,144,0.08)",
}

DISRUPTION_COLORS = {
    "normal":     THEME["green"],
    "port_strike":THEME["amber"],
    "weather":    THEME["blue"],
    "war":        THEME["red"],
    "cyber":      THEME["purple"],
    "supplier":   THEME["orange"],
    "logistics":  THEME["cyan"],
    "customs":    "#fbbf24",
}

def get_risk_color(risk: str) -> str:
    return RISK_COLORS.get(str(risk).upper(), THEME["muted"])

def get_risk_glow(risk: str) -> str:
    return RISK_GLOW.get(str(risk).upper(), "rgba(125,133,144,0.08)")

def load_premium_css():
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* ── Global Reset ── */
        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: {THEME['bg']} !important;
            color: {THEME['text']} !important;
        }}

        /* ── Main Content ── */
        .main .block-container {{
            padding: 1rem 2rem 2rem 2rem !important;
            max-width: 1500px !important;
            background-color: {THEME['bg']} !important;
        }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: {THEME['bg2']} !important;
            border-right: 1px solid {THEME['border']} !important;
            min-width: 220px !important;
        }}
        [data-testid="stSidebar"] > div {{
            background: {THEME['bg2']} !important;
        }}
        [data-testid="stSidebarNav"] {{
            display: none;
        }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
            background: {THEME['card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            padding: 4px !important;
            gap: 2px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 7px !important;
            padding: 7px 14px !important;
            color: {THEME['muted']} !important;
            font-weight: 500 !important;
            font-size: 0.84rem !important;
            border: none !important;
            background: transparent !important;
            transition: all 0.2s !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: {THEME['accent']}22 !important;
            color: {THEME['cyan']} !important;
            font-weight: 700 !important;
        }}

        /* ── Buttons ── */
        .stButton > button {{
            background: linear-gradient(135deg, {THEME['accent']}, {THEME['blue']}) !important;
            color: {THEME['text']} !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1.2rem !important;
            font-size: 0.87rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 0 0 0 rgba(59,130,246,0) !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 20px rgba(59,130,246,0.35) !important;
        }}
        .stButton > button:active {{
            transform: translateY(0px) !important;
        }}
        .stButton > button p {{
            color: {THEME['text']} !important;
            font-weight: 600 !important;
        }}

        /* ── Form Submit ── */
        .stFormSubmitButton > button {{
            background: linear-gradient(135deg, {THEME['accent']}, {THEME['blue']}) !important;
            color: {THEME['text']} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}
        .stFormSubmitButton > button p {{
            color: {THEME['text']} !important;
        }}

        /* ── Inputs / Selects ── */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input {{
            background: {THEME['card2']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 7px !important;
            color: {THEME['text']} !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.88rem !important;
        }}
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: {THEME['cyan']} !important;
            box-shadow: 0 0 0 2px rgba(56,189,248,0.18) !important;
        }}
        .stSelectbox [data-baseweb="select"] > div,
        .stSelectbox [data-baseweb="select"] {{
            background: {THEME['card2']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 7px !important;
            color: {THEME['text']} !important;
        }}
        [data-baseweb="popover"] {{
            background: {THEME['card']} !important;
        }}
        [data-baseweb="menu"] {{
            background: {THEME['card']} !important;
            border: 1px solid {THEME['border']} !important;
        }}
        [data-baseweb="option"]:hover {{
            background: {THEME['card2']} !important;
        }}
        [data-baseweb="option"][aria-selected="true"] {{
            background: {THEME['accent']}33 !important;
        }}

        /* ── Metrics ── */
        [data-testid="stMetric"] {{
            background: {THEME['card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 12px !important;
            padding: 1rem 1.25rem !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {THEME['muted']} !important;
            font-size: 0.75rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.07em !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {THEME['text']} !important;
            font-size: 1.7rem !important;
            font-weight: 700 !important;
        }}

        /* ── Dataframe / Table ── */
        [data-testid="stDataFrame"] {{
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            overflow: hidden !important;
        }}
        .dvn-scroller {{
            background: {THEME['card']} !important;
        }}

        /* ── Expander ── */
        [data-testid="stExpander"] {{
            background: {THEME['card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
        }}
        [data-testid="stExpander"] summary {{
            font-weight: 600 !important;
            color: {THEME['text2']} !important;
        }}

        /* ── Alerts / Info boxes ── */
        .stAlert {{
            background: {THEME['card']} !important;
            border-radius: 8px !important;
            border-left-width: 4px !important;
        }}

        /* ── Progress bars ── */
        .stProgress > div > div > div > div {{
            background: linear-gradient(90deg, {THEME['cyan']}, {THEME['blue']}) !important;
        }}

        /* ── Checkboxes ── */
        [data-testid="stCheckbox"] label {{
            color: {THEME['text2']} !important;
            font-size: 0.88rem !important;
        }}

        /* ── Spinner ── */
        .stSpinner > div {{
            border-top-color: {THEME['cyan']} !important;
        }}

        /* ── Caption / small text ── */
        .stCaption {{
            color: {THEME['muted']} !important;
        }}

        /* ── Divider ── */
        hr {{ border-color: {THEME['border']} !important; }}

        /* ── Scrollbar ── */
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: {THEME['bg']}; }}
        ::-webkit-scrollbar-thumb {{ background: {THEME['border2']}; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {THEME['muted']}; }}

        /* ── Radio buttons (sidebar nav) ── */
        [data-testid="stRadio"] > div {{
            gap: 4px !important;
        }}
        [data-testid="stRadio"] label {{
            background: transparent !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            cursor: pointer !important;
            transition: all 0.15s !important;
            color: {THEME['muted']} !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
        }}
        [data-testid="stRadio"] label:hover {{
            background: {THEME['card2']} !important;
            color: {THEME['text']} !important;
        }}
        [data-testid="stRadio"] [aria-checked="true"] + label,
        [data-testid="stRadio"] label:has(input:checked) {{
            background: {THEME['accent']}22 !important;
            color: {THEME['cyan']} !important;
            font-weight: 600 !important;
        }}
        /* Hide radio circles */
        [data-testid="stRadio"] [data-testid="stWidgetLabel"] {{
            display: none !important;
        }}
        [data-testid="stRadio"] input[type="radio"] {{
            display: none !important;
        }}

        </style>
    """, unsafe_allow_html=True)


# ── Component Library ──────────────────────────────────────────────────────────

def stat_card(label: str, value: str, icon: str, color: str, subtitle: str = ""):
    glow = f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.1)" if color.startswith('#') else "rgba(56,189,248,0.1)"
    st.markdown(f"""
        <div style="background:{THEME['card']};border:1px solid {THEME['border']};border-top:3px solid {color};
                    border-radius:12px;padding:18px 20px;margin-bottom:8px;
                    box-shadow:0 4px 20px {glow};
                    transition:all 0.25s ease;position:relative;overflow:hidden;">
            <div style="position:absolute;right:14px;top:14px;font-size:1.5rem;opacity:0.25;">{icon}</div>
            <div style="color:{THEME['muted']};font-size:0.7rem;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:10px;font-weight:600;">{label}</div>
            <div style="color:{color};font-size:2rem;font-weight:800;line-height:1;letter-spacing:-0.02em;">{value}</div>
            {f'<div style="color:{THEME["muted"]};font-size:0.72rem;margin-top:6px;">{subtitle}</div>' if subtitle else ''}
        </div>""", unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "", icon: str = ""):
    st.markdown(f"""
        <div style="margin:0.5rem 0 1.2rem;padding:0 0 0.8rem;border-bottom:1px solid {THEME['border']};">
            <div style="display:flex;align-items:center;gap:10px;">
                {f'<span style="font-size:1.3rem;">{icon}</span>' if icon else ''}
                <h2 style="margin:0;color:{THEME['text']};font-size:1.25rem;font-weight:700;letter-spacing:-0.01em;">{title}</h2>
            </div>
            {f'<p style="margin:4px 0 0;color:{THEME["muted"]};font-size:0.82rem;line-height:1.5;">{subtitle}</p>' if subtitle else ''}
        </div>""", unsafe_allow_html=True)


def risk_badge(risk: str) -> str:
    color = get_risk_color(risk)
    icons = {"LOW": "●", "MEDIUM": "◆", "HIGH": "▲", "CRITICAL": "⬟"}
    icon = icons.get(risk.upper(), "●")
    return f'<span style="background:{color}20;color:{color};padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;letter-spacing:0.06em;border:1px solid {color}40;">{icon} {risk}</span>'


def status_badge(status: str) -> str:
    colors = {
        "In Transit": THEME["cyan"],
        "Delayed": THEME["red"],
        "Pending": THEME["amber"],
        "Delivered": THEME["green"],
    }
    color = colors.get(status, THEME["muted"])
    dots = {"In Transit": "●", "Delayed": "⚠", "Pending": "⏳", "Delivered": "✓"}
    dot = dots.get(status, "●")
    return f'<span style="background:{color}20;color:{color};padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;border:1px solid {color}40;">{dot} {status}</span>'


def empty_state(message: str, icon: str = "📭"):
    st.markdown(f"""
        <div style="text-align:center;padding:48px 24px;color:{THEME['muted']};">
            <div style="font-size:2.8rem;margin-bottom:12px;">{icon}</div>
            <div style="font-size:0.92rem;font-weight:500;">{message}</div>
        </div>""", unsafe_allow_html=True)


def render_risk_card(prediction: dict):
    try:
        risk = prediction.get("label", "UNKNOWN")
        color = get_risk_color(risk)
        glow = get_risk_glow(risk)
        dtype = prediction.get("disruption_type", "unknown").replace("_", " ").title()
        regions = ", ".join(prediction.get("affected_regions", []))
        duration = prediction.get("estimated_duration_days", 0)
        risk_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
        icon = risk_icons.get(risk.upper(), "⚪")
        st.markdown(f"""
            <div style="background:{THEME['card']};border:1px solid {color}44;border-left:4px solid {color};
                        border-radius:12px;padding:20px;margin-bottom:16px;
                        box-shadow:0 4px 24px {glow};">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                    <span style="font-size:2rem;">{icon}</span>
                    <div>
                        <div style="color:{color};font-size:1.2rem;font-weight:800;letter-spacing:-0.01em;">{risk} RISK</div>
                        <div style="color:{THEME['muted']};font-size:0.78rem;margin-top:2px;">AI Prediction</div>
                    </div>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    <span style="background:{color}18;color:{color};padding:4px 12px;border-radius:20px;font-size:0.78rem;font-weight:600;border:1px solid {color}33;">📋 {dtype}</span>
                    <span style="background:{THEME['cyan']}15;color:{THEME['cyan']};padding:4px 12px;border-radius:20px;font-size:0.78rem;font-weight:600;border:1px solid {THEME['cyan']}30;">🌍 {regions or 'Global'}</span>
                    <span style="background:{THEME['purple']}15;color:{THEME['purple']};padding:4px 12px;border-radius:20px;font-size:0.78rem;font-weight:600;border:1px solid {THEME['purple']}30;">⏱ {duration}d est.</span>
                </div>
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Risk card error: {e}")


def render_confidence_bar(confidence: float):
    pct = int(confidence * 100)
    color = THEME["green"] if pct >= 75 else THEME["amber"] if pct >= 50 else THEME["red"]
    label = "High Confidence" if pct >= 75 else "Medium Confidence" if pct >= 50 else "Low Confidence"
    st.markdown(f"""
        <div style="background:{THEME['card']};border:1px solid {THEME['border']};border-radius:10px;padding:14px 16px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="color:{THEME['muted']};font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;">Prediction Confidence</span>
                <span style="color:{color};font-weight:700;font-size:0.9rem;">{pct}% — {label}</span>
            </div>
            <div style="background:{THEME['border']};border-radius:6px;height:6px;overflow:hidden;">
                <div style="background:linear-gradient(90deg,{color},{color}bb);width:{pct}%;height:6px;border-radius:6px;transition:width 0.6s ease;"></div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_llm_summary(plan: dict):
    summary = plan.get("llm_summary")
    generated_by = plan.get("generated_by", "rule-engine")
    if summary:
        is_ai = "gemini" in str(generated_by).lower()
        badge = "🤖 Gemini AI Summary" if is_ai else "⚙️ Rule-Based Summary"
        badge_color = THEME["purple"] if is_ai else THEME["muted"]
        st.markdown(f"""
            <div style="background:{badge_color}10;border:1px solid {badge_color}30;border-left:3px solid {badge_color};
                        border-radius:8px;padding:14px 16px;margin-bottom:14px;">
                <div style="color:{badge_color};font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">{badge}</div>
                <p style="margin:0;font-size:0.88rem;color:{THEME['text2']};line-height:1.65;font-style:italic;">"{summary}"</p>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption("⚙️ Rule engine active. Add `GEMINI_API_KEY` to `.env` for AI summaries.")


def render_action_checklist(actions: list, title: str, uid: str = ""):
    if not actions:
        st.markdown(f"<p style='color:{THEME['muted']};font-size:0.85rem;font-style:italic;'>No actions required for this phase.</p>", unsafe_allow_html=True)
        return
    for i, act in enumerate(actions):
        st.checkbox(act, key=f"chk_{uid}_{title}_{i}_{str(act)[:20]}")


def render_prevention_plan(plan: dict, uid: str = ""):
    try:
        priority = plan.get("priority", "P3")
        cost = plan.get("estimated_cost_impact", "Unknown")
        p_colors = {"P1": THEME["red"], "P2": THEME["amber"], "P3": THEME["green"]}
        p_color = p_colors.get(priority, THEME["muted"])
        priority_labels = {"P1": "P1 · Critical — Act Immediately", "P2": "P2 · High — Act within 24h", "P3": "P3 · Standard — Monitor"}
        priority_label = priority_labels.get(priority, priority)

        st.markdown(f"""
            <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">
                <span style="background:{p_color}18;color:{p_color};padding:5px 14px;border-radius:20px;font-weight:700;font-size:0.8rem;border:1px solid {p_color}40;">🚨 {priority_label}</span>
                <span style="background:{THEME['cyan']}12;color:{THEME['cyan']};padding:5px 14px;border-radius:20px;font-weight:600;font-size:0.8rem;border:1px solid {THEME['cyan']}30;">💰 {cost}</span>
            </div>""", unsafe_allow_html=True)

        render_llm_summary(plan)

        t1, t2, t3 = st.tabs(["⚡ Immediate (1h)", "📅 Short-term (24h)", "🗓️ Long-term (1 week)"])
        with t1: render_action_checklist(plan.get("immediate_actions", []), "imm", uid)
        with t2: render_action_checklist(plan.get("short_term_actions", []), "st", uid)
        with t3: render_action_checklist(plan.get("long_term_actions", []), "lt", uid)

        inv = plan.get("inventory_recommendations", [])
        if inv:
            st.markdown(f"<div style='margin-top:12px;font-size:0.82rem;font-weight:700;color:{THEME['cyan']};margin-bottom:6px;'>📦 Inventory Actions</div>", unsafe_allow_html=True)
            for r in inv:
                st.markdown(f"<div style='color:{THEME['text2']};font-size:0.84rem;padding:4px 0;border-bottom:1px solid {THEME['border']};'>→ {r}</div>", unsafe_allow_html=True)

        alts = plan.get("supplier_alternatives", [])
        if alts:
            st.markdown(f"<div style='margin-top:12px;font-size:0.82rem;font-weight:700;color:{THEME['green']};margin-bottom:6px;'>🔄 Alternative Suppliers</div>", unsafe_allow_html=True)
            for alt in alts:
                n = alt.get("name", alt) if isinstance(alt, dict) else alt
                c = alt.get("country", "") if isinstance(alt, dict) else ""
                t = alt.get("tier", "") if isinstance(alt, dict) else ""
                st.markdown(f"<div style='color:{THEME['text2']};font-size:0.84rem;padding:4px 0;'>→ {n} · {c} · Tier {t}</div>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Plan render error: {e}")


def render_route_map(routes: list, shipments: list = None):
    try:
        from utils.geo_coords import HUB_COORDS

        if not routes:
            empty_state("No routes found for mapping.", "🗺️")
            return

        fig = go.Figure()

        for r in routes:
            origin = r.get("origin_city", r.get("origin", "Unknown"))
            dest = r.get("dest_city", r.get("destination", "Unknown"))
            risk = r.get("risk_level", "LOW")
            color = get_risk_color(risk)
            o_coords = HUB_COORDS.get(origin)
            d_coords = HUB_COORDS.get(dest)
            if o_coords and d_coords:
                fig.add_trace(go.Scattergeo(
                    locationmode='ISO-3',
                    lon=[o_coords['lon'], d_coords['lon']],
                    lat=[o_coords['lat'], d_coords['lat']],
                    mode='lines',
                    line=dict(width=2.5, color=color),
                    opacity=0.75,
                    name=f"{r.get('id')}: {origin} → {dest}",
                    hoverinfo='text',
                    text=f"Route: {r.get('id')}<br>Risk: {risk}<br>{origin} → {dest}"
                ))

        if shipments:
            ship_lats, ship_lons, ship_text, ship_colors = [], [], [], []
            for s in shipments:
                if s.get("status") == "Delivered":
                    continue
                o = HUB_COORDS.get(s.get("origin"))
                d = HUB_COORDS.get(s.get("destination"))
                if o and d:
                    frac = 0.3 if s.get("status") == "In Transit" else 0.1
                    ship_lats.append(o['lat'] + (d['lat'] - o['lat']) * frac)
                    ship_lons.append(o['lon'] + (d['lon'] - o['lon']) * frac)
                    ship_text.append(f"Shipment: {s.get('id')}<br>SKU: {s.get('sku')}<br>Value: ${s.get('value_usd', 0):,.0f}")
                    ship_colors.append(THEME["cyan"])
            if ship_lats:
                fig.add_trace(go.Scattergeo(
                    lon=ship_lons, lat=ship_lats,
                    mode='markers',
                    marker=dict(size=9, color=THEME["cyan"], symbol='triangle-right', line=dict(width=1, color='white')),
                    name='Active Shipments',
                    text=ship_text, hoverinfo='text'
                ))

        fig.update_layout(
            showlegend=False,
            geo=dict(
                showland=True, landcolor="#1a2332",
                showocean=True, oceancolor="#0d1b2a",
                showcountries=True, countrycolor="#2d3748",
                showlakes=True, lakecolor="#0d1b2a",
                projection_type='equirectangular',
                bgcolor="rgba(0,0,0,0)",
                showcoastlines=True, coastlinecolor="#2d3748",
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=THEME["text2"], family="Inter")
        )

        st.plotly_chart(fig, use_container_width=True)

        df = pd.DataFrame(routes)
        if not df.empty:
            display_cols = [c for c in ["id", "origin", "destination", "via_ports", "carrier", "transit_days", "risk_level"] if c in df.columns]
            table = df[display_cols].rename(columns={
                "id": "Route ID", "origin": "Origin", "destination": "Destination",
                "via_ports": "Via", "carrier": "Carrier", "transit_days": "Transit days",
                "risk_level": "Risk",
            })
            table.index = [""] * len(table)
            st.table(table)

    except Exception as e:
        st.error(f"Route map render error: {e}")


def render_supplier_table(suppliers: list):
    try:
        if not suppliers:
            empty_state("No suppliers found.", "🏭")
            return
        df = pd.DataFrame([s if isinstance(s, dict) else vars(s) for s in suppliers])
        if "product_categories" in df.columns:
            df["product_categories"] = df["product_categories"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        keep = [c for c in ["name", "country", "active_risk", "open_disruptions", "product_categories", "tier"] if c in df.columns]
        df = df[keep]
        df = df.rename(columns={
            "name": "Supplier", "country": "Country", "active_risk": "Live risk",
            "open_disruptions": "Open cases", "product_categories": "Products", "tier": "Tier",
        })

        df.index = [""] * len(df)
        with st.container(height=min(680, max(220, 42 + 38 * len(df))), border=True):
            st.table(df)
    except Exception as e:
        st.error(f"Supplier render error: {e}")


def render_alert_card(level: str, message: str, timestamp: str = "", channel: str = "log"):
    colors = {"INFO": THEME["blue"], "WARNING": THEME["amber"], "CRITICAL": THEME["red"], "EMERGENCY": THEME["purple"]}
    icons  = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨", "EMERGENCY": "🔴"}
    ch_icons = {"slack": "💬", "email": "📧", "log": "📋"}
    color = colors.get(level, THEME["muted"])
    icon  = icons.get(level, "📢")
    ch_icon = ch_icons.get(str(channel).split(",")[0], "📋")
    st.markdown(f"""
        <div style="background:{THEME['card']};border:1px solid {THEME['border']};border-left:3px solid {color};
                    border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:flex-start;gap:12px;">
            <span style="font-size:1.1rem;margin-top:1px;">{icon}</span>
            <div style="flex:1;min-width:0;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="background:{color}20;color:{color};padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:700;letter-spacing:0.05em;">{level}</span>
                    <span style="color:{THEME['muted']};font-size:0.7rem;">{ch_icon} {str(timestamp)[:19]}</span>
                </div>
                <div style="color:{THEME['text2']};font-size:0.84rem;line-height:1.5;word-break:break-word;">{str(message)[:250]}</div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_health_badge(status: str):
    ok = status == "healthy"
    color = THEME["green"] if ok else THEME["red"]
    label = "ONLINE" if ok else "DEGRADED"
    st.markdown(f"""
        <div style="display:inline-flex;align-items:center;gap:6px;background:{color}15;
                    border:1px solid {color}40;border-radius:20px;padding:5px 14px;margin-bottom:12px;">
            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{color};animation:pulse 2s infinite;"></span>
            <span style="color:{color};font-weight:700;font-size:0.78rem;letter-spacing:0.06em;">{label}</span>
        </div>""", unsafe_allow_html=True)


def render_donut_chart(stats: dict):
    try:
        labels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        values = [stats.get(l, 0) for l in labels]
        colors = [THEME["green"], THEME["amber"], THEME["orange"], THEME["red"]]
        if sum(values) == 0:
            empty_state("No predictions logged yet.", "📊")
            return
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.65,
            marker=dict(colors=colors, line=dict(color=THEME["bg"], width=3)),
            textinfo="label+percent",
            textfont=dict(color=THEME["text2"], size=12, family="Inter")
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=240,
            margin=dict(l=0, r=0, t=10, b=0),
            font=dict(family="Inter", color=THEME["text2"])
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption(f"Chart error: {e}")
