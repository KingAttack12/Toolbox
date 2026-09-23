"""Générateur de QR code — local via qrcode + Pillow (gratuits/open source)."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/qr", tags=["qr"], dependencies=[Depends(get_current_user)])


class QrIn(BaseModel):
    text: str = Field(max_length=2000)
    size: int = Field(default=10, ge=4, le=20)  # box_size
    border: int = Field(default=4, ge=2, le=10)


@router.post("/generate")
def generate(payload: QrIn):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Texte vide.")
    try:
        import qrcode
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Librairie 'qrcode' non installée. Lancez : pip install -r requirements.txt",
        )
    qr = qrcode.QRCode(box_size=payload.size, border=payload.border)
    qr.add_data(payload.text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
