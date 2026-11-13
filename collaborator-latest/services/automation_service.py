from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models_extended import OrderModel, FinancialTrackingModel, get_session
from services.inventory_service import place_order, get_inventory_by_sku
from services.contact_service import get_supplier_contacts
from services.alert_service import send_alert

def auto_handle_disruption(shipment_id: str, disruption_type: str, risk_level: str, supplier_id: str, affected_sku: str):
    """
    Automatically handle disruptions:
    1. Check inventory levels
    2. Place emergency orders if needed
    3. Notify supplier contacts
    4. Track financial impact
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
                
                # Log financial impact of prevention
                with get_session() as s:
                    impact = FinancialTrackingModel(
                        id=f"FIN-{datetime.utcnow().timestamp()}",
                        shipment_id=shipment_id,
                        event_type="Prevention_Action",
                        impact_usd=-order_result['total_cost'],
                        description=f"Emergency buffer order for {affected_sku}",
                        action_taken="auto_buffer_order",
                        roi_estimated=0.45
                    )
                    s.add(impact)
                    s.commit()
        
        # 2. Notify supplier contacts
        contacts = get_supplier_contacts(supplier_id)
        for contact in contacts:
            if contact.alert_level in ["ALL", "CRITICAL_ONLY"] or (risk_level == "CRITICAL" and contact.alert_level == "CRITICAL_ONLY"):
                send_alert(
                    level="CRITICAL" if risk_level == "CRITICAL" else "WARNING",
                    message=f"Disruption Alert: {disruption_type} affecting shipment {shipment_id}. Actions taken: {', '.join(actions_taken)}",
                    recipients=[contact.email]
                )
                actions_taken.append(f"Alert sent to {contact.contact_name}")
        
        # 3. Log disruption financial impact
        with get_session() as s:
            impact = FinancialTrackingModel(
                id=f"FIN-DISRUPT-{datetime.utcnow().timestamp()}",
                shipment_id=shipment_id,
                event_type="Disruption",
                impact_usd=-100000,  # Placeholder
                description=f"{disruption_type} disruption on shipment {shipment_id}",
                timestamp=datetime.utcnow()
            )
            s.add(impact)
            s.commit()
        
        return {
            "shipment_id": shipment_id,
            "disruption_type": disruption_type,
            "actions_taken": actions_taken,
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
                OrderModel.created_at >= datetime.now() - timedelta(hours=24)
            ).all()
            return {
                "auto_orders_last_24h": len(orders),
                "total_auto_cost": sum(o.total_cost for o in orders),
                "status": "active"
            }
    except:
        return {"status": "error"}
