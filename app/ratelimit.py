"""Rate limiting en mémoire pour les endpoints sensibles (anti brute-force).

Règle : 5 tentatives échouées / minute / IP sur le login, sinon HTTP 429.
Uvicorn n'écoute que sur 127.0.0.1 : tout passe par Nginx qui écrase
X-Real-IP avec la vraie IP client, donc cet header est fiable ici.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60

_attempts: dict[str, deque[float]] = {}
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    header = request.headers.get("x-real-ip", "")
    if header:
        return header.strip()[:64]
    if request.client:
        return request.client.host[:64]
    return "unknown"


def _prune(ip: str, now: float) -> deque[float]:
    dq = _attempts.get(ip)
    if dq is None:
        dq = deque()
        _attempts[ip] = dq
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()
    return dq


def is_limited(ip: str) -> bool:
    with _lock:
        return len(_prune(ip, time.time())) >= MAX_ATTEMPTS


def record_failure(ip: str) -> None:
    with _lock:
        _prune(ip, time.time()).append(time.time())


def clear(ip: str) -> None:
    with _lock:
        _attempts.pop(ip, None)


def limited_response() -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"ok": False, "error": "Trop de tentatives. Réessayez dans une minute."},
        headers={"Retry-After": str(WINDOW_SECONDS)},
    )
