"""Persistence for the single ZPPS school profile."""

import sqlite3

from app.database import fetch_one


DEFAULTS = {
    "school_name": "Zilla Parishad Primary School, Mamdapur",
    "school_short_name": "ZPPS Mamdapur",
    "school_tagline": "School management for ZPPS Mamdapur",
    "school_address": "Mamdapur",
    "school_phone": "",
    "school_email": "",
    "logo_url": None,
}


def get_settings(conn: sqlite3.Connection) -> dict:
    row = fetch_one(conn, "SELECT * FROM school_settings WHERE id = 1")
    values = {**DEFAULTS, **(row or {})}
    return {key: values[key] for key in DEFAULTS}


def update_settings(conn: sqlite3.Connection, changes: dict) -> dict:
    fields = [key for key in DEFAULTS if key in changes]
    if fields:
        assignments = ", ".join(f"{field} = ?" for field in fields)
        conn.execute(
            f"UPDATE school_settings SET {assignments}, updated_at = datetime('now') WHERE id = 1",
            tuple(changes[field] for field in fields),
        )
    return get_settings(conn)
