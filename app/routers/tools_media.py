"""Téléchargement de contenus autorisés (yt-dlp) — tâche de fond.

Règles : domaines autorisés uniquement, pas de DRM/protection contournée,
case à cocher "droits confirmés" obligatoire, durée max 30 min,
fichier max 500 Mo, 2 téléchargements simultanés max, fichiers purgés
automatiquement (TTL via jobs.py). Nécessite ffmpeg sur le serveur
(pour la fusion mp4) — sinon les formats directs seuls sont proposés.
"""
from __future__ import annotations

import re
import threading
import urllib.parse
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import jobs
from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/media", tags=["media"], dependencies=[Depends(get_current_user)])

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "www.youtube-nocookie.com",
}
MAX_DURATION_S = 30 * 60
MAX_FILESIZE = 500 * 1024 * 1024
MAX_CONCURRENT = 2
FORMAT_ID_RE = re.compile(r"^[\w+-]{1,40}$")

_progress: dict[str, int] = {}
_active = 0
_lock = threading.Lock()


def _ytdlp():
    try:
        import yt_dlp
    except ImportError:
        raise HTTPException(status_code=501, detail="yt-dlp non installé (pip install -r requirements.txt).")
    return yt_dlp


def validate_url(url: str) -> str:
    url = (url or "").strip()[:500]
    try:
        parts = urllib.parse.urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="URL invalide.")
    if parts.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL http(s) uniquement.")
    if (parts.hostname or "").lower() not in ALLOWED_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Domaine non autorisé. Autorisés : {sorted(ALLOWED_HOSTS)}",
        )
    return url


def _extract(url: str) -> dict:
    yt_dlp = _ytdlp()
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "socket_timeout": 15, "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"URL inexploitable : {str(e)[:200]}")
    if not info or info.get("_type") == "playlist":
        raise HTTPException(status_code=400, detail="Playlists non supportées (une vidéo à la fois).")
    if info.get("is_live"):
        raise HTTPException(status_code=400, detail="Lives non supportés.")
    dur = info.get("duration") or 0
    if dur > MAX_DURATION_S:
        raise HTTPException(status_code=400, detail=f"Vidéo trop longue ({dur // 60} min, max 30 min).")
    return info


def _pick_formats(info: dict) -> list[dict]:
    out = []
    for f in info.get("formats") or []:
        fid = str(f.get("format_id") or "")
        if not fid or not FORMAT_ID_RE.match(fid):
            continue
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        if vcodec == "none" and acodec == "none":
            continue  # storyboard & co
        size = f.get("filesize") or f.get("filesize_approx") or 0
        if size and size > MAX_FILESIZE:
            continue
        out.append({
            "id": fid,
            "ext": f.get("ext") or "?",
            "resolution": f.get("resolution") or f.get("format_note") or "?",
            "vcodec": vcodec, "acodec": acodec,
            "size_mo": round(size / 1048576, 1) if size else None,
        })
        if len(out) >= 25:
            break
    return out


class UrlIn(BaseModel):
    url: str = Field(max_length=500)


@router.post("/formats")
def formats(payload: UrlIn):
    url = validate_url(payload.url)
    info = _extract(url)
    return {
        "title": (info.get("title") or "?")[:150],
        "duration_s": info.get("duration") or 0,
        "formats": _pick_formats(info),
    }


class FetchIn(BaseModel):
    url: str = Field(max_length=500)
    format_id: str = Field(max_length=40)
    confirm_rights: bool = False


@router.post("/fetch")
def fetch(payload: FetchIn):
    global _active
    url = validate_url(payload.url)
    if not payload.confirm_rights:
        raise HTTPException(status_code=400, detail="Confirmez détenir les droits / l'autorisation de télécharger.")
    if not FORMAT_ID_RE.match(payload.format_id or ""):
        raise HTTPException(status_code=400, detail="Format invalide.")
    info = _extract(url)  # revérifie existence du format (anti-injection)
    if payload.format_id not in {f["id"] for f in _pick_formats(info)}:
        raise HTTPException(status_code=400, detail="Format inconnu pour cette vidéo. Relistez les formats.")
    with _lock:
        if _active >= MAX_CONCURRENT:
            raise HTTPException(status_code=429, detail="2 téléchargements en cours, réessayez dans une minute.")
        _active += 1
    job = jobs.create_job("youtube")
    jobs.update_job(job.id, status="processing")
    t = threading.Thread(
        target=_download, args=(job.id, url, payload.format_id), daemon=True
    )
    t.start()
    return {"job_id": job.id}


def _download(job_id: str, url: str, format_id: str) -> None:
    global _active
    yt_dlp = _ytdlp()
    d = jobs.task_dir(job_id)

    def hook(progress: dict) -> None:
        if progress.get("status") == "downloading":
            total = progress.get("total_bytes") or progress.get("total_bytes_estimate") or 0
            done = progress.get("downloaded_bytes") or 0
            if total:
                _progress[job_id] = min(99, int(done * 100 / total))

    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "format": format_id, "merge_output_format": "mp4",
        "restrictfilenames": True, "nooverwrites": True,
        "max_filesize": MAX_FILESIZE, "socket_timeout": 20,
        "outtmpl": str(d / "%(title).80s [%(id)s].%(ext)s"),
        "progress_hooks": [hook],
    }
    try:
        _progress[job_id] = 0
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = sorted(d.glob("*"), key=lambda p: p.stat().st_size, reverse=True)
        files = [p for p in files if p.is_file()]
        if not files:
            raise RuntimeError("Aucun fichier produit.")
        jobs.update_job(job_id, status="completed", result_file=files[0].name)
        _progress[job_id] = 100
    except Exception as e:
        jobs.update_job(job_id, status="failed", error=str(e)[:300])
    finally:
        with _lock:
            _active -= 1


@router.get("/job/{job_id}")
def job_status(job_id: str):
    safe = "".join(c for c in job_id if c.isalnum())[:64]
    job = jobs.get_job(safe)
    if not job or job.type != "youtube":
        raise HTTPException(status_code=404, detail="Tâche inconnue.")
    return {
        "status": job.status,
        "progress": _progress.get(safe, 0),
        "error": job.error,
        "filename": job.result_file,
    }


@router.get("/result/{job_id}")
def job_result(job_id: str):
    safe = "".join(c for c in job_id if c.isalnum())[:64]
    job = jobs.get_job(safe)
    if not job or job.type != "youtube" or job.status != "completed" or not job.result_file:
        raise HTTPException(status_code=404, detail="Résultat indisponible.")
    path: Path = jobs.task_dir(safe) / Path(job.result_file).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier expiré ou supprimé.")
    return FileResponse(path, filename=path.name)
