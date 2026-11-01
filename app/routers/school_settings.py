"""Admin-managed ZPPS school identity and contact settings."""

import sqlite3
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app import config
from app.database import get_db, transaction
from app.repositories import school_settings as repo
from app.security import require_role

router = APIRouter(prefix="/settings", tags=["settings"])
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}


async def _save_logo(upload: UploadFile | None) -> str | None:
    if upload is None or not upload.filename:
        return None
    if upload.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=415, detail="Logo must be PNG, JPEG, WebP or SVG")
    data = await upload.read(config.MAX_MEDIA_BYTES + 1)
    if len(data) > config.MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="Logo file is too large")
    config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename).suffix.lower()
    filename = f"school-logo-{uuid.uuid4().hex}{suffix}"
    (config.MEDIA_DIR / filename).write_bytes(data)
    return f"/media/{filename}"


@router.get("")
def get_school_settings(
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return repo.get_settings(conn)


@router.patch("")
async def update_school_settings(
    school_name: str = Form(..., min_length=3, max_length=200),
    school_short_name: str = Form(..., min_length=2, max_length=80),
    school_tagline: str = Form(..., min_length=3, max_length=200),
    school_address: str = Form("", max_length=300),
    school_phone: str = Form("", max_length=30),
    school_email: str = Form("", max_length=200),
    logo: UploadFile | None = File(None),
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    logo_url = await _save_logo(logo)
    changes = {
        "school_name": school_name.strip(),
        "school_short_name": school_short_name.strip(),
        "school_tagline": school_tagline.strip(),
        "school_address": school_address.strip(),
        "school_phone": school_phone.strip(),
        "school_email": school_email.strip(),
    }
    if logo_url:
        changes["logo_url"] = logo_url
    try:
        with transaction(conn, user["id"]):
            return repo.update_settings(conn, changes)
    except sqlite3.Error:
        if logo_url:
            (config.MEDIA_DIR / Path(logo_url).name).unlink(missing_ok=True)
        raise
