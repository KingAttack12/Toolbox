"""Bêta MP3 pour une vidéo YouTube publique et explicitement autorisée."""
from __future__ import annotations

import re
import os
import signal
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import Response

from ..workload import HeavyRoute
from ..auth import get_current_user
from .tools_media import _ffmpeg_bin

router = APIRouter(prefix="/api/tools/youtube", tags=["youtube-mp3-beta"], dependencies=[Depends(get_current_user)], route_class=HeavyRoute)

MAX_DURATION_SECONDS = 20 * 60
MAX_SOURCE_BYTES = 120 * 1024 * 1024
MAX_OUTPUT_BYTES = 60 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 240
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _validate_youtube_url(value: str) -> str:
    value = (value or "").strip()
    if not value or len(value) > 2048:
        raise HTTPException(status_code=400, detail="Saisissez un lien YouTube valide.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise HTTPException(status_code=400, detail="Lien YouTube invalide.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS or parsed.username or parsed.password or port not in (None, 443):
        raise HTTPException(status_code=400, detail="Seuls les liens HTTPS directs vers youtube.com ou youtu.be sont acceptés.")

    parts = [part for part in parsed.path.split("/") if part]
    video_id = ""
    if host == "youtu.be" and len(parts) == 1:
        video_id = parts[0]
    elif parsed.path.rstrip("/") == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
        video_id = parts[1]
    if not VIDEO_ID.fullmatch(video_id):
        raise HTTPException(status_code=400, detail="Le lien doit pointer vers une seule vidéo, pas une chaîne ou une playlist.")
    return value


def _download_mp3(url: str, bitrate: str) -> bytes:
    if not shutil.which("deno"):
        raise HTTPException(status_code=501, detail="Le moteur Deno requis par la bêta n'est pas installé.")
    try:
        import yt_dlp
    except ImportError:
        raise HTTPException(status_code=501, detail="yt-dlp n'est pas installé sur le serveur.")

    ffmpeg = _ffmpeg_bin()
    script = r'''import sys
from yt_dlp import YoutubeDL

url, outdir, ffmpeg, bitrate = sys.argv[1:]

def reject_video(info, *, incomplete):
    if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming"}:
        return "Les directs ne sont pas pris en charge."
    duration = info.get("duration")
    if not isinstance(duration, (int, float)):
        return "La durée de cette vidéo ne peut pas être vérifiée."
    if duration > 1200:
        return "La durée maximale pour cette bêta est de 20 minutes."

options = {
    "format": "bestaudio/best",
    "outtmpl": outdir + "/audio.%(ext)s",
    "noplaylist": True,
    "max_filesize": 120 * 1024 * 1024,
    "socket_timeout": 20,
    "retries": 1,
    "fragment_retries": 1,
    "file_access_retries": 1,
    "concurrent_fragment_downloads": 1,
    "cachedir": False,
    "quiet": True,
    "no_warnings": True,
    "noprogress": True,
    "match_filter": reject_video,
    "ffmpeg_location": ffmpeg,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": bitrate,
    }],
}
with YoutubeDL(options) as ydl:
    ydl.download([url])
'''

    with tempfile.TemporaryDirectory(prefix="toolbox-yt-mp3-") as temp:
        root = Path(temp)
        script_path = root / "download.py"
        script_path.write_text(script, encoding="utf-8")
        try:
            proc = subprocess.Popen(
                [sys.executable, str(script_path), url, str(root), ffmpeg, bitrate],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=(os.name == "posix"),
            )
            try:
                _, _ = proc.communicate(timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.communicate()
                raise HTTPException(status_code=504, detail="Téléchargement interrompu après 4 minutes.")
        except HTTPException:
            raise
        except OSError:
            raise HTTPException(status_code=503, detail="Le téléchargeur n'a pas pu démarrer.")
        if proc.returncode != 0:
            raise HTTPException(
                status_code=422,
                detail="Extraction impossible. Vérifiez que la vidéo est disponible, autorisée et respecte la limite de 20 minutes.",
            )

        result_path = root / "audio.mp3"
        if not result_path.is_file():
            raise HTTPException(
                status_code=422,
                detail="Extraction impossible. Vérifiez que la vidéo est disponible, autorisée et respecte la limite de 20 minutes.",
            )
        size = result_path.stat().st_size
        if not size or size > MAX_OUTPUT_BYTES:
            raise HTTPException(status_code=413, detail="Le MP3 dépasse la limite de taille de cette bêta.")
        return result_path.read_bytes()


@router.post("/mp3")
def youtube_to_mp3(
    url: str = Form(...),
    bitrate: str = Form("128"),
    authorized: bool = Form(False),
):
    url = _validate_youtube_url(url)
    if bitrate not in {"128", "192"}:
        raise HTTPException(status_code=400, detail="Qualité MP3 : 128 ou 192 kb/s.")
    if not authorized:
        raise HTTPException(status_code=400, detail="Confirmez que le téléchargement de cette vidéo est explicitement autorisé.")
    result = _download_mp3(url, bitrate)
    return Response(
        content=result,
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'attachment; filename="audio-youtube.mp3"'},
    )
