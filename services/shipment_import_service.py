"""Validate and import a company's shipment CSV rows into the local workspace."""
from __future__ import annotations

import hashlib
import csv
import math
import re
from datetime import date
from pathlib import Path
from typing import Any

from db.models import RouteModel, ShipmentModel, SupplierModel, get_session
from db.models_extended import DisruptionEventModel, ReceiverModel, SupplierContactModel


def ensure_sample_shipments() -> bool:
    """Load or upgrade the bundled company ledger without importing user files."""
    from utils.config import Config
    sample_path = Path(Config.DATA_DIR) / "sample_company_shipments.csv"
    if not sample_path.is_file():
        return False
    with sample_path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return False
    expected_ids = {str(row.get("shipment_id", "")).strip() for row in rows}
    with get_session() as session:
        actual_ids = {row[0] for row in session.query(ShipmentModel.id).all()}
    if actual_ids == expected_ids:
        return False
    import_shipments(
        rows, replace_existing=bool(actual_ids), actor="system",
        source_label="bundled company dataset",
    )
    return True


ALIASES = {
    "id": "shipment_id", "shipment": "shipment_id", "shipmentid": "shipment_id",
    "supplier": "supplier_name", "suppliername": "supplier_name",
    "origin_city": "origin", "from": "origin", "destination_city": "destination", "to": "destination",
    "estimated_arrival": "eta", "arrival_date": "eta", "estimateddelivery": "eta",
    "value": "value_usd", "shipment_value": "value_usd", "valueusd": "value_usd",
    "quantity": "units", "unit_count": "units", "product_sku": "sku",
    "suppliercountry": "supplier_country", "receiver": "receiver_id", "customer": "receiver_id",
    "supplier_contact_email": "supplier_email", "suppliercontactemail": "supplier_email",
    "client_email": "receiver_email", "customer_email": "receiver_email",
    "receiver_contact_email": "receiver_email", "receivercontactemail": "receiver_email",
    "risk": "risk_level", "baseline_risk": "risk_level", "risklevel": "risk_level",
    "reliability": "supplier_reliability", "supplier_reliability_score": "supplier_reliability",
}
REQUIRED = {"shipment_id", "sku", "supplier_name", "origin", "destination", "status", "eta", "units", "value_usd"}
STATUSES = {"in transit": "In Transit", "transit": "In Transit", "in_transit": "In Transit",
            "pending": "Pending", "delayed": "Delayed", "delivered": "Delivered"}


def _key(value: Any) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return ALIASES.get(key, key)


def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.casefold().encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def import_shipments(rows: list[dict[str, Any]], *, replace_existing: bool = False,
                     actor: str = "operator", source_label: str = "company shipment records") -> dict:
    if not rows:
        raise ValueError("The uploaded file has no shipment rows.")
    normalized = [{_key(k): v for k, v in row.items()} for row in rows]
    missing = sorted(REQUIRED - set(normalized[0]))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    prepared: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(normalized, start=2):
        try:
            item = {k: _text(row.get(k, "")) for k in REQUIRED - {"units", "value_usd"}}
            item["shipment_id"] = item["shipment_id"] or ""
            item["sku"] = item["sku"] or ""
            item["supplier_name"] = item["supplier_name"] or ""
            item["origin"] = item["origin"] or ""
            item["destination"] = item["destination"] or ""
            status_raw = item["status"].lower().replace("-", " ")
            item["status"] = STATUSES.get(status_raw, STATUSES.get(status_raw.replace(" ", "_")))
            if not item["status"]:
                raise ValueError("status must be In Transit, Pending, Delayed, or Delivered")
            date.fromisoformat(item["eta"])
            unit_value = float(_text(row.get("units", "0")).replace(",", ""))
            if not unit_value.is_integer():
                raise ValueError("units must be a whole number")
            item["units"] = int(unit_value)
            item["value_usd"] = float(_text(row.get("value_usd", "0")).replace(",", "").replace("$", "").upper().replace("USD", "").strip())
            item["risk_level"] = (_text(row.get("risk_level")) or "LOW").upper()
            if item["risk_level"] not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                raise ValueError("risk_level must be LOW, MEDIUM, HIGH, or CRITICAL")
            item["supplier_reliability"] = float(_text(row.get("supplier_reliability", "0.75")) or "0.75")
            if not 0 <= item["supplier_reliability"] <= 1:
                raise ValueError("supplier_reliability must be between 0 and 1")
            if not all(item[k] for k in ("shipment_id", "sku", "supplier_name", "origin", "destination")):
                raise ValueError("shipment_id, sku, supplier_name, origin, and destination are required")
            if item["units"] <= 0 or item["value_usd"] < 0:
                raise ValueError("units must be positive and value_usd cannot be negative")
            item["supplier_country"] = _text(row.get("supplier_country")) or "Global"
            item["receiver_id"] = _text(row.get("receiver_id")) or "Company"
            item["supplier_id"] = _text(row.get("supplier_id"))
            item["route_id"] = _text(row.get("route_id"))
            item["supplier_email"] = _text(row.get("supplier_email"))
            item["receiver_email"] = _text(row.get("receiver_email"))
            for email_field in ("supplier_email", "receiver_email"):
                if item[email_field] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", item[email_field]):
                    raise ValueError(f"{email_field} must be a valid email address")
            if item["shipment_id"].casefold() in seen:
                raise ValueError("duplicate shipment_id in uploaded file")
            seen.add(item["shipment_id"].casefold())
            prepared.append(item)
        except (TypeError, ValueError, OverflowError) as exc:
            errors.append(f"Row {index}: {exc}")
    if errors:
        raise ValueError("Import was not applied. Fix these rows and upload again:\n" + "\n".join(errors[:20]))

    with get_session() as session:
        supplier_ids: dict[tuple[str, str], str] = {}
        route_ids: dict[tuple[str, str], str] = {}
        for item in prepared:
            skey = (item["supplier_name"].casefold(), item["supplier_country"].casefold())
            sid = supplier_ids.get(skey)
            if not sid:
                existing = session.query(SupplierModel).filter(
                    SupplierModel.name.ilike(item["supplier_name"]),
                    SupplierModel.country.ilike(item["supplier_country"]),
                ).first()
                sid = existing.id if existing else (item["supplier_id"] or _stable_id("SUP", "|".join(skey)))
                if not existing:
                    session.merge(SupplierModel(id=sid, name=item["supplier_name"], country=item["supplier_country"],
                                                tier=1, product_categories=item["sku"], risk_score=item["supplier_reliability"], alternate_id=""))
                else:
                    existing.risk_score = item["supplier_reliability"]
                supplier_ids[skey] = sid
            item["supplier_id"] = sid
            if item["supplier_email"]:
                contact = session.query(SupplierContactModel).filter_by(
                    supplier_id=sid, email=item["supplier_email"]
                ).first()
                if not contact:
                    session.add(SupplierContactModel(
                        id=f"SC-{_stable_id('CONTACT', sid + '|' + item['supplier_email'])}",
                        supplier_id=sid, contact_name=item["supplier_name"], email=item["supplier_email"],
                        role="Critical disruption notifications", alert_level="CRITICAL_ONLY", verified=False,
                    ))

            rkey = (item["origin"].casefold(), item["destination"].casefold())
            rid = route_ids.get(rkey)
            if not rid:
                existing_route = session.query(RouteModel).filter(
                    RouteModel.origin.ilike(item["origin"]), RouteModel.destination.ilike(item["destination"])
                ).first()
                rid = existing_route.id if existing_route else (item["route_id"] or _stable_id("RTE", "|".join(rkey)))
                if not existing_route:
                    session.merge(RouteModel(id=rid, origin=item["origin"], destination=item["destination"],
                                             via_ports="", carrier="Company supplied", transit_days=0, risk_level="UNKNOWN"))
                route_ids[rkey] = rid
            item["route_id"] = rid
            receiver = session.query(ReceiverModel).filter_by(id=item["receiver_id"]).first()
            if receiver:
                if item["receiver_email"]:
                    receiver.contact_email = item["receiver_email"]
                if not receiver.name:
                    receiver.name = item["receiver_id"]
            elif item["receiver_email"]:
                session.add(ReceiverModel(
                    id=item["receiver_id"], name=item["receiver_id"], city=item["destination"],
                    contact_email=item["receiver_email"],
                ))

        if replace_existing:
            session.query(ShipmentModel).delete(synchronize_session=False)
            # Prior scan results refer to the old ledger; preserve them in storage,
            # but keep them out of the new company's active risk queue.
            session.query(DisruptionEventModel).filter(
                DisruptionEventModel.status.in_(["open", "mitigated"])
            ).update({DisruptionEventModel.status: "archived"}, synchronize_session=False)
        for item in prepared:
            session.merge(ShipmentModel(
                id=item["shipment_id"], sku=item["sku"], supplier_id=item["supplier_id"],
                receiver_id=item["receiver_id"], route_id=item["route_id"], status=item["status"],
                estimated_arrival=item["eta"], value_usd=item["value_usd"], units=item["units"],
                risk_level=item["risk_level"],
            ))
        session.commit()

    from services.action_service import record_action
    record_action(
        "shipment_data_imported",
        f"Loaded {len(prepared)} {source_label}" + (" and replaced the shipment list." if replace_existing else "."),
        actor=actor, metadata={"imported": len(prepared), "replaced_existing": replace_existing},
    )
    return {"imported": len(prepared), "suppliers": len(supplier_ids), "routes": len(route_ids), "replaced_existing": replace_existing}
