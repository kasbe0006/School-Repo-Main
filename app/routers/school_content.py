"""School notices, activities, gallery media and admission information."""

import sqlite3
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app import config
from app.database import get_db, transaction
from app.errors import found_or_404
from app.pagination import list_params
from app.repositories import school_content as repo
from app.schemas.school_content import ContentKind, SchoolContentCreate, SchoolContentUpdate
from app.security import get_current_user, require_role

router = APIRouter(prefix="/school-content", tags=["school-content"])
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}


async def _save_upload(upload: UploadFile | None, allowed: set[str], prefix: str) -> str | None:
    if upload is None or not upload.filename:
        return None
    if upload.content_type not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported {prefix} file type")
    data = await upload.read(config.MAX_MEDIA_BYTES + 1)
    if len(data) > config.MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail=f"{prefix.title()} file is too large")
    config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename).suffix.lower()
    filename = f"{prefix}-{uuid.uuid4().hex}{suffix}"
    (config.MEDIA_DIR / filename).write_bytes(data)
    return f"/media/{filename}"


def _remove_saved_upload(url: str | None) -> None:
    if url and url.startswith("/media/"):
        (config.MEDIA_DIR / Path(url).name).unlink(missing_ok=True)


@router.get("")
def list_school_content(
    list_args: dict = Depends(list_params),
    kind: ContentKind | None = Query(None),
    user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return repo.list_content(conn, list_args, kind, user["role"] == "admin")


@router.get("/public")
def public_school_content(
    list_args: dict = Depends(list_params),
    kind: ContentKind | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return repo.list_content(conn, list_args, kind, False)


@router.post("", status_code=201)
async def create_school_content(
    kind: ContentKind = Form(...),
    title: str = Form(..., min_length=3, max_length=200),
    description: str = Form(..., min_length=3, max_length=10000),
    event_date: str | None = Form(None),
    event_end_date: str | None = Form(None),
    location: str | None = Form(None, max_length=200),
    documents_required: str | None = Form(None, max_length=5000),
    scholarship_info: str | None = Form(None, max_length=5000),
    is_published: bool = Form(True),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    body = SchoolContentCreate(
        kind=kind, title=title, description=description, event_date=event_date or None,
        event_end_date=event_end_date or None, location=location or None,
        documents_required=documents_required or None, scholarship_info=scholarship_info or None,
        is_published=is_published,
    )
    image_url = await _save_upload(image, ALLOWED_IMAGE_TYPES, "image")
    try:
        video_url = await _save_upload(video, ALLOWED_VIDEO_TYPES, "video")
    except HTTPException:
        _remove_saved_upload(image_url)
        raise
    data = body.model_dump()
    data.update(image_url=image_url, video_url=video_url)
    try:
        with transaction(conn, user["id"]):
            content_id = repo.insert_content(conn, data, user["id"])
    except sqlite3.Error:
        _remove_saved_upload(image_url)
        _remove_saved_upload(video_url)
        raise
    return repo.get_content(conn, content_id)


@router.delete("/{content_id}", status_code=204)
def delete_school_content(
    content_id: int,
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
):
    content = found_or_404(repo.get_content(conn, content_id), "School content", content_id)
    with transaction(conn, user["id"]):
        repo.delete_content(conn, content_id)
    for url in (content.get("image_url"), content.get("video_url")):
        _remove_saved_upload(url)
    return JSONResponse(status_code=204, content=None)


@router.patch("/{content_id}")
async def update_school_content(
    content_id: int,
    kind: ContentKind | None = Form(None),
    title: str | None = Form(None, min_length=3, max_length=200),
    description: str | None = Form(None, min_length=3, max_length=10000),
    event_date: str | None = Form(None),
    event_end_date: str | None = Form(None),
    location: str | None = Form(None, max_length=200),
    documents_required: str | None = Form(None, max_length=5000),
    scholarship_info: str | None = Form(None, max_length=5000),
    is_published: bool | None = Form(None),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    current = found_or_404(repo.get_content(conn, content_id), "School content", content_id)
    values = {
        key: value for key, value in {
            "kind": kind, "title": title, "description": description,
            "event_date": event_date, "event_end_date": event_end_date,
            "location": location, "documents_required": documents_required,
            "scholarship_info": scholarship_info, "is_published": is_published,
        }.items() if value is not None
    }
    if not values and image is None and video is None:
        return current
    merged = {**{key: current[key] for key in (
        "kind", "title", "description", "event_date", "event_end_date", "location",
        "documents_required", "scholarship_info", "is_published",
    )}, **values}
    SchoolContentUpdate(**merged)
    new_image = await _save_upload(image, ALLOWED_IMAGE_TYPES, "image")
    try:
        new_video = await _save_upload(video, ALLOWED_VIDEO_TYPES, "video")
    except HTTPException:
        _remove_saved_upload(new_image)
        raise
    if new_image:
        values["image_url"] = new_image
    if new_video:
        values["video_url"] = new_video
    try:
        with transaction(conn, user["id"]):
            repo.update_content(conn, content_id, values)
    except sqlite3.Error:
        _remove_saved_upload(new_image)
        _remove_saved_upload(new_video)
        raise
    for old, new in ((current.get("image_url"), new_image), (current.get("video_url"), new_video)):
        if new:
            _remove_saved_upload(old)
    return repo.get_content(conn, content_id)
