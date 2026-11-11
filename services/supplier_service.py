"""
Upgrade 3: DB-backed Supplier Service.
Falls back to hardcoded list if DB is unavailable.
"""
from dataclasses import dataclass
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class Supplier:
    id: str
    name: str
    country: str
    tier: int
    product_categories: list
    risk_score: float
    alternate_id: str

def _from_db() -> list[Supplier]:
    try:
        from db.models import get_session, SupplierModel
        with get_session() as s:
            rows = s.query(SupplierModel).all()
            return [Supplier(
                id=r.id, name=r.name, country=r.country, tier=r.tier,
                product_categories=r.product_categories.split(","),
                risk_score=r.risk_score, alternate_id=r.alternate_id
            ) for r in rows]
    except Exception as e:
        print(f"[SupplierService] DB unavailable, using stub: {e}")
        return []

_FALLBACK = [
    Supplier("S001","Global MicroTech","Taiwan",1,["Semiconductors"],0.85,"S002"),
    Supplier("S002","Seoul Silicates","South Korea",2,["Semiconductors"],0.20,""),
    Supplier("S003","Bavarian Motors Parts","Germany",1,["Auto Parts"],0.60,"S004"),
    Supplier("S004","Czech Auto Works","Czech Republic",2,["Auto Parts"],0.15,""),
    Supplier("S005","Pan-Am Textiles","Mexico",1,["Fabrics"],0.30,"S006"),
    Supplier("S006","Andes Weavers","Peru",2,["Fabrics"],0.10,""),
    Supplier("S007","Shenzhen Electronics","China",1,["Consumer Tech"],0.50,"S008"),
    Supplier("S008","Hanoi Tech Assembly","Vietnam",2,["Consumer Tech"],0.40,""),
    Supplier("S009","Texas Polymers","USA",1,["Plastics"],0.25,"S010"),
    Supplier("S010","Calgary Petrochem","Canada",2,["Chemicals"],0.05,""),
]

def get_all_suppliers() -> list[Supplier]:
    db = _from_db()
    return db if db else _FALLBACK

def get_alternates(supplier_id: str) -> list[Supplier]:
    all_s = get_all_suppliers()
    for s in all_s:
        if s.id == supplier_id and s.alternate_id:
            return [a for a in all_s if a.id == s.alternate_id]
    return []

def get_suppliers_by_region(region: str) -> list[Supplier]:
    region_map = {
        "east-asia": ["Taiwan","South Korea","China"],
        "europe": ["Germany","Czech Republic"],
        "north-america": ["USA","Canada"],
        "latin-america": ["Mexico","Peru"],
        "southeast-asia": ["Vietnam","Indonesia","Thailand"],
        "south-asia": ["India"],
        "middle-east": ["Egypt"],
    }
    allowed = region_map.get(region, [])
    return [s for s in get_all_suppliers() if s.country in allowed]

def assess_supplier_risk(supplier_id: str, geo_events: list) -> float:
    for s in get_all_suppliers():
        if s.id == supplier_id:
            score = s.risk_score
            for e in geo_events:
                if e.country == s.country:
                    score += 0.5 if e.severity == "CRITICAL" else 0.3 if e.severity == "HIGH" else 0
            return min(score, 1.0)
    return 0.0
