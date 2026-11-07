"""Bounded FIFO queue for all expensive tools; single uvicorn worker required."""
import asyncio
import threading
import time
from collections import deque
from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from anyio import CancelScope
from . import accounts, config
from .auth import get_session_user


class Workload:
    def __init__(self):
        self.lock = threading.Lock()
        self.waiting = deque()
        self.running = None
        self.completed = self.failed = self.rejected = 0
        self.max_waiting = 3
        self.wait_seconds = 30

    def admit(self, user, tool):
        entry = {"user": user, "tool": tool, "queued_at": time.time(), "ticket": object()}
        with self.lock:
            entries = list(self.waiting) + ([self.running] if self.running else [])
            if any(e["user"].casefold() == user.casefold() for e in entries):
                self.rejected += 1
                raise HTTPException(429, "Vous avez déjà une conversion en cours ou en attente.", headers={"Retry-After":"5"})
            if len(entries) >= self.max_waiting + 1:
                self.rejected += 1
                raise HTTPException(429, "La file de conversion est pleine. Réessayez dans un instant.", headers={"Retry-After":"30"})
            self.waiting.append(entry)
        return entry

    def start(self, entry):
        with self.lock:
            if self.running is None and self.waiting and self.waiting[0] is entry:
                self.waiting.popleft()
                entry["started_at"] = time.time()
                self.running = entry
                return True
            return False

    def release(self, entry, success=False):
        with self.lock:
            if self.running is entry:
                self.running = None
                if success: self.completed += 1
                else: self.failed += 1
            else:
                self.waiting = deque(e for e in self.waiting if e is not entry)

    def snapshot(self):
        with self.lock:
            clean = lambda e: {k:v for k,v in e.items() if k != "ticket"}
            return {"running": clean(self.running) if self.running else None,
                    "waiting": [clean(e) for e in self.waiting], "completed": self.completed,
                    "failed": self.failed, "rejected": self.rejected,
                    "max_running": 1, "max_waiting": self.max_waiting, "wait_seconds": self.wait_seconds}


workload = Workload()


def charge_quota(user):
    key = user.casefold()
    limit = 30 if user == config.USERNAME else 10
    with accounts.database() as db:
        db.execute("CREATE TABLE IF NOT EXISTS conversion_usage (username TEXT NOT NULL, created REAL NOT NULL)")
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM conversion_usage WHERE created < ?", (time.time()-3600,))
        count = db.execute("SELECT count(*) FROM conversion_usage WHERE username=?", (key,)).fetchone()[0]
        if count >= limit:
            raise HTTPException(429, f"Quota atteint : {limit} conversions par heure. Réessayez plus tard.", headers={"Retry-After":"3600"})
        db.execute("INSERT INTO conversion_usage VALUES (?,?)", (key,time.time()))


class HeavyRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request):
            user = await run_in_threadpool(get_session_user, request.cookies.get(config.SESSION_COOKIE))
            if not user:
                raise HTTPException(401, "Non authentifié.")
            entry = workload.admit(user, self.path)
            success = False
            try:
                deadline = time.monotonic() + workload.wait_seconds
                while not workload.start(entry):
                    if time.monotonic() >= deadline:
                        raise HTTPException(429, "Attente trop longue. Réessayez dans un instant.", headers={"Retry-After":"30"})
                    await asyncio.sleep(.1)
                # Keep the slot until the synchronous worker has actually finished,
                # even if its HTTP client goes away. No parallel heavy work on cancel.
                with CancelScope(shield=True):
                    current = await run_in_threadpool(get_session_user, request.cookies.get(config.SESSION_COOKIE))
                    if not current:
                        raise HTTPException(401, "Session expirée ou compte suspendu.")
                    await run_in_threadpool(charge_quota, user)
                    response = await original(request)
                    success = response.status_code < 400
                    return response
            finally:
                workload.release(entry, success)
        return handler
