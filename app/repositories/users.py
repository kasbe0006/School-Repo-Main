"""Raw SQL for the users table (login accounts)."""

import sqlite3

from app.database import execute, fetch_one


def get_user_by_email(conn: sqlite3.Connection, email: str) -> dict | None:
    """Find a user by email. The column is COLLATE NOCASE, so the case does not matter."""
    return fetch_one(conn, "SELECT * FROM users WHERE email = ?", (email.strip(),))


def insert_user(conn: sqlite3.Connection, email: str, password_hash: str, role: str) -> int:
    """Create a login account and return its id."""
    return execute(
        conn,
        "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
        (email.strip().lower(), password_hash, role),
    )


def update_last_login(conn: sqlite3.Connection, user_id: int) -> None:
    """Remember when the user last logged in."""
    conn.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user_id,))


def set_user_active(conn: sqlite3.Connection, user_id: int, is_active: bool) -> None:
    """Enable or disable a login account."""
    conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))


def get_user_password_hash(conn: sqlite3.Connection, user_id: int) -> str | None:
    """Return the password hash for one user."""
    row = fetch_one(conn, "SELECT password_hash FROM users WHERE id = ?", (user_id,))
    return row["password_hash"] if row else None


def update_password(conn: sqlite3.Connection, user_id: int, password_hash: str) -> None:
    """Replace one user's password hash."""
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
