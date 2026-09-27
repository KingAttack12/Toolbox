"""Téléchargement de contenus autorisés (yt-dlp) — tâche de fond.

Règles : domaines autorisés uniquement, pas de DRM/protection contournée,
case à cocher "droits confirmés" obligatoire, durée max 30 min,
fichier max 500 Mo, 2 téléchargements simultanés max, fichiers purgés
automatiquement (TTL via jobs.py). Nécessite ffmpeg sur le serveur
(pour la fusion mp4) — sinon les formats directs seuls sont proposés.

Anti-bot (mécanismes officiels yt-dlp uniquement) : clients tv/web_safari
en anonyme, cookies du compte (JETABLE conseillé) + web_safari sinon.
Jamais de contournement DRM, proxy, ferme à tokens ou autre bidouille.
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
MAX_COOKIES_BYTES = 100 * 1024
FORMAT_ID_RE = re.compile(r"^[\w+-]{1,40}$")

# Clients essayés dans l'ordre (doc officielle yt-dlp) :
# - sans cookies : tv (le moins scruté) puis web_safari puis web ;
# - avec cookies : JAMAIS tv (invalide la session) -> web_safari puis web.
ANON_CLIENTS = ["tv", "web_safari", "web"]
AUTH_CLIENTS = ["web_safari", "web"]

_progress: dict[str, dict] = {}
_active = 0
_lock = threading.Lock()


def _cookie_path():
    from .. import config

    return config.DATA_DIR / "yt-cookies.txt"


def _cookies_configured() -> bool:
    p = _cookie_path()
    return p.is_file() and p.stat().st_size > 0


def _base_opts() -> dict:
    """Options communes : clients + cookies éventuels (compte jetable conseillé)."""
    opts: dict = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "socket_timeout": 20,
    }
    if _cookies_configured():
        opts["cookiefile"] = str(_cookie_path())
        opts["extractor_args"] = {"youtube": {"player_client": AUTH_CLIENTS}}
    else:
        opts["extractor_args"] = {"youtube": {"player_client": ANON_CLIENTS}}
    return opts


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
    opts = _base_opts()
    opts["socket_timeout"] = 15
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        msg = str(e)[:200]
        if "not a bot" in msg.lower():
            msg += (" — YouTube bloque les IP de serveurs. Méthode fiable : outil "
                    "Cookies YouTube avec un compte JETABLE, puis réessayez. Doc : "
                    "https://github.com/yt-dlp/yt-dlp/wiki/FAQ")
        raise HTTPException(status_code=400, detail=f"URL inexploitable : {msg}")
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

    def _fmt_speed(v) -> str:
        try:
            v = float(v or 0)
        except (TypeError, ValueError):
            return ""
        if v <= 0:
            return ""
        for unit in ("o/s", "Ko/s", "Mo/s"):
            if v < 1024 or unit == "Mo/s":
                return f"{v:.1f} {unit}"
            v /= 1024
        return ""

    def hook(progress: dict) -> None:
        if progress.get("status") == "downloading":
            total = progress.get("total_bytes") or progress.get("total_bytes_estimate") or 0
            done = progress.get("downloaded_bytes") or 0
            pct = min(99, int(done * 100 / total)) if total else 0
            _progress[job_id] = {
                "p": pct,
                "speed": _fmt_speed(progress.get("speed")),
                "eta": str(progress.get("eta") or ""),
            }

    opts = _base_opts()
    opts.update({
        "format": format_id, "merge_output_format": "mp4",
        "restrictfilenames": True, "nooverwrites": True,
        "max_filesize": MAX_FILESIZE, "socket_timeout": 20,
        "concurrent_fragments": 4,
        "outtmpl": str(d / "%(title).80s [%(id)s].%(ext)s"),
        "progress_hooks": [hook],
    })
    try:
        _progress[job_id] = {"p": 0, "speed": "", "eta": ""}
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = sorted(d.glob("*"), key=lambda p: p.stat().st_size, reverse=True)
        files = [p for p in files if p.is_file()]
        if not files:
            raise RuntimeError("Aucun fichier produit.")
        jobs.update_job(job_id, status="completed", result_file=files[0].name)
        _progress[job_id] = {"p": 100, "speed": "", "eta": ""}
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
    prog = _progress.get(safe, {"p": 0, "speed": "", "eta": ""})
    if isinstance(prog, int):  # compat ancien format
        prog = {"p": prog, "speed": "", "eta": ""}
    return {
        "status": job.status,
        "progress": prog.get("p", 0),
        "speed": prog.get("speed", ""),
        "eta": prog.get("eta", ""),
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


class CookiesIn(BaseModel):
    action: Literal["status", "save", "delete"] = "status"
    data: str = Field(default="", max_length=120_000)


def _valid_netscape(txt: str) -> bool:
    """Format Netscape cookies.txt : commentaires # ou lignes à 7 champs
    contenant un domaine youtube/google."""
    if len(txt.encode()) > MAX_COOKIES_BYTES:
        return False
    seen_domain = False
    seen_cookie = False
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            return False
        if "youtube.com" in parts[0] or "google.com" in parts[0]:
            seen_domain = True
        seen_cookie = True
    return seen_domain and seen_cookie


@router.post("/cookies")
def cookies(payload: CookiesIn):
    """Gère le fichier cookies YouTube (compte JETABLE conseillé).
    Stocké chmod 600, jamais affiché ni loggé. Sans cookies, les clients
    anonymes (tv/web_safari) sont tentés ; avec cookies, web_safari/web
    (jamais tv : invaliderait la session)."""
    from .. import config

    jobs.ensure_data_dir()
    path = _cookie_path()
    if payload.action == "status":
        return {"configured": _cookies_configured()}
    if payload.action == "delete":
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return {"configured": False}
    # save
    txt = payload.data.strip()[:120_000]
    if not _valid_netscape(txt):
        raise HTTPException(
            status_code=400,
            detail="Fichier invalide : export Netscape cookies.txt attendu "
                   "(lignes à 7 champs avec domaine youtube.com ou google.com).",
        )
    tmp = path.with_suffix(".tmp")
    tmp.write_text(txt, encoding="utf-8")
    try:
        tmp.chmod(0o600)
        tmp.replace(path)
    except Exception:
        raise HTTPException(status_code=500, detail="Écriture impossible.")
    return {"configured": True}
