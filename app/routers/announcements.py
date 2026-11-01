"""
/api/announcements
    GET  /api/announcements     (everyone: only what they are allowed to see; admin sees all)
    POST /api/announcements     (admin)
"""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.database import get_db, transaction
from app.errors import found_or_404
from app.pagination import list_params
from app.repositories import announcements as repo
from app.repositories.departments import get_department
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from app.security import get_current_user, require_role

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("")
def list_announcements(
    list_args: dict = Depends(list_params),
    include_expired: bool = Query(False, description="Admins only"),
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Announcements visible to this user (by role and department), newest first."""
    return repo.list_announcements(conn, list_args, user, include_expired)


@router.post("", status_code=201)
def create_announcement(body: AnnouncementCreate, user: dict = Depends(require_role("admin")),
                        conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Publish an announcement now."""
    if body.target_department_id is not None:
        found_or_404(get_department(conn, body.target_department_id), "Department", body.target_department_id)
    with transaction(conn, user["id"]):
        announcement_id = repo.insert_announcement(conn, body.model_dump(mode="json"), user["id"])
    return repo.get_announcement(conn, announcement_id)


@router.patch("/{announcement_id}")
def update_announcement(
    announcement_id: int,
    body: AnnouncementUpdate,
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    announcement = found_or_404(repo.get_announcement(conn, announcement_id), "Announcement", announcement_id)
    changes = body.model_dump(mode="json", exclude_unset=True)
    if "target_department_id" in changes and changes["target_department_id"] is not None:
        found_or_404(get_department(conn, changes["target_department_id"]), "Department", changes["target_department_id"])
    with transaction(conn, user["id"]):
        repo.update_announcement(conn, announcement_id, changes)
    return repo.get_announcement(conn, announcement_id)


@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: int,
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
):
    found_or_404(repo.get_announcement(conn, announcement_id), "Announcement", announcement_id)
    with transaction(conn, user["id"]):
        repo.delete_announcement(conn, announcement_id)
