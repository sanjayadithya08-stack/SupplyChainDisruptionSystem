from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models_extended import OrderModel, get_session
from services.inventory_service import place_order, get_inventory_by_sku
from services.contact_service import get_supplier_contacts
from services.alert_service import send_alert

def auto_handle_disruption(shipment_id: str, disruption_type: str, risk_level: str, supplier_id: str, affected_sku: str):
    """
    Automatically handle disruptions:
    1. Check inventory levels
    2. Place emergency orders if needed
    3. Notify supplier contacts
    4. Record exactly what was done for the activity timeline
    """
    
    actions_taken = []
    
    try:
        # 1. Check inventory for affected SKU
        inv = get_inventory_by_sku(affected_sku)
        if inv and inv.current_stock <= inv.safety_stock:
            # Place emergency order
            order_result = place_order(
                supplier_id=supplier_id,
                sku=affected_sku,
                quantity=int(inv.safety_stock * 1.5),
                unit_price=inv.unit_cost,
                reason=f"Disruption-{disruption_type}",
                shipment_id=shipment_id
            )
            
            if order_result:
                actions_taken.append(f"Emergency order placed: {order_result['id']}")
        
        # 2. Notify supplier contacts
        contacts = get_supplier_contacts(supplier_id)
        for contact in contacts:
            if contact.alert_level == "ALL" or (
                risk_level == "CRITICAL" and contact.alert_level == "CRITICAL_ONLY"
            ):
                delivered = send_alert(
                    level="CRITICAL" if risk_level == "CRITICAL" else "WARNING",
                    message=f"Disruption Alert: {disruption_type} affecting shipment {shipment_id}. Actions taken: {', '.join(actions_taken)}",
                    recipients=[contact.email]
                )
                if delivered:
                    actions_taken.append(f"Alert delivered to {contact.contact_name}")
                else:
                    actions_taken.append(f"Alert saved to the local log; delivery to {contact.contact_name} is not configured")

        if not actions_taken:
            actions_taken.append("Risk review recorded. No purchase order or supplier notification was configured.")

        from services.action_service import record_action
        activity_id = record_action(
            "mitigation_executed",
            f"{risk_level} {disruption_type} risk response recorded for shipment {shipment_id}.",
            shipment_id=shipment_id, actor="operator",
            metadata={"disruption_type": disruption_type, "risk_level": risk_level, "actions_taken": actions_taken}
        )
        
        return {
            "shipment_id": shipment_id,
            "disruption_type": disruption_type,
            "actions_taken": actions_taken,
            "activity_id": activity_id,
            "status": "automated_response_executed"
        }
    
    except Exception as e:
        print(f"Automation error: {e}")
        return {"status": "failed", "error": str(e)}

def get_automation_status():
    """Get status of recent automated actions"""
    try:
        with get_session() as s:
            orders = s.query(OrderModel).filter(
                OrderModel.reason.like("%Disruption%"),
                OrderModel.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            return {
                "auto_orders_last_24h": len(orders),
                "total_auto_cost": sum(o.total_cost for o in orders),
                "status": "active"
            }
    except:
        return {"status": "error"}
