"""Authentification privée mono-utilisateur : PBKDF2 stdlib + sessions à jetons opaques."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import threading
_session_lock = threading.RLock()
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status

from . import config, accounts

# token -> {"username": str, "expires": float}
_sessions: dict[str, dict] = {}

_ITERATIONS = 600_000


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


def create_session(username: str, version=None) -> str:
    if version is None:
        row=accounts.active(username) if username != config.USERNAME else None
        version=row['version'] if row else 0
    token=secrets.token_urlsafe(32)
    with _session_lock:
        _purge()
        existing=[key for key,value in _sessions.items() if value['username']==username]
        for key in existing[:-4]:_sessions.pop(key,None)
        _sessions[token]={"username":username,"expires":time.time()+config.SESSION_TTL_SECONDS,"version":version}
    return token


def destroy_session(token: Optional[str]) -> None:
    with _session_lock:_sessions.pop(token,None)


def get_session_user(token: Optional[str]) -> Optional[str]:
    with _session_lock:
        sess=_sessions.get(token)
        if not sess:return None
        if sess['expires']<time.time():_sessions.pop(token,None);return None
        username=sess['username']
        if username!=config.USERNAME:
            row=accounts.active(username)
            if not row or row['version']!=sess.get('version',0):_sessions.pop(token,None);return None
        return username


def _purge() -> None:
    with _session_lock:
        for token,session in list(_sessions.items()):
            if session['expires']<time.time():_sessions.pop(token,None)


def authenticate_session(username,password):
    if username==config.USERNAME:
        return create_session(username) if check_credentials(username,password) else None
    row=accounts.active(username)
    valid=verify_password(password,row['password_hash'] if row else config.PASSWORD_HASH)
    return create_session(username,version=row['version']) if row and valid else None


def get_current_user(
    toolbox_session: Optional[str] = Cookie(default=None, alias=config.SESSION_COOKIE),
) -> str:
    user = get_session_user(toolbox_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")
    return user


def check_credentials(username: str, password: str) -> bool:
    if username == config.USERNAME:
        return bool(config.PASSWORD_HASH) and verify_password(password, config.PASSWORD_HASH)
    row = accounts.active(username)
    stored = row[0] if row else config.PASSWORD_HASH
    valid = verify_password(password, stored) if stored else False
    return bool(row) and valid


def get_admin(user: str = Depends(get_current_user)) -> str:
    if user != config.USERNAME:
        raise HTTPException(status_code=403, detail="Accès réservé au propriétaire.")
    return user


def revoke_user(username):
    if username == config.USERNAME: return
    with accounts.database() as db:
        db.execute("UPDATE accounts SET version=version+1 WHERE username=?", (username,))
        db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)", (username,"Sessions révoquées",time.time()))
