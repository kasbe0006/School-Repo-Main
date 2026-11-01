"""
Start UCMS with one command:

    python run.py

- If ucms.db does not exist yet (or is empty), it is created with the school schema.
- Then the web server starts at http://localhost:8000 (API docs at /docs).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn  # noqa: E402

from app import config  # noqa: E402
from app.database import fetch_value, get_connection, transaction  # noqa: E402
from app.repositories.users import insert_user  # noqa: E402
from app.security import hash_password  # noqa: E402
from scripts.init_db import init_database, list_tables  # noqa: E402
from scripts.migrate_school import migrate_school_schema  # noqa: E402
from scripts.seed import seed_database  # noqa: E402


def ensure_database() -> None:
    """Create the schema and optionally seed development data."""
    conn = get_connection()
    try:
        has_tables = bool(list_tables(conn))
        has_users = has_tables and fetch_value(conn, "SELECT COUNT(*) FROM users") > 0
    finally:
        conn.close()

    if not has_tables:
        print("Creating the database schema ...")
        init_database(config.DB_PATH, verbose=False)
    else:
        migration_conn = get_connection(config.DB_PATH)
        try:
            migrate_school_schema(migration_conn)
        finally:
            migration_conn.close()
    if config.AUTO_SEED and not has_users:
        print("Seeding demo data (takes a few seconds) ...")
        seed_database(config.DB_PATH)
    elif not config.AUTO_SEED and not has_users:
        if not config.PROVISION_ADMIN_EMAIL or len(config.PROVISION_ADMIN_PASSWORD) < 12:
            raise RuntimeError(
                "The database has no users. Set PROVISION_ADMIN_EMAIL and a "
                "PROVISION_ADMIN_PASSWORD of at least 12 characters for the first start."
            )
        conn = get_connection()
        try:
            with transaction(conn):
                insert_user(
                    conn,
                    config.PROVISION_ADMIN_EMAIL,
                    hash_password(config.PROVISION_ADMIN_PASSWORD),
                    "admin",
                )
        finally:
            conn.close()
        print(f"Created the first administrator: {config.PROVISION_ADMIN_EMAIL}")


def main() -> None:
    """Prepare the database, then run the web server."""
    ensure_database()
    host_for_link = "localhost" if config.HOST in ("127.0.0.1", "0.0.0.0") else config.HOST
    print(f"\nSchool ERP is running at http://{host_for_link}:{config.PORT}   (API docs: /docs)")
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
