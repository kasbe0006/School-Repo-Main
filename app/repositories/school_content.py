"""Persistence for public school content."""

import sqlite3

from app.database import execute, fetch_all, fetch_one, where_clause
from app.pagination import paginate

SELECT = """
SELECT c.id, c.kind, c.title, c.description, c.event_date, c.event_end_date,
       c.location, c.image_url, c.video_url, c.documents_required,
       c.scholarship_info, c.is_published, c.created_by,
       u.email AS created_by_email, c.created_at, c.updated_at
FROM school_content c
JOIN users u ON u.id = c.created_by
"""


def list_content(conn: sqlite3.Connection, args: dict, kind: str | None, admin: bool) -> dict:
    conditions, params = [], []
    if kind:
        conditions.append("c.kind = ?")
        params.append(kind)
    if not admin:
        conditions.append("c.is_published = 1")
    if not args["sort"]:
        args = {**args, "sort": "created_at", "order": "desc"}
    return paginate(
        conn, SELECT + where_clause(conditions), params, args,
        search_columns=["c.title", "c.description", "c.location", "c.scholarship_info"],
        sort_columns=["id", "kind", "title", "event_date", "created_at"],
        default_sort="created_at",
    )


def get_content(conn: sqlite3.Connection, content_id: int) -> dict | None:
    return fetch_one(conn, SELECT + " WHERE c.id = ?", (content_id,))


def insert_content(conn: sqlite3.Connection, data: dict, created_by: int) -> int:
    return execute(
        conn,
        """INSERT INTO school_content
           (kind, title, description, event_date, event_end_date, location,
            image_url, video_url, documents_required, scholarship_info,
            is_published, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["kind"], data["title"], data["description"], data.get("event_date"),
            data.get("event_end_date"), data.get("location"), data.get("image_url"),
            data.get("video_url"), data.get("documents_required"), data.get("scholarship_info"),
            int(data.get("is_published", True)), created_by,
        ),
    )


def delete_content(conn: sqlite3.Connection, content_id: int) -> int:
    return conn.execute("DELETE FROM school_content WHERE id = ?", (content_id,)).rowcount
