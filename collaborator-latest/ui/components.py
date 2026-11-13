import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── Theme Palette ──────────────────────────────────────────────────────────────
THEME = {
    "bg":       "#0d1117",
    "card":     "#161b22",
    "border":   "#30363d",
    "cyan":     "#00d4ff",
    "blue":     "#0061ff",
    "green":    "#00c896",
    "amber":    "#ffb020",
    "red":      "#ff3b5c",
    "purple":   "#a855f7",
    "text":     "#e6edf3",
    "muted":    "#8b949e",
}

RISK_COLORS = {
    "LOW":      THEME["green"],
    "MEDIUM":   THEME["amber"],
    "HIGH":     "#ff6b35",
    "CRITICAL": THEME["red"],
    "UNKNOWN":  THEME["muted"],
}

def get_risk_color(risk: str) -> str:
    return RISK_COLORS.get(risk.upper(), THEME["muted"])

def load_premium_css():
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: {THEME['bg']};
            color: {THEME['text']};
        }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: {THEME['card']};
            border-right: 1px solid {THEME['border']};
        }}

        /* ── Main Content Area ── */
        .block-container {{
            padding-top: 1.5rem;
            max-width: 1400px;
        }}

        /* ── Metric Cards ── */
        [data-testid="stMetric"] {{
            background: {THEME['card']};
            border: 1px solid {THEME['border']};
            border-radius: 12px;
            padding: 1rem 1.25rem;
            transition: border-color 0.2s ease;
        }}
        [data-testid="stMetric"]:hover {{
            border-color: {THEME['cyan']};
        }}
        [data-testid="stMetricLabel"] {{ color: {THEME['muted']} !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }}
        [data-testid="stMetricValue"] {{ color: {THEME['text']} !important; font-size: 1.8rem !important; font-weight: 700 !important; }}

        /* ── Buttons ── */
        .stButton > button {{
            background: linear-gradient(135deg, {THEME['blue']} 0%, {THEME['cyan']} 100%);
            color: white !important;
            border: none !important;
            border-radius: 10px;
            padding: 0.65rem 1.4rem;
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(0, 97, 255, 0.35);
            width: 100%;
        }}
        .stButton > button:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.45);
            background: linear-gradient(135deg, {THEME['cyan']} 0%, {THEME['blue']} 100%);
        }}
        .stButton > button:active {{ transform: translateY(1px); }}
        .stButton > button p {{ color: white !important; font-weight: 700 !important; }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: {THEME['card']};
            border: 1px solid {THEME['border']};
            border-radius: 10px;
            padding: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            padding: 8px 18px;
            color: {THEME['muted']};
            font-weight: 500;
            font-size: 0.88rem;
            border: none;
            background: transparent;
        }}
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, {THEME['blue']}33, {THEME['cyan']}22) !important;
            color: {THEME['cyan']} !important;
            font-weight: 700 !important;
            border-bottom: 2px solid {THEME['cyan']} !important;
        }}

        /* ── Inputs ── */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div {{
            background: {THEME['card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 8px !important;
            color: {THEME['text']} !important;
            font-family: 'Inter', sans-serif !important;
        }}
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: {THEME['cyan']} !important;
            box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2) !important;
        }}

        /* ── Dataframe ── */
        [data-testid="stDataFrame"] {{
            border: 1px solid {THEME['border']};
            border-radius: 10px;
            overflow: hidden;
        }}

        /* ── Info / Warning / Error boxes ── */
        .stAlert {{
            border-radius: 10px !important;
            border-left-width: 4px !important;
        }}

        /* ── Divider ── */
        hr {{ border-color: {THEME['border']}; }}

        /* ── Headers ── */
        h1 {{ font-size: 1.9rem !important; font-weight: 800 !important; }}
        h2 {{ font-size: 1.4rem !important; font-weight: 700 !important; }}
        h3 {{ font-size: 1.1rem !important; font-weight: 600 !important; }}

        /* ── Spinner ── */
        .stSpinner > div {{ border-top-color: {THEME['cyan']} !important; }}

        /* ── Form Submit Button ── */
        .stFormSubmitButton > button {{
            background: linear-gradient(135deg, {THEME['purple']}, {THEME['blue']}) !important;
        }}
        </style>
    """, unsafe_allow_html=True)


# ── Component Helpers ──────────────────────────────────────────────────────────

def stat_card(label: str, value: str, icon: str, color: str):
    st.markdown(f"""
        <div style="background:{THEME['card']};border:1px solid {color}44;border-radius:14px;
                    padding:18px 20px;margin-bottom:12px;border-left:4px solid {color};
                    transition:all 0.2s ease;">
            <div style="color:{THEME['muted']};font-size:0.75rem;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:6px;">{icon} {label}</div>
            <div style="color:{color};font-size:1.9rem;font-weight:800;line-height:1;">{value}</div>
        </div>""", unsafe_allow_html=True)

def section_header(title: str, subtitle: str = ""):
    st.markdown(f"""
        <div style="margin-bottom:1.2rem;padding-bottom:0.8rem;border-bottom:1px solid {THEME['border']};">
            <h2 style="margin:0;color:{THEME['text']};">{title}</h2>
            {f'<p style="margin:4px 0 0;color:{THEME["muted"]};font-size:0.88rem;">{subtitle}</p>' if subtitle else ''}
        </div>""", unsafe_allow_html=True)

def render_risk_card(prediction: dict):
    try:
        risk = prediction.get("label", "UNKNOWN")
        color = get_risk_color(risk)
        dtype = prediction.get("disruption_type", "unknown").replace("_", " ").title()
        regions = ", ".join(prediction.get("affected_regions", []))
        duration = prediction.get("estimated_duration_days", 0)
        risk_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴", "UNKNOWN": "⚪"}
        icon = risk_icons.get(risk.upper(), "⚪")
        st.markdown(f"""
            <div style="background:{THEME['card']};border:2px solid {color};border-radius:14px;
                        padding:22px;margin-bottom:16px;position:relative;overflow:hidden;">
                <div style="position:absolute;top:0;right:0;width:80px;height:80px;
                            background:{color}15;border-radius:0 14px 0 80px;"></div>
                <div style="font-size:2.8rem;line-height:1;margin-bottom:8px;">{icon}</div>
                <div style="color:{color};font-size:1.6rem;font-weight:800;margin-bottom:10px;">{risk}</div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    <span style="background:{color}20;color:{color};padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">📋 {dtype}</span>
                    <span style="background:{THEME['blue']}20;color:{THEME['cyan']};padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">🌍 {regions or 'Global'}</span>
                    <span style="background:{THEME['purple']}20;color:{THEME['purple']};padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">⏱ {duration}d</span>
                </div>
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Risk card error: {e}")

def render_confidence_bar(confidence: float):
    pct = int(confidence * 100)
    color = THEME["green"] if pct >= 75 else THEME["amber"] if pct >= 50 else THEME["red"]
    st.markdown(f"""
        <div style="background:{THEME['card']};border:1px solid {THEME['border']};border-radius:10px;padding:14px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="color:{THEME['muted']};font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Model Confidence</span>
                <span style="color:{color};font-weight:800;font-size:1rem;">{pct}%</span>
            </div>
            <div style="background:{THEME['border']};border-radius:4px;height:8px;">
                <div style="background:linear-gradient(90deg,{color},{color}aa);width:{pct}%;height:8px;border-radius:4px;transition:width 0.6s ease;"></div>
            </div>
        </div>""", unsafe_allow_html=True)

def render_llm_summary(plan: dict):
    summary = plan.get("llm_summary")
    generated_by = plan.get("generated_by", "rule-engine")
    if summary:
        badge = "🤖 Gemini AI" if "gemini" in generated_by else "⚙️ Rule Engine"
        badge_color = THEME["purple"] if "gemini" in generated_by else THEME["muted"]
        st.markdown(f"""
            <div style="background:linear-gradient(135deg,{THEME['purple']}15,{THEME['blue']}10);
                        border:1px solid {THEME['purple']}44;border-left:4px solid {THEME['purple']};
                        border-radius:10px;padding:16px;margin-bottom:14px;">
                <div style="color:{badge_color};font-size:0.72rem;font-weight:700;
                            text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">{badge} — Executive Summary</div>
                <p style="margin:0;font-size:0.92rem;color:{THEME['text']};font-style:italic;line-height:1.6;">"{summary}"</p>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption(f"⚙️ Rule Engine active. Add `GEMINI_API_KEY` to `.env` to enable AI summaries.")

def render_action_checklist(actions: list, title: str, uid: str = ""):
    if not actions:
        st.markdown(f"<p style='color:{THEME['muted']};font-size:0.88rem;'>No actions for this phase.</p>", unsafe_allow_html=True)
        return
    for i, act in enumerate(actions):
        st.checkbox(act, key=f"chk_{uid}_{title}_{i}_{act[:20]}")

def render_prevention_plan(plan: dict, uid: str = ""):
    try:
        priority = plan.get("priority", "P3")
        cost = plan.get("estimated_cost_impact", "Unknown")
        p_colors = {"P1": THEME["red"], "P2": THEME["amber"], "P3": THEME["green"]}
        p_color = p_colors.get(priority, THEME["muted"])

        st.markdown(f"""
            <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
                <span style="background:{p_color}22;color:{p_color};padding:6px 16px;border-radius:20px;font-weight:700;font-size:0.88rem;border:1px solid {p_color}55;">
                    🚨 Priority {priority}
                </span>
                <span style="background:{THEME['cyan']}15;color:{THEME['cyan']};padding:6px 16px;border-radius:20px;font-weight:600;font-size:0.88rem;border:1px solid {THEME['cyan']}44;">
                    💰 {cost}
                </span>
            </div>""", unsafe_allow_html=True)

        render_llm_summary(plan)

        t1, t2, t3 = st.tabs(["⚡ Immediate (1h)", "⏱️ Short-term (24h)", "📅 Long-term (1w)"])
        with t1: render_action_checklist(plan.get("immediate_actions", []), "imm", uid)
        with t2: render_action_checklist(plan.get("short_term_actions", []), "st", uid)
        with t3: render_action_checklist(plan.get("long_term_actions", []), "lt", uid)

        inv = plan.get("inventory_recommendations", [])
        if inv:
            st.markdown(f"<div style='margin-top:12px;font-size:0.85rem;font-weight:700;color:{THEME['cyan']};'>📦 Inventory</div>", unsafe_allow_html=True)
            for r in inv: st.caption(f"→ {r}")

        alts = plan.get("supplier_alternatives", [])
        if alts:
            st.markdown(f"<div style='margin-top:12px;font-size:0.85rem;font-weight:700;color:{THEME['green']};'>🔄 Alternate Suppliers</div>", unsafe_allow_html=True)
            for alt in alts:
                n = alt.get("name", alt) if isinstance(alt, dict) else alt
                c = alt.get("country", "") if isinstance(alt, dict) else ""
                t = alt.get("tier", "") if isinstance(alt, dict) else ""
                st.caption(f"→ {n} · {c} · Tier {t}")
    except Exception as e:
        st.error(f"Plan render error: {e}")

def render_route_map(routes: list, shipments: list = None):
    try:
        from utils.geo_coords import HUB_COORDS
        import plotly.graph_objects as go
        
        if not routes:
            st.warning("No routes found for mapping.")
            return
            
        fig = go.Figure()
        
        # 1. Draw Routes as Arcs/Lines
        for r in routes:
            origin = r.get("origin_city", "Unknown")
            dest = r.get("dest_city", "Unknown")
            risk = r.get("risk_level", "LOW")
            color = get_risk_color(risk)
            
            o_coords = HUB_COORDS.get(origin)
            d_coords = HUB_COORDS.get(dest)
            
            if o_coords and d_coords:
                fig.add_trace(go.Scattergeo(
                    locationmode = 'ISO-3',
                    lon = [o_coords['lon'], d_coords['lon']],
                    lat = [o_coords['lat'], d_coords['lat']],
                    mode = 'lines',
                    line = dict(width = 2, color = color),
                    opacity = 0.6,
                    name = f"{r.get('id')}: {origin} → {dest}",
                    hoverinfo = 'text',
                    text = f"Route: {r.get('id')}<br>Status: {risk}<br>Avg Delay: {r.get('avg_delay_days')}d"
                ))

        # 2. Draw Active Shipments as pulsing dots if provided
        if shipments:
            ship_lats = []
            ship_lons = []
            ship_text = []
            ship_colors = []
            for s in shipments:
                if s.get("status") == "Delivered": continue
                # Place shipment at a rough midpoint for visualization
                o = HUB_COORDS.get(s.get("origin"))
                d = HUB_COORDS.get(s.get("destination"))
                if o and d:
                    # Move 30% along the path for "In Transit"
                    frac = 0.3 if s.get("status") == "In Transit" else 0.1
                    lat = o['lat'] + (d['lat'] - o['lat']) * frac
                    lon = o['lon'] + (d['lon'] - o['lon']) * frac
                    ship_lats.append(lat)
                    ship_lons.append(lon)
                    ship_colors.append(THEME["cyan"])
                    ship_text.append(f"Shipment: {s.get('id')}<br>SKU: {s.get('sku')}<br>Value: ${s.get('value_usd'):,}")

            fig.add_trace(go.Scattergeo(
                lon = ship_lons, lat = ship_lats,
                mode = 'markers',
                marker = dict(size = 10, color = ship_colors, symbol = 'triangle-right',
                             line = dict(width=1, color='white')),
                name = 'Active Shipments',
                text = ship_text, hoverinfo = 'text'
            ))

        fig.update_layout(
            title_text = 'Global Supply Chain Network & Active Risk Zones',
            showlegend = False,
            geo = dict(
                showland = True, landcolor = THEME["card"],
                showocean = True, oceancolor = THEME["bg"],
                showcountries = True, countrycolor = THEME["border"],
                projection_type = 'equirectangular',
                bgcolor = "rgba(0,0,0,0)"
            ),
            margin = dict(l=0, r=0, t=40, b=0),
            height = 500,
            paper_bgcolor = "rgba(0,0,0,0)",
            plot_bgcolor = "rgba(0,0,0,0)",
            font = dict(color = THEME["text"])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Also show the table below for detail
        df = pd.DataFrame([r if isinstance(r, dict) else r.__dict__ for r in routes])
        def highlight_risk(val):
            c = get_risk_color(str(val))
            return f"background-color:{c}25;color:{c};font-weight:700;"
        st.dataframe(df.style.map(highlight_risk, subset=["risk_level"]), use_container_width=True)
        
    except Exception as e:
        st.error(f"Route map render error: {e}")

def render_supplier_table(suppliers: list):
    try:
        if not suppliers:
            st.warning("No suppliers found.")
            return
        df = pd.DataFrame([s if isinstance(s, dict) else s.__dict__ for s in suppliers])
        if "product_categories" in df.columns:
            df["product_categories"] = df["product_categories"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

        def highlight_risk(val):
            if val >= 0.7: return f"background-color:{THEME['red']}25;color:{THEME['red']};font-weight:700;"
            elif val >= 0.4: return f"background-color:{THEME['amber']}25;color:{THEME['amber']};font-weight:700;"
            return f"background-color:{THEME['green']}25;color:{THEME['green']};"

        st.dataframe(df.style.map(highlight_risk, subset=["risk_score"]), use_container_width=True)
    except Exception as e:
        st.error(f"Supplier render error: {e}")

def render_alert_card(level: str, message: str, timestamp: str = "", channel: str = "log"):
    colors = {"INFO": THEME["blue"], "WARNING": THEME["amber"], "CRITICAL": THEME["red"], "EMERGENCY": "#cc00ff"}
    icons  = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨", "EMERGENCY": "🔴"}
    ch_icons = {"slack": "💬", "email": "📧", "log": "📋"}
    color = colors.get(level, THEME["muted"])
    icon  = icons.get(level, "📢")
    ch_icon = ch_icons.get(channel.split(",")[0], "📋")
    st.markdown(f"""
        <div style="background:{THEME['card']};border:1px solid {color}44;border-left:4px solid {color};
                    border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:flex-start;gap:12px;">
            <span style="font-size:1.3rem;">{icon}</span>
            <div style="flex:1;min-width:0;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="color:{color};font-weight:700;font-size:0.82rem;text-transform:uppercase;">{level}</span>
                    <span style="color:{THEME['muted']};font-size:0.72rem;">{ch_icon} {timestamp[:19] if timestamp else ''}</span>
                </div>
                <div style="color:{THEME['text']};font-size:0.85rem;line-height:1.5;word-break:break-word;">{message[:200]}</div>
            </div>
        </div>""", unsafe_allow_html=True)

def render_health_badge(status: str):
    ok = status == "healthy"
    color = THEME["green"] if ok else THEME["red"]
    label = "● HEALTHY" if ok else "● DEGRADED"
    st.markdown(f"""
        <div style="display:inline-flex;align-items:center;gap:8px;background:{color}18;
                    border:1px solid {color}55;border-radius:20px;padding:6px 16px;margin-bottom:12px;">
            <span style="color:{color};font-weight:800;font-size:0.85rem;">{label}</span>
        </div>""", unsafe_allow_html=True)

def render_donut_chart(stats: dict):
    try:
        labels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        values = [stats.get(l, 0) for l in labels]
        colors = [THEME["green"], THEME["amber"], "#ff6b35", THEME["red"]]
        if sum(values) == 0:
            st.caption("No predictions logged yet.")
            return
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.65,
            marker=dict(colors=colors, line=dict(color=THEME["bg"], width=3)),
            textinfo="label+percent", textfont=dict(color=THEME["text"], size=12)
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=240, margin=dict(l=0, r=0, t=10, b=0),
            font=dict(family="Inter", color=THEME["text"])
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption(f"Chart error: {e}")
