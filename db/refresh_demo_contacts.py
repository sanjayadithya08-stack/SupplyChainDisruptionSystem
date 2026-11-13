"""Mark seeded sample contacts as demo-only and ensure every active supplier has one."""
from db.models import SupplierModel, get_session as get_core_session
from db.models_extended import ReceiverModel, SupplierContactModel, ensure_contact_schema, get_session as get_extended_session

ensure_contact_schema()
with get_core_session() as core, get_extended_session() as ext:
    suppliers = {row.id: row.name for row in core.query(SupplierModel).all()}
    for sid, supplier_name in suppliers.items():
        contacts = ext.query(SupplierContactModel).filter(SupplierContactModel.supplier_id == sid).order_by(SupplierContactModel.id).all()
        if not contacts:
            contacts = [SupplierContactModel(id=f"DEMO-{sid}", supplier_id=sid, contact_name=f"{supplier_name} Operations Contact (Demo)", email=f"{sid.lower()}.contact@example.com", phone="", role="Operations (demo)", alert_level="ALL", verified=False)]
            ext.add_all(contacts)
        for index, contact in enumerate(contacts, start=1):
            contact.contact_name = f"{supplier_name} Contact {index} (Demo)"
            contact.email = f"{sid.lower()}.contact{index}@example.com"
            contact.phone = ""
            contact.role = "Supplier operations (demo)"
            contact.verified = False
    for receiver in ext.query(ReceiverModel).all():
        receiver.name = receiver.name.replace(" (Demo)", "") + " (Demo)"
        receiver.contact_email = f"receiver.{receiver.id.lower()}@example.com"
        receiver.contact_phone = ""
        receiver.contact_verified = False
    ext.commit()
print(f"Prepared {len(suppliers)} demo supplier contact groups and receiver contacts. No shipments were changed.")
