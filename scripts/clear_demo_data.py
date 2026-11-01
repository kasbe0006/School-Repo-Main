"""Remove seeded records and create the first real school administrator.

Usage:
    python scripts/clear_demo_data.py admin@school.edu "a-unique-password"

The schema and the single-school settings row are preserved. All users and
dependent operational records are removed, so run this only before entering
real school data.
"""

import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import config  # noqa: E402
from app.database import get_connection, transaction  # noqa: E402
from app.repositories.users import insert_user  # noqa: E402
from app.security import hash_password  # noqa: E402


def clear_demo_data(email: str, password: str) -> int:
    conn = get_connection(config.DB_PATH)
    try:
        table_names = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' AND name NOT IN ('school_settings', '_audit_actor')"
            ).fetchall()
        ]
        conn.execute("PRAGMA foreign_keys = OFF")
        with transaction(conn):
            for table_name in table_names:
                conn.execute(f'DELETE FROM "{table_name}"')
            insert_user(conn, email, hash_password(password), "admin")
        conn.execute("PRAGMA foreign_keys = ON")
        return len(table_names)
    finally:
        conn.close()


def main() -> int:
    if len(sys.argv) > 3 or len(sys.argv) < 2:
        print("Usage: python scripts/clear_demo_data.py ADMIN_EMAIL [PASSWORD]")
        return 2
    email = sys.argv[1].strip().lower()
    password = sys.argv[2] if len(sys.argv) == 3 else getpass.getpass("New admin password: ")
    if len(password) < 12:
        print("ERROR: password must be at least 12 characters.")
        return 2
    deleted_tables = clear_demo_data(email, password)
    print(f"Removed demo records from {deleted_tables} tables.")
    print(f"Created administrator: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
