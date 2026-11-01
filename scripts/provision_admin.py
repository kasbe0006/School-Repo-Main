"""Create the first administrator account for a production database.

Usage:
    python scripts/provision_admin.py admin@school.edu

The password is entered interactively and is never echoed or stored in a file.
"""

import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import get_connection, transaction  # noqa: E402
from app.repositories.users import get_user_by_email, insert_user  # noqa: E402
from app.security import hash_password  # noqa: E402
from scripts.init_db import init_database, list_tables  # noqa: E402


def provision_admin(email: str, password: str) -> int:
    """Create one administrator in the configured database."""
    email = email.strip().lower()
    if len(email) < 3 or "@" not in email:
        raise ValueError("Provide a valid administrator email address")
    if len(password) < 12:
        raise ValueError("Administrator password must contain at least 12 characters")

    conn = get_connection()
    try:
        if not list_tables(conn):
            init_database()
        if get_user_by_email(conn, email):
            raise ValueError(f"A user with {email} already exists")
        with transaction(conn):
            return insert_user(conn, email, hash_password(password), "admin")
    finally:
        conn.close()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/provision_admin.py admin@school.edu")
        return 2
    try:
        password = getpass.getpass("Administrator password (12+ characters): ")
        confirmation = getpass.getpass("Repeat password: ")
        if password != confirmation:
            raise ValueError("Passwords do not match")
        user_id = provision_admin(sys.argv[1], password)
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Administrator created with id {user_id}. You can now start the application.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
