"""
/api/auth: login and "who am I".
    POST /api/auth/login
    GET  /api/auth/me
"""

import sqlite3
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from app import config
from app.database import get_db, transaction
from app.repositories.users import (get_user_by_email, get_user_password_hash, update_last_login,
                                    update_password)
from app.schemas.auth import LoginRequest, PasswordChangeRequest
from app.security import create_access_token, get_current_user, hash_password, load_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
_login_failures: dict[str, list[float]] = {}
_login_failures_lock = threading.Lock()


def _login_key(request: Request, email: str) -> str:
    """Keep failures separate per client and account without storing passwords."""
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{email.strip().lower()}"


def _check_login_limit(key: str) -> None:
    now = time.monotonic()
    with _login_failures_lock:
        recent = [stamp for stamp in _login_failures.get(key, []) if now - stamp < config.LOGIN_FAILURE_WINDOW_SECONDS]
        _login_failures[key] = recent
        if len(recent) >= config.LOGIN_MAX_FAILURES:
            raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.",
                                headers={"Retry-After": str(config.LOGIN_FAILURE_WINDOW_SECONDS)})


def _record_login_failure(key: str) -> None:
    with _login_failures_lock:
        _login_failures.setdefault(key, []).append(time.monotonic())


def _clear_login_failures(key: str) -> None:
    with _login_failures_lock:
        _login_failures.pop(key, None)


@router.post("/login")
def login(request: Request, body: LoginRequest, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """
    Check email + password and return a JWT.
    Wrong email and wrong password give the SAME message, so an attacker cannot
    find out which emails exist.
    """
    key = _login_key(request, body.email)
    _check_login_limit(key)
    user = get_user_by_email(conn, body.email)
    if user is None or not verify_password(body.password, user["password_hash"]):
        _record_login_failure(key)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="This account is disabled. Please contact the admin.")

    with transaction(conn, actor_id=user["id"]):
        update_last_login(conn, user["id"])
    _clear_login_failures(key)

    return {
        "access_token": create_access_token(user["id"], user["role"]),
        "token_type": "bearer",
        "role": user["role"],
        "user": load_user(conn, user["id"]),
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    """The logged-in user, with teacher_id / student_id / department_id if they have one."""
    return user


@router.post("/change-password")
def change_password(body: PasswordChangeRequest, user: dict = Depends(get_current_user),
                    conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Change the authenticated user's password after verifying the current one."""
    password_hash = get_user_password_hash(conn, user["id"])
    if password_hash is None or not verify_password(body.current_password, password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    with transaction(conn, actor_id=user["id"]):
        update_password(conn, user["id"], hash_password(body.new_password))
    return {"detail": "Password changed successfully"}
