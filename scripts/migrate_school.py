"""Apply the small school-specific schema additions to an existing database."""

import sqlite3
from pathlib import Path


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def _add_meal_content_kind(conn: sqlite3.Connection) -> None:
    """Rebuild older school-content tables whose CHECK omitted meal schedules."""
    definition = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'school_content'"
    ).fetchone()
    if not definition or "'meal'" in definition[0]:
        return
    conn.execute("DROP TRIGGER IF EXISTS trg_school_content_updated_at")
    conn.execute(
        """CREATE TABLE school_content_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK (kind IN ('notice','activity','gallery','admission','meal')),
            title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 3 AND 200),
            description TEXT NOT NULL CHECK (length(trim(description)) BETWEEN 3 AND 10000),
            event_date TEXT NULL,
            event_end_date TEXT NULL,
            location TEXT NULL,
            image_url TEXT NULL,
            video_url TEXT NULL,
            documents_required TEXT NULL,
            scholarship_info TEXT NULL,
            is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0,1)),
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            CHECK (event_end_date IS NULL OR event_date IS NULL OR event_end_date >= event_date)
        )"""
    )
    conn.execute(
        """INSERT INTO school_content_new
           SELECT id, kind, title, description, event_date, event_end_date, location,
                  image_url, video_url, documents_required, scholarship_info, is_published,
                  created_by, created_at, updated_at
           FROM school_content"""
    )
    conn.execute("DROP TABLE school_content")
    conn.execute("ALTER TABLE school_content_new RENAME TO school_content")


def migrate_school_schema(conn: sqlite3.Connection) -> None:
    """Add school-specific fields and content tables when they are missing."""
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
        conn.execute(
            """CREATE TABLE IF NOT EXISTS school_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK (kind IN ('notice','activity','gallery','admission','meal')),
                title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 3 AND 200),
                description TEXT NOT NULL CHECK (length(trim(description)) BETWEEN 3 AND 10000),
                event_date TEXT NULL,
                event_end_date TEXT NULL,
                location TEXT NULL,
                image_url TEXT NULL,
                video_url TEXT NULL,
                documents_required TEXT NULL,
                scholarship_info TEXT NULL,
                is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0,1)),
                created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK (event_end_date IS NULL OR event_date IS NULL OR event_end_date >= event_date)
            )"""
        )
        _add_meal_content_kind(conn)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS school_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                school_name TEXT NOT NULL,
                school_short_name TEXT NOT NULL,
                school_tagline TEXT NOT NULL,
                school_address TEXT NOT NULL DEFAULT '',
                school_phone TEXT NOT NULL DEFAULT '',
                school_email TEXT NOT NULL DEFAULT '',
                logo_url TEXT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        conn.execute(
            """INSERT OR IGNORE INTO school_settings
               (id, school_name, school_short_name, school_tagline)
               VALUES (1, 'Zilla Parishad Primary School, Mamdapur',
                       'ZPPS Mamdapur', 'School management for ZPPS Mamdapur')"""
        )
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS trg_school_settings_updated_at
               AFTER UPDATE ON school_settings
               FOR EACH ROW WHEN NEW.updated_at = OLD.updated_at
               BEGIN
                   UPDATE school_settings SET updated_at = datetime('now') WHERE id = NEW.id;
               END"""
        )
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS trg_school_content_updated_at
               AFTER UPDATE ON school_content
               FOR EACH ROW WHEN NEW.updated_at = OLD.updated_at
               BEGIN
                   UPDATE school_content SET updated_at = datetime('now') WHERE id = NEW.id;
               END"""
        )
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
