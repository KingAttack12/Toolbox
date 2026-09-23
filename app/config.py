"""Configuration par variables d'environnement (avec support fichier .env minimal, sans dépendance)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # dossier toolbox/


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


USERNAME: str = _get("TOOLBOX_USERNAME", "admin")
PASSWORD_HASH: str = _get("TOOLBOX_PASSWORD_HASH", "")
SESSION_SECRET: str = _get("TOOLBOX_SESSION_SECRET", "dev-secret-change-me")

DATA_DIR: Path = Path(_get("TOOLBOX_DATA_DIR", str(BASE_DIR / "data" / "tmp")))
TMP_TTL_HOURS: int = _get_int("TOOLBOX_TMP_TTL_HOURS", 2)
MAX_TEXT_CHARS: int = _get_int("TOOLBOX_MAX_TEXT_CHARS", 500_000)
MAX_UPLOAD_MB: int = _get_int("TOOLBOX_MAX_UPLOAD_MB", 50)

HOST: str = _get("TOOLBOX_HOST", "127.0.0.1")
PORT: int = _get_int("TOOLBOX_PORT", 8000)

# IA facultative : vide = désactivée (Phase 6)
AI_API_KEY: str = _get("AI_API_KEY", "")
AI_PROVIDER: str = _get("AI_PROVIDER", "")
AI_MODEL: str = _get("AI_MODEL", "")

SESSION_COOKIE = "toolbox_session"
SESSION_TTL_SECONDS = 12 * 3600
