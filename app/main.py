"""
The FastAPI application: API under /api, frontend files under /.

Start it with:  python run.py      (or: uvicorn app.main:app --reload)
API docs:       http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
import sqlite3

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.database import enable_wal, fetch_value, get_connection
from app.errors import register_exception_handlers
from app.routers import (announcements, assessments, attendance, audit_logs, auth, billing, courses,
                         dashboard, departments, enrollments, offerings, reports, rooms, schedules,
                         semesters, students, teachers, school_content, school_settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at startup: make sure the schema exists and WAL mode is on.
    (Seeding demo data is done by run.py / scripts/seed.py, not here.)
    """
    from scripts.init_db import init_database, list_tables   # imported here: only needed at startup
    from scripts.migrate_school import migrate_school_schema

    conn = get_connection()
    try:
        has_tables = bool(list_tables(conn))
        if has_tables:
            enable_wal(conn)
    finally:
        conn.close()
    if not has_tables:
        init_database(config.DB_PATH, verbose=False)
    else:
        migration_conn = get_connection(config.DB_PATH)
        try:
            migrate_school_schema(migration_conn)
        finally:
            migration_conn.close()
    yield


app = FastAPI(
    title="School ERP API",
    description="School management system for grades 1-12: FastAPI + raw SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)
register_exception_handlers(app)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add browser security headers without changing application responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if config.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Every router lives under /api
for module in (auth, dashboard, departments, teachers, students, courses, rooms, semesters, offerings,
               schedules, enrollments, attendance, assessments, billing, announcements, school_content,
               school_settings, audit_logs, reports):
    app.include_router(module.router, prefix="/api")

# The frontend: plain files. Mounted LAST, so /api/... routes win.
# html=True serves index.html for "/".
@app.get("/api/config", include_in_schema=False)
def public_config() -> dict[str, str | None]:
    """Return non-sensitive branding settings used by the frontend."""
    from app.repositories.school_settings import get_settings
    conn = get_connection()
    try:
        return get_settings(conn)
    finally:
        conn.close()


@app.get("/health", include_in_schema=False, response_model=None)
def health() -> dict | JSONResponse:
    """Return a lightweight readiness check for hosting providers."""
    conn = get_connection()
    try:
        user_count = fetch_value(conn, "SELECT COUNT(*) FROM users")
    except sqlite3.Error:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    finally:
        conn.close()
    if not user_count:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": "no_users"})
    return {"status": "ok"}


config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")
app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
