"""
Application settings.

All settings come from environment variables. For convenience we also read a
`.env` file in the project folder (see `.env.example`). We use a tiny
hand-written loader instead of an extra library, so there is nothing magic here.
"""

import os
from pathlib import Path

# Project root folder = the folder that contains `app/`, `sql/`, `scripts/` ...
BASE_DIR: Path = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """
    Read simple KEY=VALUE lines from a .env file into os.environ.

    Real environment variables always win (we use setdefault), so you can
    still override anything from the command line.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        # Skip empty lines and comments
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


load_env_file(BASE_DIR / ".env")


def resolve_path(value: str) -> Path:
    """Turn a relative path from the settings into an absolute path inside BASE_DIR."""
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


# ---- Database ----
DB_PATH: Path = resolve_path(os.getenv("UCMS_DB_PATH", "ucms.db"))
SQL_DIR: Path = BASE_DIR / "sql"
BACKUP_DIR: Path = BASE_DIR / "backups"
MEDIA_DIR: Path = resolve_path(os.getenv("MEDIA_DIR", "media"))
MAX_MEDIA_BYTES: int = int(os.getenv("MAX_MEDIA_BYTES", str(50 * 1024 * 1024)))

# ---- Auth ----
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# ---- Runtime environment ----
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip().lower()
AUTO_SEED: bool = os.getenv("AUTO_SEED", "false").strip().lower() in {"1", "true", "yes", "on"}
PROVISION_ADMIN_EMAIL: str = os.getenv("PROVISION_ADMIN_EMAIL", "").strip().lower()
PROVISION_ADMIN_PASSWORD: str = os.getenv("PROVISION_ADMIN_PASSWORD", "")
SCHOOL_NAME: str = os.getenv("SCHOOL_NAME", "Zilla Parishad Primary School, Mamdapur")
SCHOOL_SHORT_NAME: str = os.getenv("SCHOOL_SHORT_NAME", "ZPPS Mamdapur")
SCHOOL_TAGLINE: str = os.getenv("SCHOOL_TAGLINE", "School management for ZPPS Mamdapur")
LOGIN_MAX_FAILURES: int = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_FAILURE_WINDOW_SECONDS: int = int(os.getenv("LOGIN_FAILURE_WINDOW_SECONDS", "300"))

# ---- Web server ----
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))
FRONTEND_DIR: Path = BASE_DIR / "frontend"


def validate_production_settings() -> None:
    """Reject settings that would make a production deployment unsafe."""
    if ENVIRONMENT != "production":
        return
    if JWT_SECRET == "dev-secret-change-me" or len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be a random value of at least 32 characters in production")
    if AUTO_SEED:
        raise RuntimeError("AUTO_SEED must be false in production")


validate_production_settings()
