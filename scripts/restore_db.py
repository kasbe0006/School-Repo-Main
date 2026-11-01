"""Restore a verified SQLite backup into the configured database.

Usage:
    python scripts/restore_db.py backups/ucms_20261102_010000.db
    python scripts/restore_db.py backups/ucms_20261102_010000.db --yes

Stop the web server before replacing the live database.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import config  # noqa: E402
from app.database import get_connection  # noqa: E402


def verify_backup(source: Path) -> None:
    """Verify that a backup is a readable, internally consistent SQLite database."""
    if not source.exists():
        raise FileNotFoundError(f"Backup not found: {source}")
    conn = sqlite3.connect(source)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Backup integrity check failed: {integrity}")
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            raise RuntimeError(f"Backup foreign-key check failed: {foreign_keys[:3]}")
    finally:
        conn.close()


def restore_database(source: Path, target: Path, overwrite: bool = False) -> None:
    """Restore a verified backup to the configured database path."""
    verify_backup(source)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Target exists: {target}. Use --yes to replace it.")

    target.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(source)
    target_conn = get_connection(target)
    try:
        source_conn.backup(target_conn, pages=0)
    finally:
        target_conn.close()
        source_conn.close()

    verify_backup(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a verified UCMS SQLite backup")
    parser.add_argument("backup", type=Path)
    parser.add_argument("--yes", action="store_true", help="replace the configured database")
    args = parser.parse_args()
    try:
        restore_database(args.backup, config.DB_PATH, overwrite=args.yes)
    except (FileNotFoundError, FileExistsError, RuntimeError, sqlite3.Error) as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Database restored from {args.backup} to {config.DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
