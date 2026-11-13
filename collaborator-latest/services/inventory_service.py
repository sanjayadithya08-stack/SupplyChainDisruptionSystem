from dataclasses import dataclass
from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models_extended import InventoryModel, OrderModel, get_session

@dataclass
class Inventory:
    id: str
    sku: str
    supplier_id: str
    current_stock: int
    safety_stock: int
    reorder_point: int
    lead_time_days: int
    unit_cost: float

@dataclass
class Order:
    id: str
    supplier_id: str
    sku: str
    quantity: int
    unit_price: float
    total_cost: float
    status: str
    reason: str
    triggered_by_shipment: str = None
    expected_delivery: str = None

def get_inventory():
    try:
        with get_session() as s:
            items = s.query(InventoryModel).all()
            return [Inventory(i.id, i.sku, i.supplier_id, i.current_stock, i.safety_stock, i.reorder_point, i.lead_time_days, i.unit_cost) for i in items]
    except: return []

def get_inventory_by_sku(sku: str):
    try:
        with get_session() as s:
            inv = s.query(InventoryModel).filter(InventoryModel.sku == sku).first()
            if inv: return Inventory(inv.id, inv.sku, inv.supplier_id, inv.current_stock, inv.safety_stock, inv.reorder_point, inv.lead_time_days, inv.unit_cost)
    except: pass
    return None

def check_low_stock():
    """Check if any inventory is below reorder point"""
    try:
        with get_session() as s:
            low = s.query(InventoryModel).filter(InventoryModel.current_stock <= InventoryModel.reorder_point).all()
            return [i.sku for i in low]
    except: return []

def place_order(supplier_id: str, sku: str, quantity: int, unit_price: float, reason: str = "Inventory", shipment_id: str = None):
    try:
        with get_session() as s:
            order_id = f"ORD-{supplier_id}-{datetime.utcnow().timestamp()}"
            lead_time = s.query(InventoryModel).filter(InventoryModel.sku == sku).first().lead_time_days if sku else 14
            expected_delivery = (datetime.now() + timedelta(days=lead_time)).strftime("%Y-%m-%d")
            order = OrderModel(id=order_id, supplier_id=supplier_id, sku=sku, quantity=quantity, unit_price=unit_price, total_cost=quantity*unit_price, status="Placed", reason=reason, triggered_by_shipment=shipment_id, expected_delivery=expected_delivery)
            s.add(order)
            s.commit()
            return {"id": order_id, "quantity": quantity, "total_cost": quantity*unit_price, "expected_delivery": expected_delivery}
    except Exception as e:
        print(f"Order error: {e}")
        return None

def get_pending_orders():
    try:
        with get_session() as s:
            orders = s.query(OrderModel).filter(OrderModel.status.in_(["Placed", "Confirmed"])).all()
            return [Order(o.id, o.supplier_id, o.sku, o.quantity, o.unit_price, o.total_cost, o.status, o.reason, o.triggered_by_shipment, o.expected_delivery) for o in orders]
    except: return []
