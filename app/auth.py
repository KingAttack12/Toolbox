"""Authentification privée mono-utilisateur : PBKDF2 stdlib + sessions à jetons opaques."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status

from . import config

# token -> {"username": str, "expires": float}
_sessions: dict[str, dict] = {}

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Génère un hash stockable : pbkdf2_sha256$iterations$salt_hex$hash_hex."""
    if len(password) < 8:
        raise ValueError("Mot de passe trop court (min 8 caractères).")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"username": username, "expires": time.time() + config.SESSION_TTL_SECONDS}
    _purge()
    return token


def destroy_session(token: Optional[str]) -> None:
    if token and token in _sessions:
        del _sessions[token]


def get_session_user(token: Optional[str]) -> Optional[str]:
    if not token or token not in _sessions:
        return None
    sess = _sessions[token]
    if sess["expires"] < time.time():
        del _sessions[token]
        return None
    return sess["username"]


def _purge() -> None:
    now = time.time()
    expired = [t for t, s in _sessions.items() if s["expires"] < now]
    for t in expired:
        del _sessions[t]


def get_current_user(
    toolbox_session: Optional[str] = Cookie(default=None, alias=config.SESSION_COOKIE),
) -> str:
    user = get_session_user(toolbox_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")
    return user


def check_credentials(username: str, password: str) -> bool:
    if not config.PASSWORD_HASH:
        return False
    if not hmac.compare_digest(username, config.USERNAME):
        # compare_digest anti-timing + vérification factice pour ne pas fuiter l'existence
        verify_password("factice", config.PASSWORD_HASH)
        return False
    return verify_password(password, config.PASSWORD_HASH)
