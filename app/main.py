"""Toolbox privée — FastAPI. Phase 1+2 : auth + outils simples 100 % locaux."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, jobs
from .routers import auth_routes, tools_bio, tools_calc, tools_image, tools_media, tools_pdf, tools_qr, tools_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("toolbox")

app = FastAPI(title="Toolbox privée", version="0.1.0", docs_url="/docs", redoc_url=None)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
def _startup() -> None:
    jobs.ensure_data_dir()
    jobs.start_cleanup_thread()
    if not config.PASSWORD_HASH:
        log.warning("TOOLBOX_PASSWORD_HASH vide ! Lancez: python generate_password.py")
    log.info("Toolbox démarrée (data=%s, user=%s)", config.DATA_DIR, config.USERNAME)


@app.get("/api/health")
def health():
    return {"ok": True, "ai_enabled": bool(config.AI_API_KEY)}


app.include_router(auth_routes.router)
app.include_router(tools_text.router)
app.include_router(tools_calc.router)
app.include_router(tools_bio.router)
app.include_router(tools_qr.router)
app.include_router(tools_image.router)
app.include_router(tools_pdf.router)
app.include_router(tools_media.router)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
