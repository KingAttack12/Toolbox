"""Outils PDF — 100 % local.

- pypdf (BSD-3) : fusion, séparation, rotation, métadonnées, réenregistrement.
- PyMuPDF (AGPLv3 — usage privé sur son propre serveur, pas de redistribution)
  : rendu PDF -> images uniquement.
- Pillow : images -> PDF.

Word <-> PDF et OCR : phase ultérieure (LibreOffice/Tesseract lourds).
"""
from __future__ import annotations

import io
import re
import zipfile
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/pdf", tags=["pdf"], dependencies=[Depends(get_current_user)])

MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_FILES = 20


def _read_upload(data: bytes, name: str = "fichier") -> bytes:
    if not data:
        raise HTTPException(status_code=400, detail=f"{name} vide.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"{name} trop lourd (max 50 Mo).")
    return data


def _open_reader(data: bytes):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(status_code=501, detail="pypdf non installé (pip install -r requirements.txt).")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise HTTPException(status_code=400, detail="PDF chiffré/protégé non supporté.")
        return reader
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="PDF illisible ou corrompu.")


def parse_ranges(spec: str, nb_pages: int) -> list[int]:
    """'1-3,5' (1-indexed) -> [0,1,2,4]. 'all'/vide -> toutes."""
    spec = (spec or "").strip().lower()
    if spec in ("", "all", "toutes", "tout"):
        return list(range(nb_pages))
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a < 1 or b < 1 or a > nb_pages or b > nb_pages or b < a:
                raise HTTPException(status_code=400, detail=f"Plage invalide : {part} (1-{nb_pages}).")
            pages.extend(range(a - 1, b))
        elif re.fullmatch(r"\d+", part):
            n = int(part)
            if n < 1 or n > nb_pages:
                raise HTTPException(status_code=400, detail=f"Page {n} hors limites (1-{nb_pages}).")
            pages.append(n - 1)
        else:
            raise HTTPException(status_code=400, detail=f"Plage invalide : {part} (ex : 1-3,5).")
    if not pages:
        raise HTTPException(status_code=400, detail="Aucune page sélectionnée.")
    if len(pages) > 500:
        raise HTTPException(status_code=400, detail="Trop de pages (max 500).")
    return pages


def _pdf_response(buf: bytes, filename: str) -> Response:
    safe = "".join(c for c in filename if c.isalnum() or c in "-_.")[:80] or "resultat.pdf"
    return Response(
        content=buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}"'},
    )


@router.post("/merge")
async def merge(files: list[UploadFile] = File(...)):
    if not 2 <= len(files) <= MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Envoyez 2 à {MAX_FILES} PDF.")
    from pypdf import PdfWriter

    writer = PdfWriter()
    total = 0
    for f in files:
        data = _read_upload(await f.read(), f.filename or "pdf")
        reader = _open_reader(data)
        for page in reader.pages:
            writer.add_page(page)
            total += 1
        if total > 500:
            raise HTTPException(status_code=400, detail="Trop de pages au total (max 500).")
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_response(buf.getvalue(), "fusion.pdf")


@router.post("/split")
async def split(
    file: UploadFile = File(...),
    pages: str = Form("all"),
):
    data = _read_upload(await file.read(), file.filename or "pdf")
    reader = _open_reader(data)
    from pypdf import PdfWriter

    wanted = parse_ranges(pages, len(reader.pages))
    writer = PdfWriter()
    for i in wanted:
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_response(buf.getvalue(), "extrait.pdf")


@router.post("/rotate")
async def rotate(
    file: UploadFile = File(...),
    pages: str = Form("all"),
    angle: int = Form(90),
):
    if angle not in (90, 180, 270):
        raise HTTPException(status_code=400, detail="Angle : 90, 180 ou 270.")
    data = _read_upload(await file.read(), file.filename or "pdf")
    reader = _open_reader(data)
    from pypdf import PdfWriter

    wanted = set(parse_ranges(pages, len(reader.pages)))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in wanted:
            page.rotate(angle)
        writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_response(buf.getvalue(), "rotation.pdf")


@router.post("/to-images")
async def to_images(
    file: UploadFile = File(...),
    dpi: int = Form(150),
    format: Literal["png", "jpg"] = Form("png"),
):
    if dpi not in (72, 100, 150, 200, 300):
        raise HTTPException(status_code=400, detail="DPI : 72, 100, 150, 200 ou 300.")
    data = _read_upload(await file.read(), file.filename or "pdf")
    try:
        import pymupdf
    except ImportError:
        raise HTTPException(status_code=501, detail="PyMuPDF non installé (pip install -r requirements.txt).")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="PDF illisible.")
    if len(doc) > 50:
        raise HTTPException(status_code=400, detail="Trop de pages (max 50).")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            if format == "png":
                z.writestr(f"page-{i + 1:03d}.png", pix.tobytes("png"))
            else:
                z.writestr(f"page-{i + 1:03d}.jpg", pix.tobytes("jpg", jpg_quality=85))
    return Response(
        content=zbuf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="pages.zip"'},
    )


@router.post("/from-images")
async def from_images(files: list[UploadFile] = File(...)):
    if not 1 <= len(files) <= MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Envoyez 1 à {MAX_FILES} images.")
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = 50_000_000
    imgs = []
    for f in files:
        data = _read_upload(await f.read(), f.filename or "image")
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            imgs.append(img.convert("RGB"))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Image illisible : {f.filename or '?'}")
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return _pdf_response(buf.getvalue(), "images.pdf")


@router.post("/metadata")
async def metadata(
    file: UploadFile = File(...),
    strip: bool = Form(False),
):
    data = _read_upload(await file.read(), file.filename or "pdf")
    reader = _open_reader(data)
    info = {str(k).lstrip("/"): str(v)[:500] for k, v in (reader.metadata or {}).items()}
    result = {"pages": len(reader.pages), "metadata": info}
    if not strip:
        return result
    from pypdf import PdfWriter

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({})  # vide les métadonnées document
    buf = io.BytesIO()
    writer.write(buf)
    resp = _pdf_response(buf.getvalue(), "sans-metadonnees.pdf")
    return resp


@router.post("/compress")
async def compress(file: UploadFile = File(...)):
    """Réenregistrement optimisé (déduplique les objets). Gain modeste :
    la vraie compression image (Ghostscript) viendra plus tard."""
    data = _read_upload(await file.read(), file.filename or "pdf")
    reader = _open_reader(data)
    from pypdf import PdfWriter

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for meth in ("compress_identical_objects", "remove_unreferenced_resources"):
        try:
            fn = getattr(writer, meth, None)
            if callable(fn):
                fn()
        except Exception:
            pass
    buf = io.BytesIO()
    writer.write(buf)
    out = buf.getvalue()
    if len(out) >= len(data):
        raise HTTPException(
            status_code=400,
            detail=f"Pas de gain possible ({len(data) // 1024} Ko déjà optimisé).",
        )
    return _pdf_response(out, "compresse.pdf")
