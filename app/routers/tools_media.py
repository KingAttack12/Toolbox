"""Conversion vidéo locale (ffmpeg) — 100 % local, aucun service externe.

Outil : MP4 (ou autre conteneur) -> MP3 (128/192/320 kbps).
Upload effectif ~50 Mo (plafond Nginx). Timeout 5 min, fichiers
temporaires purgés par TTL (jobs.py).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import jobs
from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/media", tags=["media"], dependencies=[Depends(get_current_user)])

MAX_FILESIZE = 500 * 1024 * 1024


def _ffmpeg_bin() -> str:
    """ffmpeg système, sinon binaire statique imageio-ffmpeg (secours dev)."""
    import shutil

    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise HTTPException(status_code=501, detail="ffmpeg introuvable sur le serveur.")


@router.post("/mp4-to-mp3")
async def mp4_to_mp3(
    file: UploadFile = File(...),
    bitrate: Literal["128", "192", "320"] = Form("192"),
):
    """Extrait la piste audio d'une vidéo -> MP3. Commande construite en
    liste d'arguments (jamais de shell), timeout 5 min."""
    import subprocess

    data = await file.read(MAX_FILESIZE + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(data) > MAX_FILESIZE:
        raise HTTPException(status_code=413, detail="Fichier trop lourd (max 500 Mo).")
    ffmpeg = _ffmpeg_bin()
    job = jobs.create_job("mp3")
    d = jobs.task_dir(job.id)
    src = d / "input.bin"
    src.write_bytes(data)
    base = (file.filename or "audio").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    base = "".join(c for c in base.rsplit(".", 1)[0] if c.isalnum() or c in "-_")[:50] or "audio"
    dst = d / f"{base}.mp3"
    try:
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-i", str(src), "-vn",
             "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", str(dst)],
            timeout=300, check=True, capture_output=True,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Conversion trop longue (abandon après 5 min).")
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=400, detail="Fichier vidéo illisible ou format non supporté.")
    finally:
        try:
            src.unlink(missing_ok=True)
        except OSError:
            pass
    if not dst.is_file() or dst.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Échec de conversion.")
    jobs.update_job(job.id, status="completed", result_file=dst.name)
    return FileResponse(dst, media_type="audio/mpeg", filename=dst.name)
