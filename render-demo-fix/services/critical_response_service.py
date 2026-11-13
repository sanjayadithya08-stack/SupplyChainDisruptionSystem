"""Automatic, cause-specific follow-up for newly detected critical risks."""
from __future__ import annotations

from services.action_service import record_action


CAUSE_ACTIONS = {
    "weather": "Request a carrier safety check, alternate-route options, and a revised ETA.",
    "port_strike": "Request alternate-port and carrier-capacity options with a revised ETA.",
    "war": "Flag the route for security review and request safe-route confirmation before booking changes.",
    "cyber": "Request a shipment-status check through an approved alternate channel and alert the security contact.",
    "logistics": "Request current shipment location, cause of delay, and a recovery ETA from the carrier.",
    "supplier": "Request the supplier's recovery date and confirm qualified alternate-source availability.",
    "customs": "Request the broker's hold reason, missing documents, and clearance estimate.",
}


def _delivery_summary(statuses: list[dict], missing_message: str) -> dict:
    if not statuses:
        return {"status": "not_configured", "detail": missing_message, "contacts": 0}
    sent_count = sum(item.get("status") == "sent" for item in statuses)
    failed_count = sum(item.get("status") == "failed" for item in statuses)
    if sent_count and failed_count:
        state = "partially_sent"
    elif sent_count:
        state = "sent"
    elif failed_count:
        state = "failed"
    else:
        state = "not_configured"
    detail = next((item.get("detail") for item in statuses if item.get("detail")), None)
    return {"status": state, "detail": detail, "contacts": len(statuses),
            "sent_count": sent_count, "failed_count": failed_count, "results": statuses}


def execute_critical_response(event: dict, shipment: dict) -> dict:
    """Create an auditable follow-up and email actual supplier/client contacts.

    This workflow requests information or review. It does not reroute freight,
    place purchase orders, or mark the disruption resolved automatically.
    """
    from services.contact_service import get_receiver, get_supplier_contacts
    from services.alert_service import send_recipient_email

    shipment_id = shipment.get("id", event.get("shipment_id", "Shipment"))
    cause = str(event.get("disruption_type", "logistics")).casefold()
    next_step = CAUSE_ACTIONS.get(cause, "Request a recovery plan, a current status, and a revised ETA.")
    evidence = event.get("source_summary") or "No external cause details were attached to this finding."
    sku = shipment.get("sku", "SKU not supplied")
    eta = shipment.get("estimated_arrival", "Not supplied")
    supplier_name = shipment.get("supplier_name", "Supplier")
    receiver_id = shipment.get("receiver_id")
    receiver = get_receiver(receiver_id) if receiver_id else None

    supplier_results = []
    contacts = get_supplier_contacts(shipment.get("supplier_id"))
    for contact in contacts:
        if contact.alert_level not in {"ALL", "CRITICAL_ONLY"} or not contact.email:
            continue
        message = (
            f"A critical {cause.replace('_', ' ')} disruption affects shipment {shipment_id} ({sku}).\n\n"
            f"Signal: {evidence}\n"
            f"Route: {shipment.get('origin', 'Origin')} to {shipment.get('destination', 'Destination')}\n"
            f"Current ETA: {eta}\n\n"
            f"Automated follow-up requested: {next_step}\n"
            "Please reply with the latest status and recovery options. This notice does not change the booking."
        )
        supplier_results.append(send_recipient_email(
            "CRITICAL", f"Critical disruption · shipment {shipment_id}", message, contact.email,
            role="supplier",
        ))

    customer_results = []
    if receiver and receiver.contact_email:
        message = (
            f"We identified a critical {cause.replace('_', ' ')} disruption affecting shipment {shipment_id} ({sku}).\n\n"
            f"Signal: {evidence}\n"
            f"Current ETA: {eta}\n\n"
            f"Our automated follow-up is to {next_step[0].lower() + next_step[1:]} We will share a confirmed update when available."
        )
        customer_results.append(send_recipient_email(
            "CRITICAL", f"Shipment update · {shipment_id}", message, receiver.contact_email,
            role="customer",
        ))

    supplier_delivery = _delivery_summary(supplier_results, "Supplier notification email is not configured for this shipment.")
    customer_delivery = _delivery_summary(customer_results, "Customer notification email is not configured for this receiver.")
    statuses = {supplier_delivery["status"], customer_delivery["status"]}
    if statuses == {"sent"}:
        workflow_status = "notified"
    elif "sent" in statuses or "partially_sent" in statuses:
        workflow_status = "partially_notified"
    elif "failed" in statuses:
        workflow_status = "delivery_failed"
    else:
        workflow_status = "awaiting_contact_configuration"

    action_id = record_action(
        "critical_response_automated",
        f"Critical {cause.replace('_', ' ')} follow-up created for {shipment_id}; notification status: {workflow_status.replace('_', ' ')}.",
        shipment_id=shipment_id, actor="system",
        status="completed" if workflow_status in {"notified", "partially_notified", "awaiting_contact_configuration"} else "failed",
        metadata={
            "event_id": event.get("id"), "cause": cause, "automated_action": next_step,
            "workflow_status": workflow_status, "supplier_notification": supplier_delivery,
            "customer_notification": customer_delivery,
        },
    )
    return {"activity_id": action_id, "automated_action": next_step, "workflow_status": workflow_status,
            "supplier_notification": supplier_delivery, "customer_notification": customer_delivery}
