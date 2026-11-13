"""
First-run bootstrap.

ML artefacts are gitignored and the seeded SQLite data has ETAs relative to the day it
was generated, so a fresh clone used to start with no models (every prediction UNKNOWN)
and shipments whose arrival dates were already in the past. This module fixes both.
"""
import os, sys
from datetime import date
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config


def models_present() -> bool:
    return all(os.path.exists(p) for p in (
        Config.PIPELINE_PATH, Config.COMPANY_MODEL_PATH, Config.COMPANY_ENCODER_PATH))


def train_models(force: bool = False):
    if not force and models_present():
        return
    if force or not os.path.exists(Config.PIPELINE_PATH):
        if not os.path.exists(Config.AUGMENTED_DATASET_PATH):
            from data.augment_data import augment_dataset
            augment_dataset()
        from ml.train_model import train_and_evaluate
        train_and_evaluate()
    if force or not os.path.exists(Config.COMPANY_MODEL_PATH):
        from ml.company_train import train as train_company
        train_company()


def db_is_stale() -> bool:
    """True when the shipments table is missing/empty or every active ETA is in the past."""
    import sqlite3
    if not os.path.exists(Config.DB_PATH):
        return True
    try:
        with sqlite3.connect(Config.DB_PATH) as c:
            row = c.execute("SELECT COUNT(*), MAX(estimated_arrival) FROM shipments "
                            "WHERE status != 'Delivered'").fetchone()
        return not row[0] or row[1] < date.today().isoformat()
    except Exception:
        return True


def ensure_ready(verbose: bool = True):
    log = print if verbose else (lambda *a, **k: None)
    if Config.VERCEL_RUNTIME:
        if not Config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required on Vercel. Configure managed PostgreSQL and import the demo/production data before deployment.")
        if not models_present():
            raise RuntimeError("Model artifacts are missing. The Vercel build hook must complete before serving traffic.")
        from db.models import Base as CoreBase, engine as core_engine
        from db.models_extended import Base as ExtendedBase, engine as extended_engine, ensure_contact_schema
        CoreBase.metadata.create_all(core_engine)
        ExtendedBase.metadata.create_all(extended_engine)
        ensure_contact_schema()
        from db.models import ShipmentModel, get_session
        with get_session() as session:
            if session.query(ShipmentModel).count() == 0:
                raise RuntimeError("The configured DATABASE_URL has no shipments. Import the demo/company data before deployment.")
        return
    if db_is_stale():
        log("[bootstrap] Shipment data missing or stale - reseeding database...")
        from db.reseed_db import reseed
        reseed()
    from db.models_extended import ensure_contact_schema
    ensure_contact_schema()
    if not models_present():
        log("[bootstrap] ML artefacts missing - training models (one-time, ~30s)...")
        train_models()


if __name__ == "__main__":
    ensure_ready()
