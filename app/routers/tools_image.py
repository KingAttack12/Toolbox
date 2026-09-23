"""Conversion d'images — 100 % local via Pillow (gratuit/open source).

Couvre : JPG/PNG/WebP, compression (qualité), redimensionnement,
rotation, miroir, noir & blanc, suppression EXIF.
"""
from __future__ import annotations

import io
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/image", tags=["images"], dependencies=[Depends(get_current_user)])

MAX_IMAGE_BYTES = 20 * 1024 * 1024
OUTPUTS = {
    "jpg": ("JPEG", "image/jpeg", "jpg"),
    "png": ("PNG", "image/png", "png"),
    "webp": ("WEBP", "image/webp", "webp"),
}


def _load_image(data: bytes):
    try:
        from PIL import Image
    except ImportError:
        raise HTTPException(status_code=501, detail="Pillow non installé (pip install -r requirements.txt).")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image trop lourde (max 20 Mo).")
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    try:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = 50_000_000  # anti decompression-bomb
        img = Image.open(io.BytesIO(data))
        img.load()  # validation réelle du contenu (pas l'extension)
    except Exception:
        raise HTTPException(status_code=400, detail="Fichier image illisible ou format non supporté.")
    return img


@router.post("/convert")
async def convert(
    file: UploadFile = File(...),
    format: Literal["jpg", "png", "webp"] = Form("jpg"),
    quality: int = Form(85),
    resize_max: int = Form(0),
    rotate: int = Form(0),
    flip: Literal["none", "horizontal", "vertical"] = Form("none"),
    grayscale: bool = Form(False),
    strip_exif: bool = Form(True),
):
    data = await file.read(MAX_IMAGE_BYTES + 1)
    img = _load_image(data)
    from PIL import Image

    if not (10 <= quality <= 100):
        raise HTTPException(status_code=400, detail="Qualité entre 10 et 100.")
    if resize_max and not (100 <= resize_max <= 8000):
        raise HTTPException(status_code=400, detail="resize_max entre 100 et 8000 (0 = inchangé).")
    if rotate not in (0, 90, 180, 270):
        raise HTTPException(status_code=400, detail="Rotation : 0, 90, 180 ou 270.")

    # Transformations (ordre : orientation -> miroir -> N&B -> taille)
    if rotate:
        img = img.transpose({90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}[rotate])
    if flip == "horizontal":
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif flip == "vertical":
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if grayscale:
        img = img.convert("L")
    if resize_max and max(img.size) > resize_max:
        img.thumbnail((resize_max, resize_max), Image.LANCZOS)

    pil_format, media_type, ext = OUTPUTS[format]
    # JPEG sans canal alpha : fond blanc (pas d'EXIF recopié -> strip par défaut)
    if pil_format == "JPEG" and img.mode in ("RGBA", "LA", "PA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif pil_format == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    save_kwargs: dict = {}
    if pil_format in ("JPEG", "WEBP"):
        save_kwargs = {"quality": quality}
        if pil_format == "WEBP":
            save_kwargs["method"] = 4
    if pil_format == "PNG":
        save_kwargs = {"optimize": True}
    if not strip_exif:
        # conserve l'EXIF d'origine si présent et si le format le supporte
        try:
            exif = img.getexif()
            if exif and pil_format in ("JPEG", "WEBP"):
                save_kwargs["exif"] = exif
        except Exception:
            pass
    img.save(buf, format=pil_format, **save_kwargs)
    out = buf.getvalue()

    base = (file.filename or "image").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    base = "".join(c for c in base.rsplit(".", 1)[0] if c.isalnum() or c in "-_")[:50] or "image"
    return Response(
        content=out,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{base}.{ext}"'},
    )
