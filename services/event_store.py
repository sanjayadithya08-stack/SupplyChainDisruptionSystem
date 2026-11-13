"""Database-backed application event store for deployments without durable local files."""
from datetime import datetime
from db.models_extended import AppEventModel, get_session

def write_event(category: str, event_id: str, payload: dict):
    with get_session() as session:
        session.add(AppEventModel(id=event_id, category=category, payload=payload, created_at=datetime.utcnow()))
        session.commit()

def list_events(category: str, limit: int = 100):
    with get_session() as session:
        rows = (session.query(AppEventModel).filter(AppEventModel.category == category)
                .order_by(AppEventModel.created_at.desc()).limit(max(1, limit)).all())
        return [row.payload for row in rows]

def update_event(category: str, event_id: str, changes: dict):
    with get_session() as session:
        row = session.query(AppEventModel).filter(
            AppEventModel.category == category, AppEventModel.id == event_id
        ).first()
        if not row:
            return None
        row.payload = {**(row.payload or {}), **changes}
        session.commit()
        return row.payload
