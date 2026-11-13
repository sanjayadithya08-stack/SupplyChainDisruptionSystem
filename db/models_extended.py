"""
Database models extension for:
- Supplier Contacts
- Receivers/Customers
- Inventory Management
- Orders/Purchase Orders
- Financial Tracking
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, Column, String, Float, Integer, Text, DateTime, Boolean, ForeignKey, inspect, text, JSON
from sqlalchemy.orm import DeclarativeBase, Session
from datetime import datetime
from utils.config import Config

engine = create_engine(Config.DB_URL, echo=False)

class Base(DeclarativeBase):
    pass

# -- SUPPLIER CONTACTS -------
class SupplierContactModel(Base):
    __tablename__ = "supplier_contacts"
    id              = Column(String, primary_key=True)
    supplier_id     = Column(String, nullable=False)
    contact_name    = Column(String, nullable=False)
    email           = Column(String, nullable=False)
    phone           = Column(String)
    role            = Column(String)
    alert_level     = Column(String)
    verified        = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

# -- RECEIVERS / CUSTOMERS -------
class ReceiverModel(Base):
    __tablename__ = "receivers"
    id              = Column(String, primary_key=True)
    name            = Column(String, nullable=False)
    country         = Column(String)
    city            = Column(String)
    contact_email   = Column(String)
    contact_phone   = Column(String)
    contact_verified = Column(Boolean, default=False)
    sla_delivery_days = Column(Integer, default=30)
    tier            = Column(String)
    created_at      = Column(DateTime, default=datetime.utcnow)

# -- INVENTORY MANAGEMENT -------
class InventoryModel(Base):
    __tablename__ = "inventory"
    id              = Column(String, primary_key=True)
    sku             = Column(String, nullable=False)
    supplier_id     = Column(String, nullable=False)
    current_stock   = Column(Integer, default=0)
    safety_stock    = Column(Integer, default=0)
    reorder_point   = Column(Integer, default=0)
    lead_time_days  = Column(Integer, default=14)
    unit_cost       = Column(Float, default=0.0)
    last_updated    = Column(DateTime, default=datetime.utcnow)

# -- ORDERS / PURCHASE ORDERS -------
class OrderModel(Base):
    __tablename__ = "orders"
    id              = Column(String, primary_key=True)
    supplier_id     = Column(String, nullable=False)
    sku             = Column(String, nullable=False)
    quantity        = Column(Integer, nullable=False)
    unit_price      = Column(Float, nullable=False)
    total_cost      = Column(Float, nullable=False)
    status          = Column(String)
    reason          = Column(String)
    triggered_by_shipment = Column(String)
    order_date      = Column(DateTime, default=datetime.utcnow)
    expected_delivery = Column(String)
    created_at      = Column(DateTime, default=datetime.utcnow)

# -- FINANCIAL TRACKING -------
class FinancialTrackingModel(Base):
    __tablename__ = "financial_tracking"
    id              = Column(String, primary_key=True)
    shipment_id     = Column(String)
    event_type      = Column(String)
    impact_usd      = Column(Float, nullable=False)
    currency        = Column(String, default="USD")
    description     = Column(Text)
    action_taken    = Column(String)
    roi_estimated   = Column(Float)
    timestamp       = Column(DateTime, default=datetime.utcnow)

def get_session() -> Session:
    return Session(engine)

def ensure_contact_schema():
    """Create contact tables and add receiver verification to existing SQLite DBs."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        columns = {column["name"] for column in inspect(conn).get_columns("receivers")}
        if "contact_verified" not in columns:
            default_value = "FALSE" if conn.dialect.name == "postgresql" else "0"
            conn.execute(text(f"ALTER TABLE receivers ADD COLUMN contact_verified BOOLEAN NOT NULL DEFAULT {default_value}"))


def init_extended_db():
    """Add contact tables and seed demo records."""
    ensure_contact_schema()
    _seed_extended()
    print(f"Extended database initialized at {Config.DB_PATH}")

def _seed_extended():
    """Seed new tables with sample data"""
    supplier_contacts = [
        (f"DEMO-{sid}", sid, f"{sid} Operations Contact (Demo)", f"{sid.lower()}.contact@example.com", "", "Operations (demo)", "ALL", False)
        for sid in [f"S{i:03d}" for i in range(1, 15)]
    ]
    receivers = [
        ("TECH-HQ-LA", "TechCore North America HQ (Demo)", "United States", "Los Angeles", "receiver.tech-hq-la@example.com", "", 30, "Gold", False),
        ("TECH-NY-HUB", "TechCore East Coast Hub (Demo)", "United States", "New York", "receiver.tech-ny-hub@example.com", "", 28, "Gold", False),
        ("TECH-TX-HUB", "TechCore Central Distribution (Demo)", "United States", "Dallas", "receiver.tech-tx-hub@example.com", "", 30, "Silver", False),
        ("TECH-EU-HUB", "TechCore European Logistics Center (Demo)", "Netherlands", "Amsterdam", "receiver.tech-eu-hub@example.com", "", 35, "Gold", False),
        ("TECH-SYD", "TechCore APAC Hub (Demo)", "Australia", "Sydney", "receiver.tech-syd@example.com", "", 40, "Silver", False),
        ("TECH-VAN", "TechCore Canada Distribution (Demo)", "Canada", "Vancouver", "receiver.tech-van@example.com", "", 32, "Silver", False),
        ("TECH-TYO", "TechCore Japan Assembly Center (Demo)", "Japan", "Tokyo", "receiver.tech-tyo@example.com", "", 25, "Gold", False),
        ("TECH-UK-HUB", "TechCore UK Fulfillment (Demo)", "United Kingdom", "London", "receiver.tech-uk-hub@example.com", "", 30, "Silver", False),
    ]

    inventory = [
        ("INV001", "SKU-MC01", "S001", 5000, 2000, 1000, 14, 125.50),
        ("INV002", "SKU-CT03", "S007", 3000, 1500, 750, 16, 89.75),
        ("INV003", "SKU-AP01", "S003", 2500, 1000, 500, 10, 210.00),
        ("INV004", "SKU-PL01", "S009", 4000, 2000, 1000, 8, 45.00),
        ("INV005", "SKU-RM02", "S012", 2000, 800, 400, 12, 156.25),
        ("INV006", "SKU-PH01", "S013", 1500, 600, 300, 18, 320.00),
        ("INV007", "SKU-MC02", "S002", 3500, 1500, 750, 14, 118.00),
        ("INV008", "SKU-FB01", "S005", 5000, 2500, 1250, 6, 32.50),
    ]
    
    with get_session() as s:
        if s.query(SupplierContactModel).count() == 0:
            for row in supplier_contacts:
                s.add(SupplierContactModel(id=row[0], supplier_id=row[1], contact_name=row[2],
                                          email=row[3], phone=row[4], role=row[5], 
                                          alert_level=row[6], verified=row[7]))
        
        if s.query(ReceiverModel).count() == 0:
            for row in receivers:
                s.add(ReceiverModel(id=row[0], name=row[1], country=row[2], city=row[3],
                                    contact_email=row[4], contact_phone=row[5],
                                    sla_delivery_days=row[6], tier=row[7], contact_verified=row[8]))
        
        if s.query(InventoryModel).count() == 0:
            for row in inventory:
                s.add(InventoryModel(id=row[0], sku=row[1], supplier_id=row[2],
                                     current_stock=row[3], safety_stock=row[4],
                                     reorder_point=row[5], lead_time_days=row[6],
                                     unit_cost=row[7]))
        
        s.commit()

if __name__ == "__main__":
    init_extended_db()


class AppEventModel(Base):
    """Persistent application audit events for serverless deployments."""
    __tablename__ = "app_events"
    id = Column(String, primary_key=True)
    category = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
