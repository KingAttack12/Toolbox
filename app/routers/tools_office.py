"""Conversions Word/PDF et OCR, traitées localement sur le serveur."""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pymupdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from ..workload import HeavyRoute
from ..auth import get_current_user
from .tools_pdf import MAX_PDF_BYTES, _open_reader, _read_upload

router = APIRouter(prefix="/api/tools/office", tags=["word-pdf-ocr"], dependencies=[Depends(get_current_user)], route_class=HeavyRoute)

MAX_PDF_PAGES = 100
MAX_OCR_PAGES = 20
MAX_DOCX_UNPACKED_BYTES = 100 * 1024 * 1024
MAX_DOCX_MEMBERS = 2_000
def _validate_docx(data: bytes) -> None:
    if not data:
        raise HTTPException(status_code=400, detail="Fichier Word vide.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="Fichier Word trop lourd (max 50 Mo).")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            names = {item.filename for item in members}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise HTTPException(status_code=400, detail="Fichier Word invalide. Seuls les documents .docx sont acceptés.")
            if len(members) > MAX_DOCX_MEMBERS or sum(item.file_size for item in members) > MAX_DOCX_UNPACKED_BYTES:
                raise HTTPException(status_code=413, detail="Contenu Word trop volumineux après décompression.")
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                raise HTTPException(status_code=400, detail="Les documents Word contenant des macros ne sont pas acceptés.")
            for item in members:
                if not item.filename.endswith(".rels"):
                    continue
                try:
                    relationships = ET.fromstring(archive.read(item))
                except ET.ParseError:
                    raise HTTPException(status_code=400, detail="Fichier Word invalide ou corrompu.")
                for relation in relationships:
                    if relation.attrib.get("TargetMode", "").lower() == "external" and not relation.attrib.get("Type", "").endswith("/hyperlink"):
                        raise HTTPException(status_code=400, detail="Les ressources externes liées au document Word ne sont pas acceptées.")
    except HTTPException:
        raise
    except (zipfile.BadZipFile, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Fichier Word illisible ou corrompu.")


def _validate_pdf(data: bytes) -> int:
    reader = _open_reader(_read_upload(data, "PDF"))
    pages = len(reader.pages)
    if not pages:
        raise HTTPException(status_code=400, detail="Le PDF ne contient aucune page.")
    if pages > MAX_PDF_PAGES:
        raise HTTPException(status_code=400, detail=f"PDF trop long (max {MAX_PDF_PAGES} pages).")
    return pages


def _file_response(data: bytes, mime: str, filename: str) -> Response:
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _convert_docx_to_pdf(data: bytes) -> bytes:
    office = shutil.which("libreoffice") or shutil.which("soffice")
    if not office:
        raise HTTPException(status_code=501, detail="Conversion Word → PDF indisponible : LibreOffice n'est pas installé sur ce serveur.")

    with tempfile.TemporaryDirectory(prefix="toolbox-docx-pdf-") as temp:
        root = Path(temp)
        src = root / "document.docx"
        outdir = root / "out"
        profile = root / "profile"
        outdir.mkdir()
        src.write_bytes(data)
        command = [
            office,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(outdir),
            str(src),
        ]
        try:
            proc = subprocess.run(command, capture_output=True, timeout=60, check=False)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="La conversion Word a dépassé le délai autorisé (60 s).")
        except OSError:
            raise HTTPException(status_code=503, detail="LibreOffice n'a pas pu démarrer.")
        pdf_path = outdir / "document.pdf"
        if proc.returncode != 0 or not pdf_path.is_file():
            raise HTTPException(status_code=422, detail="Impossible de convertir ce document Word. Vérifiez qu'il s'ouvre correctement.")
        result = pdf_path.read_bytes()
        if not result or len(result) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="Le PDF produit dépasse la limite de 50 Mo.")
        return result


def _convert_pdf_to_docx(data: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="toolbox-pdf-docx-") as temp:
        root = Path(temp)
        src, dst = root / "document.pdf", root / "document.docx"
        src.write_bytes(data)
        command = [sys.executable, "-m", "pdf2docx.main", "convert", str(src), str(dst), "--multi_processing=False", "--raw_exceptions=True"]
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"
        try:
            proc = subprocess.run(command, capture_output=True, timeout=90, check=False, env=env)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="La conversion PDF a dépassé le délai autorisé (90 s).")
        except OSError:
            raise HTTPException(status_code=503, detail="Le convertisseur PDF → Word n'a pas pu démarrer.")
        if proc.returncode != 0 or not dst.is_file():
            raise HTTPException(status_code=422, detail="Impossible de convertir ce PDF. Les mises en page complexes ou les documents scannés peuvent donner un résultat incomplet.")
        result = dst.read_bytes()
        if not result or len(result) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="Le document Word produit dépasse la limite de 50 Mo.")
        return result


def _ocr_pdf(data: bytes, language: str, dpi: int) -> bytes:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise HTTPException(status_code=501, detail="OCR indisponible : Tesseract n'est pas installé sur ce serveur.")
    try:
        langs_result = subprocess.run([tesseract, "--list-langs"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=503, detail="Le moteur OCR n'a pas pu démarrer.")
    available = set((langs_result.stdout or "").splitlines()[1:])
    requested = language.split("+")
    missing = [lang for lang in requested if lang not in available]
    if missing:
        raise HTTPException(status_code=501, detail="Langue OCR absente du serveur : " + ", ".join(missing) + ".")

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="PDF illisible ou corrompu.")

    scale = dpi / 72
    text_parts: list[str] = []
    env = os.environ.copy()
    env["OMP_THREAD_LIMIT"] = "1"
    try:
        for index, page in enumerate(doc):
            rect = page.rect
            if rect.width <= 0 or rect.height <= 0 or rect.width * scale * rect.height * scale > 20_000_000:
                raise HTTPException(status_code=400, detail=f"La page {index + 1} est trop grande pour l'OCR à {dpi} DPI.")
            try:
                pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            except Exception:
                raise HTTPException(status_code=422, detail=f"Impossible de rendre la page {index + 1} pour l'OCR.")
            command = [tesseract, "stdin", "stdout", "-l", language, "--psm", "3", "--dpi", str(dpi)]
            try:
                proc = subprocess.run(command, input=pix.tobytes("png"), capture_output=True, timeout=15, check=False, env=env)
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=504, detail=f"L'OCR de la page {index + 1} est trop long.")
            except OSError:
                raise HTTPException(status_code=503, detail="Le moteur OCR n'a pas pu démarrer.")
            if proc.returncode != 0:
                raise HTTPException(status_code=422, detail=f"Échec de l'OCR à la page {index + 1}.")
            content = proc.stdout.decode("utf-8", errors="replace").strip()
            text_parts.append(f"--- Page {index + 1} ---\n{content}" if content else f"--- Page {index + 1} ---\n[Aucun texte détecté]")
    finally:
        doc.close()
    return ("\n\n".join(text_parts) + "\n").encode("utf-8")


@router.post("/word-to-pdf")
def word_to_pdf(file: UploadFile = File(...)):
    data = file.file.read(MAX_PDF_BYTES + 1)
    _validate_docx(data)
    result = _convert_docx_to_pdf(data)
    return _file_response(result, "application/pdf", "document.pdf")


@router.post("/pdf-to-word")
def pdf_to_word(file: UploadFile = File(...)):
    data = file.file.read(MAX_PDF_BYTES + 1)
    _validate_pdf(data)
    result = _convert_pdf_to_docx(data)
    return _file_response(result, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document.docx")


@router.post("/ocr")
def ocr_pdf(
    file: UploadFile = File(...),
    language: str = Form("fra"),
    dpi: int = Form(150),
):
    if language not in {"fra", "eng", "fra+eng"}:
        raise HTTPException(status_code=400, detail="Langue OCR : français, anglais ou français + anglais.")
    if dpi not in {100, 150, 200}:
        raise HTTPException(status_code=400, detail="Résolution OCR : 100, 150 ou 200 DPI.")
    data = file.file.read(MAX_PDF_BYTES + 1)
    pages = _validate_pdf(data)
    if pages > MAX_OCR_PAGES:
        raise HTTPException(status_code=400, detail=f"OCR limité à {MAX_OCR_PAGES} pages par fichier.")
    result = _ocr_pdf(data, language, dpi)
    return _file_response(result, "text/plain; charset=utf-8", "texte-ocr.txt")
