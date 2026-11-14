"""Conversion vidéo locale (ffmpeg) — 100 % local, aucun service externe.

Outil : MP4 (ou autre conteneur) -> MP3 (128/192/320 kbps).
Upload effectif ~50 Mo (plafond Nginx). Timeout 5 min, fichiers
temporaires purgés par TTL (jobs.py).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from .. import jobs
from ..workload import HeavyRoute
from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/media", tags=["media"], dependencies=[Depends(get_current_user)], route_class=HeavyRoute)

MAX_FILESIZE = 50 * 1024 * 1024


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
def mp4_to_mp3(
    file: UploadFile = File(...),
    bitrate: Literal["128", "192", "320"] = Form("192"),
):
    """Extrait la piste audio d'une vidéo -> MP3. Commande construite en
    liste d'arguments (jamais de shell), timeout 5 min."""
    import subprocess

    data = file.file.read(MAX_FILESIZE + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(data) > MAX_FILESIZE:
        raise HTTPException(status_code=413, detail="Fichier trop lourd (max 50 Mo).")
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
             "-threads", "1", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", str(dst)],
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


def _media_demuxer(data):
    # Force a known binary demuxer: never let ffmpeg interpret uploaded playlists.
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE": return "wav"
    if data[:4] == b"RIFF" and data[8:12] == b"AVI ": return "avi"
    if data[:4] == b"fLaC": return "flac"
    if data[:4] == b"OggS": return "ogg"
    if data[:4] == b"\x1aE\xdf\xa3": return "matroska"
    if data[4:8] == b"ftyp": return "mov"
    if data[:3] == b"ID3": return "mp3"
    if len(data) >= 2 and data[0] == 255:
        if data[1] & 0xf6 == 0xf0: return "aac"
        if data[1] & 0xe0 == 0xe0: return "mp3"
    raise HTTPException(400, "Fichier audio ou vidéo non reconnu. Les listes de lecture ne sont pas acceptées.")


@router.post("/convert")
def convert_media(
    file: UploadFile = File(...),
    format: Literal["mp3", "wav", "flac", "ogg", "m4a", "mp4", "webm"] = Form(...),
):
    import json
    import math
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    data = file.file.read(MAX_FILESIZE + 1)
    if not data: raise HTTPException(400, "Fichier vide.")
    if len(data) > MAX_FILESIZE: raise HTTPException(413, "Fichier trop lourd (max 50 Mo).")
    demuxer = _media_demuxer(data)
    ffmpeg, probe = _ffmpeg_bin(), shutil.which("ffprobe")
    if not probe: raise HTTPException(501, "Analyse du média indisponible sur ce serveur.")
    codecs = {
        "mp3": (["-c:a", "libmp3lame", "-b:a", "192k"], "audio/mpeg"),
        "wav": (["-c:a", "pcm_s16le"], "audio/wav"),
        "flac": (["-c:a", "flac"], "audio/flac"),
        "ogg": (["-c:a", "libvorbis", "-q:a", "4"], "audio/ogg"),
        "m4a": (["-c:a", "aac", "-b:a", "160k"], "audio/mp4"),
        "mp4": (["-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"], "video/mp4"),
        "webm": (["-c:v", "libvpx-vp9", "-deadline", "realtime", "-cpu-used", "6", "-crf", "35", "-b:v", "0", "-c:a", "libopus", "-b:a", "96k"], "video/webm"),
    }
    with tempfile.TemporaryDirectory(prefix="toolbox-media-") as directory:
        source, target = Path(directory) / "input.bin", Path(directory) / ("conversion." + format)
        source.write_bytes(data)
        del data
        safe_input = ["-protocol_whitelist", "file,pipe", "-f", demuxer, "-i", str(source)]
        try:
            result = subprocess.run([probe, "-v", "error", *safe_input, "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json"], capture_output=True, timeout=15, check=True)
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
            if not math.isfinite(duration) or not 0 < duration <= 600:
                raise HTTPException(400, "Média limité à 10 minutes, avec une durée lisible.")
            video = format in {"mp4", "webm"}
            streams = info.get("streams", [])
            if not any(stream.get("codec_type") == ("video" if video else "audio") for stream in streams):
                raise HTTPException(400, "Ce fichier ne contient pas de piste " + ("vidéo." if video else "audio."))
            if any(stream.get("width", 0) * stream.get("height", 0) > 3840 * 2160 for stream in streams):
                raise HTTPException(400, "Vidéo source limitée à la définition 4K.")
            mapping = ["-map", "0:v:0", "-map", "0:a:0?", "-vf", "scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2", "-r", "30"] if video else ["-map", "0:a:0", "-vn", "-ar", "44100", "-ac", "2"]
            encoder, mime = codecs[format]
            subprocess.run([ffmpeg, "-nostdin", "-y", "-v", "error", "-threads", "1", "-filter_threads", "1", *safe_input, *mapping, "-map_metadata", "-1", "-sn", "-dn", *encoder, "-threads", "1", "-fs", str(MAX_FILESIZE), str(target)], capture_output=True, timeout=300, check=True)
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "Conversion trop longue. Essayez un fichier plus court.")
        except (subprocess.CalledProcessError, ValueError, OSError):
            raise HTTPException(422, "Ce média est illisible ou ne peut pas être converti dans ce format.")
        if not target.is_file() or not target.stat().st_size:
            raise HTTPException(422, "Aucun fichier produit.")
        if target.stat().st_size >= MAX_FILESIZE - 65536:
            raise HTTPException(413, "La sortie dépasse 50 Mo. Essayez un format plus compact ou un fichier plus court.")
        return Response(target.read_bytes(), media_type=mime, headers={"Content-Disposition": f'attachment; filename="conversion.{format}"'})
