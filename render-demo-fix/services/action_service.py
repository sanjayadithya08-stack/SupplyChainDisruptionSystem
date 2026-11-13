"""Persistent operational activity feed backed by SQLite."""
from dataclasses import dataclass
from datetime import datetime
import json
from uuid import uuid4

from db.models_extended import ActionModel, Base, engine, get_session

@dataclass
class Action:
    id: str
    action_type: str
    status: str
    summary: str
    shipment_id: str | None
    order_id: str | None
    actor: str
    metadata: dict
    created_at: str

def _ensure_table():
    """Safe for existing databases: creates only missing tables."""
    Base.metadata.create_all(engine)

def record_action(action_type: str, summary: str, *, shipment_id: str | None = None,
                  order_id: str | None = None, actor: str = "operator", status: str = "completed",
                  metadata: dict | None = None) -> str:
    _ensure_table()
    action_id = f"ACT-{uuid4().hex[:12].upper()}"
    with get_session() as session:
        session.add(ActionModel(
            id=action_id, action_type=action_type, status=status, summary=summary,
            shipment_id=shipment_id, order_id=order_id, actor=actor,
            metadata_json=json.dumps(metadata or {}, default=str),
        ))
        session.commit()
    return action_id

def get_recent_actions(limit: int = 50) -> list[Action]:
    _ensure_table()
    with get_session() as session:
        rows = session.query(ActionModel).order_by(ActionModel.created_at.desc()).limit(limit).all()
        return [Action(
            id=row.id, action_type=row.action_type, status=row.status, summary=row.summary,
            shipment_id=row.shipment_id, order_id=row.order_id, actor=row.actor,
            metadata=json.loads(row.metadata_json or "{}"),
            created_at=row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
        ) for row in rows]
