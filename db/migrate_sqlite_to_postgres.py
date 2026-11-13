"""Copy the current SQLite demo/company dataset to an empty managed PostgreSQL DB.

Run once from a trusted machine with DATABASE_URL set. Refuses non-empty targets.
"""
import os
from sqlalchemy import create_engine, inspect, MetaData, select, func, Table
from utils.config import Config
from db.models import Base as CoreBase, ShipmentModel
from db.models_extended import Base as ExtendedBase, ensure_contact_schema

if not Config.DATABASE_URL:
    raise SystemExit("Set DATABASE_URL to the managed PostgreSQL destination before importing.")
source_path = os.getenv("SQLITE_SOURCE", Config.DB_PATH)
if not os.path.isfile(source_path):
    raise SystemExit(f"SQLite source database not found: {source_path}")
source = create_engine(f"sqlite:///{source_path}")
destination = create_engine(Config.DATABASE_URL)
CoreBase.metadata.create_all(destination)
ExtendedBase.metadata.create_all(destination)
ensure_contact_schema()
with destination.begin() as conn:
    populated = []
    for table_name in inspect(destination).get_table_names():
        table = MetaData()
        table.reflect(bind=destination, only=[table_name])
        count = conn.execute(select(func.count()).select_from(table.tables[table_name])).scalar_one()
        if count:
            populated.append((table_name, count))
    if populated:
        summary = ", ".join(f"{name}={count}" for name, count in populated)
        raise SystemExit(f"Refusing to import over a non-empty destination ({summary}).")
source_meta = MetaData()
source_meta.reflect(bind=source)
destination_tables = set(inspect(destination).get_table_names())
with destination.begin() as dest_conn, source.connect() as source_conn:
    for table_name in source_meta.sorted_tables:
        if table_name.name not in destination_tables:
            continue
        table = source_meta.tables[table_name.name]
        destination_columns = {column["name"] for column in inspect(destination).get_columns(table_name.name)}
        rows = source_conn.execute(select(table)).mappings().all()
        if rows:
            values = [{key: value for key, value in dict(row).items() if key in destination_columns} for row in rows]
            destination_table = Table(table_name.name, MetaData(), autoload_with=destination)
            dest_conn.execute(destination_table.insert(), values)
print(f"Imported current database tables into managed PostgreSQL from {source_path}.")
