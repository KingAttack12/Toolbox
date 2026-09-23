"""Système de tâches + fichiers temporaires avec nettoyage automatique.

Phase 1-2 : les outils simples répondent en synchrone, mais chaque futur
traitement fichier (PDF, média...) passera par ce module :
  job = create_job("pdf-merge") -> processing -> completed/failed
  les fichiers vivent sous DATA_DIR/<job_id>/ et expirent après TMP_TTL_HOURS.
"""
from __future__ import annotations

import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config


@dataclass
class Job:
    id: str
    type: str
    status: str = "queued"  # queued | processing | completed | failed | expired
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""
    error: str = ""
    result_file: str = ""

    def __post_init__(self) -> None:
        if not self.expires_at:
            exp = datetime.now(timezone.utc) + timedelta(hours=config.TMP_TTL_HOURS)
            self.expires_at = exp.isoformat()


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job(job_type: str) -> Job:
    job = Job(id=uuid.uuid4().hex, type=job_type)
    with _lock:
        _jobs[job.id] = job
    task_dir(job.id).mkdir(parents=True, exist_ok=True)
    return job


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            for k, v in kwargs.items():
                if hasattr(job, k):
                    setattr(job, k, v)


def task_dir(job_id: str) -> Path:
    # job_id toujours généré en interne (hex) : aucun traversal possible
    safe = "".join(c for c in job_id if c.isalnum())[:64]
    return config.DATA_DIR / safe


def ensure_data_dir() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_expired() -> int:
    """Supprime les dossiers expirés + marque les jobs. Retourne le nb supprimé."""
    removed = 0
    now = datetime.now(timezone.utc)
    with _lock:
        items = list(_jobs.items())
    for jid, job in items:
        try:
            exp = datetime.fromisoformat(job.expires_at)
        except ValueError:
            continue
        if exp < now and job.status != "expired":
            d = task_dir(jid)
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
            update_job(jid, status="expired")
    # Sécurité : supprime aussi tout dossier orphelin plus vieux que TTL
    try:
        ttl = time.time() - config.TMP_TTL_HOURS * 3600
        for child in config.DATA_DIR.iterdir():
            if child.is_dir() and child.stat().st_mtime < ttl and child.name not in _jobs:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
    except FileNotFoundError:
        pass
    return removed


def start_cleanup_thread(interval_seconds: int = 600) -> threading.Thread:
    def _loop() -> None:
        while True:
            try:
                cleanup_expired()
            except Exception:
                pass
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="tmp-cleanup")
    t.start()
    return t
