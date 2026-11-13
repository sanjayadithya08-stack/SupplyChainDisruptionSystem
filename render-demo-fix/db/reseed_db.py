import sys
import os
import random
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from db.models import engine, Base as Base1, SupplierModel, RouteModel, ShipmentModel, get_session
from db.models_extended import Base as Base2, SupplierContactModel, ReceiverModel, InventoryModel, OrderModel, FinancialTrackingModel

def reseed():
    print("=======================================================")
    print("  TechCore Supply Chain — Reseeding Live Database 2026")
    print("=======================================================")
    
    # 1. Drop and re-create tables
    Base1.metadata.drop_all(engine)
    Base2.metadata.drop_all(engine)
    
    Base1.metadata.create_all(engine)
    Base2.metadata.create_all(engine)
    
    now = datetime.now()
    
    # 2. Suppliers Catalog
    suppliers = [
        SupplierModel(id="S001", name="Global MicroTech", country="Taiwan", tier=1, product_categories="Semiconductors,Controllers", risk_score=0.72, alternate_id="S002"),
        SupplierModel(id="S002", name="Seoul Silicates", country="South Korea", tier=2, product_categories="Semiconductors,DRAM", risk_score=0.91, alternate_id=""),
        SupplierModel(id="S003", name="Bavarian Motors Parts", country="Germany", tier=1, product_categories="Auto Parts,Engines", risk_score=0.88, alternate_id="S004"),
        SupplierModel(id="S004", name="Czech Auto Works", country="Czech Republic", tier=2, product_categories="Auto Parts,Transmission", risk_score=0.79, alternate_id=""),
        SupplierModel(id="S005", name="Pan-Am Textiles", country="Mexico", tier=1, product_categories="Fabrics,Apparel", risk_score=0.77, alternate_id="S006"),
        SupplierModel(id="S006", name="Andes Weavers", country="Peru", tier=2, product_categories="Fabrics,Cotton", risk_score=0.83, alternate_id=""),
        SupplierModel(id="S007", name="Shenzhen Electronics", country="China", tier=1, product_categories="Consumer Tech,PCB", risk_score=0.81, alternate_id="S008"),
        SupplierModel(id="S008", name="Hanoi Tech Assembly", country="Vietnam", tier=2, product_categories="Consumer Tech,Displays", risk_score=0.65, alternate_id=""),
        SupplierModel(id="S009", name="Texas Polymers", country="USA", tier=1, product_categories="Plastics,Chemicals", risk_score=0.95, alternate_id="S010"),
        SupplierModel(id="S010", name="Calgary Petrochem", country="Canada", tier=2, product_categories="Chemicals,Resins", risk_score=0.97, alternate_id=""),
        SupplierModel(id="S011", name="Jakarta Rubber Works", country="Indonesia", tier=1, product_categories="Raw Materials,Rubber", risk_score=0.68, alternate_id="S012"),
        SupplierModel(id="S012", name="Bangkok Materials", country="Thailand", tier=2, product_categories="Raw Materials,Metals", risk_score=0.71, alternate_id=""),
        SupplierModel(id="S013", name="Mumbai Pharma", country="India", tier=1, product_categories="Pharmaceuticals,API", risk_score=0.74, alternate_id="S014"),
        SupplierModel(id="S014", name="Hyderabad Biotech", country="India", tier=2, product_categories="Pharmaceuticals,Reagents", risk_score=0.82, alternate_id=""),
        SupplierModel(id="S015", name="Osaka Precision Steel", country="Japan", tier=1, product_categories="Raw Materials,Specialized Alloy", risk_score=0.93, alternate_id=""),
        SupplierModel(id="S016", name="Rotterdam Logistics Components", country="Netherlands", tier=1, product_categories="Auto Parts,Sensors", risk_score=0.86, alternate_id=""),
    ]
    
    # 3. Routes Catalog (15 Trade Corridors)
    routes = [
        RouteModel(id="R1", origin="Kaohsiung", destination="Los Angeles", via_ports="Trans-Pacific", carrier="Maersk", transit_days=14, risk_level="HIGH"),
        RouteModel(id="R2", origin="Shenzhen", destination="Seattle", via_ports="Trans-Pacific", carrier="MSC", transit_days=16, risk_level="MEDIUM"),
        RouteModel(id="R3", origin="Rotterdam", destination="New York", via_ports="Trans-Atlantic", carrier="Hapag-Lloyd", transit_days=10, risk_level="LOW"),
        RouteModel(id="R4", origin="Mumbai", destination="Rotterdam", via_ports="Red Sea,Suez Canal", carrier="CMA CGM", transit_days=24, risk_level="CRITICAL"),
        RouteModel(id="R5", origin="Mumbai", destination="Rotterdam", via_ports="Cape of Good Hope", carrier="CMA CGM", transit_days=36, risk_level="MEDIUM"),
        RouteModel(id="R6", origin="Tokyo", destination="Los Angeles", via_ports="Trans-Pacific", carrier="ONE", transit_days=12, risk_level="LOW"),
        RouteModel(id="R7", origin="Singapore", destination="Hamburg", via_ports="Suez Canal", carrier="Evergreen", transit_days=26, risk_level="HIGH"),
        RouteModel(id="R8", origin="Veracruz", destination="Houston", via_ports="Gulf of Mexico", carrier="ZIM", transit_days=4, risk_level="LOW"),
        RouteModel(id="R9", origin="Busan", destination="Vancouver", via_ports="North Pacific", carrier="HMM", transit_days=13, risk_level="LOW"),
        RouteModel(id="R10", origin="Jakarta", destination="Sydney", via_ports="Intra-Pacific", carrier="Evergreen", transit_days=8, risk_level="LOW"),
        RouteModel(id="R11", origin="Cape Town", destination="Rotterdam", via_ports="South Atlantic", carrier="Hapag-Lloyd", transit_days=20, risk_level="MEDIUM"),
        RouteModel(id="R12", origin="Mumbai", destination="Singapore", via_ports="Bay of Bengal", carrier="PIL", transit_days=7, risk_level="MEDIUM"),
        RouteModel(id="R13", origin="Shanghai", destination="Long Beach", via_ports="Trans-Pacific", carrier="COSCO", transit_days=15, risk_level="HIGH"),
        RouteModel(id="R14", origin="Manzanillo", destination="Long Beach", via_ports="Pacific Coastal", carrier="ONE", transit_days=5, risk_level="LOW"),
        RouteModel(id="R15", origin="Frankfurt Airport", destination="Chicago O'Hare", via_ports="Air Cargo Corridor", carrier="Lufthansa Cargo", transit_days=2, risk_level="LOW"),
    ]
    
    # 4. Receivers / Customer Hubs
    receivers = [
        ReceiverModel(id="TECH-HQ-LA", name="TechCore North America HQ", country="United States", city="Los Angeles", contact_email="la-ops@techcore.com", contact_phone="+1-310-555-0100", sla_delivery_days=30, tier="Gold"),
        ReceiverModel(id="TECH-NY-HUB", name="TechCore East Coast Hub", country="United States", city="New York", contact_email="ny-ops@techcore.com", contact_phone="+1-212-555-0100", sla_delivery_days=28, tier="Gold"),
        ReceiverModel(id="TECH-TX-HUB", name="TechCore Central Distribution", country="United States", city="Dallas", contact_email="tx-supply@techcore.com", contact_phone="+1-972-555-0100", sla_delivery_days=30, tier="Silver"),
        ReceiverModel(id="TECH-EU-HUB", name="TechCore European Logistics Center", country="Netherlands", city="Amsterdam", contact_email="eu-supply@techcore.nl", contact_phone="+31-20-555-0100", sla_delivery_days=35, tier="Gold"),
        ReceiverModel(id="TECH-SYD", name="TechCore APAC Hub", country="Australia", city="Sydney", contact_email="apac@techcore.com.au", contact_phone="+61-2-555-0100", sla_delivery_days=40, tier="Silver"),
        ReceiverModel(id="TECH-VAN", name="TechCore Canada Distribution", country="Canada", city="Vancouver", contact_email="supply@techcore.ca", contact_phone="+1-604-555-0100", sla_delivery_days=32, tier="Silver"),
        ReceiverModel(id="TECH-TYO", name="TechCore Japan Assembly Center", country="Japan", city="Tokyo", contact_email="japan-ops@techcore.jp", contact_phone="+81-3-5555-0100", sla_delivery_days=25, tier="Gold"),
        ReceiverModel(id="TECH-UK-HUB", name="TechCore UK Fulfillment", country="United Kingdom", city="London", contact_email="uk-fulfillment@techcore.co.uk", contact_phone="+44-20-7946-0100", sla_delivery_days=30, tier="Silver"),
    ]
    
    # 5. Supplier Contacts
    supplier_contacts = [
        SupplierContactModel(id="SC001", supplier_id="S001", contact_name="David Chen", email="procurement@globalmicrotech.tw", phone="+886-2-1234-5678", role="Procurement Director", alert_level="ALL", verified=True),
        SupplierContactModel(id="SC002", supplier_id="S001", contact_name="Sarah Wong", email="ops@globalmicrotech.tw", phone="+886-2-1234-5679", role="Operations Manager", alert_level="CRITICAL_ONLY", verified=True),
        SupplierContactModel(id="SC003", supplier_id="S003", contact_name="Klaus Mueller", email="supply@bavarian-motors.de", phone="+49-30-1234-5678", role="VP Supply Chain", alert_level="ALL", verified=True),
        SupplierContactModel(id="SC004", supplier_id="S007", contact_name="Wei Zhang", email="orders@shenzhen-elec.cn", phone="+86-755-1234-5678", role="Logistics Lead", alert_level="ALL", verified=True),
        SupplierContactModel(id="SC005", supplier_id="S009", contact_name="John Smith", email="sales@texaspolymers.us", phone="+1-512-1234-5678", role="Account Executive", alert_level="CRITICAL_ONLY", verified=True),
        SupplierContactModel(id="SC006", supplier_id="S002", contact_name="Min-Jun Park", email="logistics@seoulsilicates.kr", phone="+82-2-555-1234", role="Export Coordinator", alert_level="ALL", verified=True),
        SupplierContactModel(id="SC007", supplier_id="S008", contact_name="Nguyen Van Minh", email="contact@hanoitech.vn", phone="+84-24-3825-1234", role="Plant Director", alert_level="ALL", verified=True),
        SupplierContactModel(id="SC008", supplier_id="S013", contact_name="Aarav Sharma", email="export@mumbaipharma.in", phone="+91-22-6677-8899", role="Global Supply Lead", alert_level="ALL", verified=True),
    ]
    
    # 6. Inventory Records
    inventory = [
        InventoryModel(id="INV001", sku="SKU-MC01", supplier_id="S001", current_stock=12000, safety_stock=4000, reorder_point=6000, lead_time_days=14, unit_cost=125.50),
        InventoryModel(id="INV002", sku="SKU-MC02", supplier_id="S001", current_stock=8500, safety_stock=3000, reorder_point=5000, lead_time_days=14, unit_cost=140.00),
        InventoryModel(id="INV003", sku="SKU-CT03", supplier_id="S007", current_stock=6200, safety_stock=2500, reorder_point=3500, lead_time_days=16, unit_cost=89.75),
        InventoryModel(id="INV004", sku="SKU-AP01", supplier_id="S003", current_stock=4100, safety_stock=1500, reorder_point=2500, lead_time_days=10, unit_cost=210.00),
        InventoryModel(id="INV005", sku="SKU-PL01", supplier_id="S009", current_stock=9500, safety_stock=3500, reorder_point=5000, lead_time_days=8, unit_cost=45.00),
        InventoryModel(id="INV006", sku="SKU-RM02", supplier_id="S012", current_stock=3800, safety_stock=1200, reorder_point=2000, lead_time_days=12, unit_cost=156.25),
        InventoryModel(id="INV007", sku="SKU-PH01", supplier_id="S013", current_stock=2400, safety_stock=1000, reorder_point=1500, lead_time_days=18, unit_cost=320.00),
        InventoryModel(id="INV008", sku="SKU-FB01", supplier_id="S005", current_stock=11000, safety_stock=4000, reorder_point=6000, lead_time_days=6, unit_cost=32.50),
    ]

    # 7. Generate 48 Active 2026 Live Shipments
    sku_catalog = [
        ("SKU-MC01", "S001", 125.50), ("SKU-MC02", "S001", 140.00), ("SKU-MC03", "S002", 118.00), ("SKU-MC04", "S002", 160.00),
        ("SKU-CT01", "S007", 60.00),  ("SKU-CT02", "S007", 80.00),  ("SKU-CT03", "S008", 90.00),  ("SKU-CT04", "S008", 110.00),
        ("SKU-AP01", "S003", 210.00), ("SKU-AP02", "S003", 180.00), ("SKU-AP03", "S004", 195.00), ("SKU-AP04", "S004", 230.00),
        ("SKU-FB01", "S005", 32.50),  ("SKU-FB02", "S005", 40.00),  ("SKU-FB03", "S006", 28.00),
        ("SKU-PL01", "S009", 45.00),  ("SKU-PL02", "S009", 55.00),
        ("SKU-CH01", "S010", 75.00),  ("SKU-CH02", "S010", 90.00),
        ("SKU-RM01", "S011", 38.00),  ("SKU-RM02", "S012", 156.25), ("SKU-RM03", "S012", 48.00),
        ("SKU-PH01", "S013", 320.00), ("SKU-PH02", "S014", 270.00)
    ]
    
    receiver_ids = [r.id for r in receivers]
    route_ids = [r.id for r in routes]
    statuses = ["In Transit", "In Transit", "In Transit", "Delayed", "Pending", "In Transit"]
    
    shipments = []
    
    for i in range(1, 49):
        shp_id = f"SHP-{i:03d}"
        sku, sup_id, unit_cost = random.choice(sku_catalog)
        rec_id = random.choice(receiver_ids)
        rt_id = random.choice(route_ids)
        status = random.choice(statuses)
        
        # Calculate dynamic estimated arrival date relative to current time (Sept 2026)
        if status == "Delayed":
            days_out = random.randint(12, 35)
        elif status == "Pending":
            days_out = random.randint(15, 45)
        else:
            days_out = random.randint(2, 21)
            
        est_arrival = (now + timedelta(days=days_out)).strftime("%Y-%m-%d")
        units = random.randint(1500, 25000)
        val_usd = round(units * unit_cost, 2)
        
        shipments.append(ShipmentModel(
            id=shp_id,
            sku=sku,
            supplier_id=sup_id,
            receiver_id=rec_id,
            route_id=rt_id,
            status=status,
            estimated_arrival=est_arrival,
            value_usd=val_usd,
            units=units
        ))

    # Commit all to session
    with get_session() as s:
        s.add_all(suppliers)
        s.add_all(routes)
        s.add_all(receivers)
        s.add_all(supplier_contacts)
        s.add_all(inventory)
        s.add_all(shipments)
        s.commit()
        
    print(f"[OK] Database reseeded at {Config.DB_PATH}")
    print(f"  - Suppliers: {len(suppliers)}")
    print(f"  - Routes: {len(routes)}")
    print(f"  - Receivers: {len(receivers)}")
    print(f"  - Supplier Contacts: {len(supplier_contacts)}")
    print(f"  - Inventory Items: {len(inventory)}")
    print(f"  - Active 2026 Shipments: {len(shipments)}")
    print("=======================================================")

if __name__ == "__main__":
    reseed()
