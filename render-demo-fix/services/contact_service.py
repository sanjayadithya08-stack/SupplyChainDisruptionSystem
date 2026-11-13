from dataclasses import dataclass
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models_extended import SupplierContactModel, ReceiverModel, InventoryModel, OrderModel, FinancialTrackingModel, get_session

@dataclass
class SupplierContact:
    id: str
    supplier_id: str
    contact_name: str
    email: str
    phone: str = None
    role: str = None
    alert_level: str = "ALL"

@dataclass
class Receiver:
    id: str
    name: str
    country: str = None
    city: str = None
    contact_email: str = None
    contact_phone: str = None
    sla_delivery_days: int = 30
    tier: str = "Silver"

def get_supplier_contacts(supplier_id: str = None):
    try:
        with get_session() as s:
            if supplier_id:
                contacts = s.query(SupplierContactModel).filter(SupplierContactModel.supplier_id == supplier_id).all()
            else:
                contacts = s.query(SupplierContactModel).all()
            return [SupplierContact(c.id, c.supplier_id, c.contact_name, c.email, c.phone, c.role, c.alert_level) for c in contacts]
    except: return []

def get_receivers():
    try:
        with get_session() as s:
            receivers = s.query(ReceiverModel).all()
            return [Receiver(r.id, r.name, r.country, r.city, r.contact_email, r.contact_phone, r.sla_delivery_days, r.tier) for r in receivers]
    except: return []

def get_receiver(receiver_id: str):
    try:
        with get_session() as s:
            r = s.query(ReceiverModel).filter(ReceiverModel.id == receiver_id).first()
            if r: return Receiver(r.id, r.name, r.country, r.city, r.contact_email, r.contact_phone, r.sla_delivery_days, r.tier)
    except: pass
    return None

def add_supplier_contact(supplier_id: str, contact_name: str, email: str):
    try:
        with get_session() as s:
            contact = SupplierContactModel(id=f"SC-{supplier_id}-{datetime.utcnow().timestamp()}", supplier_id=supplier_id, contact_name=contact_name, email=email)
            s.add(contact)
            s.commit()
            return True
    except: return False
