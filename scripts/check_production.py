"""Validate production configuration and database readiness before launch."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import config  # noqa: E402
from app.database import fetch_value, get_connection  # noqa: E402
from scripts.init_db import list_tables  # noqa: E402


def check_production() -> None:
    """Raise a clear error if the configured production instance is unsafe."""
    if config.ENVIRONMENT != "production":
        raise RuntimeError("ENVIRONMENT must be production")
    if config.AUTO_SEED:
        raise RuntimeError("AUTO_SEED must be false")
    if not config.DB_PATH.exists():
        raise RuntimeError(f"Database does not exist: {config.DB_PATH}")

    conn = get_connection(config.DB_PATH)
    try:
        if not list_tables(conn):
            raise RuntimeError("Database has no schema")
        user_count = fetch_value(conn, "SELECT COUNT(*) FROM users")
        if not user_count:
            raise RuntimeError("Database has no administrator or other users")
        integrity = fetch_value(conn, "PRAGMA integrity_check")
        if integrity != "ok":
            raise RuntimeError(f"Database integrity check failed: {integrity}")
    finally:
        conn.close()


def main() -> int:
    try:
        check_production()
    except RuntimeError as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Production configuration is ready: {config.DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
