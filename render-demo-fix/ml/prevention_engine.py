"""
Upgrade 2: LLM-Enhanced Prevention Engine using Google Gemini.
Falls back to rule-based generation if no API key.
"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

_GEMINI_MODEL = None

def _get_model():
    global _GEMINI_MODEL
    if _GEMINI_MODEL:
        return _GEMINI_MODEL
    key = Config.GEMINI_API_KEY
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        _GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
        print("[Gemini] LLM engine loaded successfully.")
        return _GEMINI_MODEL
    except Exception as e:
        print(f"[Gemini] Could not load model: {e}")
        return None

def _llm_prevention_plan(prediction: dict) -> dict | None:
    """Ask Gemini to generate a detailed, context-aware prevention plan."""
    model = _get_model()
    if not model:
        return None
    try:
        disruption_type = prediction.get("disruption_type", "unknown")
        label = prediction.get("label", "LOW")
        regions = ", ".join(prediction.get("affected_regions", ["global"]))
        duration = prediction.get("estimated_duration_days", 0)

        prompt = f"""
You are a senior supply chain risk analyst. A disruption has been detected.

Disruption Details:
- Risk Level: {label}
- Disruption Type: {disruption_type}
- Affected Regions: {regions}
- Estimated Duration: {duration} days

Generate a precise, actionable prevention response plan. Respond ONLY with a valid JSON object in this exact format:
{{
  "immediate_actions": ["action1", "action2", "action3"],
  "short_term_actions": ["action1", "action2"],
  "long_term_actions": ["action1", "action2"],
  "rerouting_options": [],
  "supplier_alternatives": [],
  "inventory_recommendations": ["recommendation1"],
  "estimated_cost_impact": "High ($100k+)",
  "priority": "P1",
  "llm_summary": "A concise 2-sentence executive summary of the situation and recommended response."
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown code block if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        import json
        plan = json.loads(text.strip())
        plan["generated_by"] = "gemini-1.5-flash"
        return plan
    except Exception as e:
        print(f"[Gemini] Plan generation failed: {e}")
        return None

def _rule_based_plan(prediction: dict) -> dict:
    """Reliable rule-based fallback used when LLM is unavailable."""
    disruption_type = prediction.get("disruption_type", "normal")
    label = prediction.get("label", "LOW")
    regions = prediction.get("affected_regions", ["global"])

    plan = {
        "immediate_actions": [],
        "short_term_actions": [],
        "long_term_actions": [],
        "rerouting_options": [],
        "supplier_alternatives": [],
        "inventory_recommendations": [],
        "estimated_cost_impact": "Minimal",
        "priority": "P3",
        "llm_summary": None,
        "generated_by": "rule-engine"
    }

    if label == "CRITICAL": plan.update({"priority": "P1", "estimated_cost_impact": "High ($100k+)"})
    elif label == "HIGH": plan.update({"priority": "P2", "estimated_cost_impact": "Medium ($10k–$100k)"})
    elif label == "MEDIUM": plan.update({"priority": "P3", "estimated_cost_impact": "Low ($1k–$10k)"})

    playbooks = {
        "port_strike": {
            "immediate_actions": ["Reroute to alternate port immediately", "Notify procurement team", "Contact freight forwarder"],
            "short_term_actions": ["Activate air freight for critical SKUs", "Communicate delays to customers"],
            "long_term_actions": ["Buffer stock at inland warehouses", "Negotiate multi-port contracts"],
            "inventory_recommendations": ["Increase safety stock by 30%"]
        },
        "weather": {
            "immediate_actions": [f"Suspend shipments to {regions[0]}", "Issue carrier weather alerts", "Check vessel tracking"],
            "short_term_actions": ["Switch to inland routes if available", "Extend lead time commitments"],
            "long_term_actions": ["Pre-position inventory at safe hubs", "Build seasonal weather buffer"],
            "inventory_recommendations": ["Pre-build 2-week buffer stock"]
        },
        "war": {
            "immediate_actions": ["Escalate to executive team", f"Blacklist routes through {regions[0]}", "Issue force majeure notice"],
            "short_term_actions": ["Activate secondary supplier network", "Review insurance coverage"],
            "long_term_actions": ["Trigger full supplier diversification audit"],
            "inventory_recommendations": ["Increase safety stock to 60-day cover"]
        },
        "cyber": {
            "immediate_actions": ["Switch to manual booking systems", "Alert IT security team", "Isolate affected systems"],
            "short_term_actions": ["Verify all in-transit shipments manually", "Pause automated order triggers"],
            "long_term_actions": ["Conduct full cybersecurity audit", "Implement backup EDI systems"],
            "inventory_recommendations": ["Manual stock verification required"]
        },
        "logistics": {
            "immediate_actions": ["Notify sales team of delays", "Assess which orders are critical"],
            "short_term_actions": ["Activate backup carrier contracts", "Extend customer lead times"],
            "long_term_actions": ["Increase safety stock targets", "Qualify 2 additional carriers"],
            "inventory_recommendations": ["Increase safety stock by 20%"]
        },
        "supplier": {
            "immediate_actions": ["Assess inventory depletion timeline", "Identify alternate source immediately"],
            "short_term_actions": ["Emergency PO to Tier-2 suppliers", "Expedite open orders"],
            "long_term_actions": ["Fully activate Tier-2 supplier", "Dual-source critical components"],
            "inventory_recommendations": ["Trigger emergency replenishment order"]
        },
        "customs": {
            "immediate_actions": ["Engage customs broker immediately", "Prepare all required documentation"],
            "short_term_actions": ["Add delay buffer to planning system", "Notify affected customers"],
            "long_term_actions": ["Review import compliance procedures"],
            "inventory_recommendations": ["Pull forward upcoming orders to avoid gap"]
        },
    }
    
    playbook = playbooks.get(disruption_type, {
        "immediate_actions": ["Continue routine monitoring"],
        "short_term_actions": ["No action required"],
        "long_term_actions": ["Maintain current safety stock levels"],
        "inventory_recommendations": []
    })
    plan.update(playbook)
    return plan

def generate_prevention_plan(prediction: dict) -> dict:
    """Main entry: Try Gemini first, fall back to rule engine."""
    llm_plan = _llm_prevention_plan(prediction)
    if llm_plan:
        return llm_plan
    return _rule_based_plan(prediction)
