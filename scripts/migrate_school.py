"""Apply the small school-specific schema additions to an existing database."""

import sqlite3
from pathlib import Path


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def migrate_school_schema(conn: sqlite3.Connection) -> None:
    """Add grade/section and guardian email fields when they are missing."""
    student_columns = _columns(conn, "students")
    profile_columns = _columns(conn, "student_profiles")
    conn.execute("BEGIN IMMEDIATE")
    try:
        if "grade_level" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN grade_level INTEGER NOT NULL DEFAULT 1")
        if "section" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN section TEXT NOT NULL DEFAULT 'A'")
        if "guardian_email" not in profile_columns:
            conn.execute("ALTER TABLE student_profiles ADD COLUMN guardian_email TEXT")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


if __name__ == "__main__":
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    from app import config
    from app.database import get_connection

    connection = get_connection(config.DB_PATH)
    try:
        migrate_school_schema(connection)
    finally:
        connection.close()
    print(f"School schema ready: {config.DB_PATH}")
