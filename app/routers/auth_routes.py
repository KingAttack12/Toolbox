from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from .. import config, accounts
from ..auth import check_credentials, create_session, destroy_session, get_current_user, get_admin, hash_password
from ..ratelimit import clear, client_ip, is_limited, limited_response, record_failure
from fastapi import Depends

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
def login(payload: dict, request: Request, response: Response):
    ip = client_ip(request)
    if is_limited(ip):
        return limited_response()
    username = str(payload.get("username", ""))[:128].strip()
    password = str(payload.get("password", ""))
    if len(password) > 256:
        return JSONResponse(status_code=400, content={"error": "Mot de passe trop long."})
    if not username or not password:
        return Response(status_code=400)
    if not config.PASSWORD_HASH:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Serveur non initialisé : TOOLBOX_PASSWORD_HASH vide."},
        )
    if not check_credentials(username, password):
        record_failure(ip)  # 401 loggé par Nginx -> exploité par fail2ban
        return JSONResponse(status_code=401, content={"ok": False, "error": "Identifiants invalides."})
    clear(ip)
    destroy_session(request.cookies.get(config.SESSION_COOKIE))
    token = create_session(username)
    response.set_cookie(
        key=config.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=config.SESSION_TTL_SECONDS,
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, user: str = Depends(get_current_user)):
    destroy_session(request.cookies.get(config.SESSION_COOKIE))
    response.delete_cookie(key=config.SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user, "is_admin": user == config.USERNAME, "ai_enabled": bool(config.AI_API_KEY)}


# Custom same-origin header is required for the new state-changing beta APIs.
# CORS is deliberately not enabled; foreign origins cannot send this header.
def beta_write(request: Request):
    if request.headers.get("x-toolbox-request") != "1" or request.headers.get("sec-fetch-site") == "cross-site":
        from fastapi import HTTPException
        raise HTTPException(403, "Requête non autorisée.")


@router.get("/registration")
def registration_status():
    return {"enabled": accounts.enabled(), "beta": True}


from pydantic import BaseModel, Field
from typing import Literal
import re


class Signup(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=15, max_length=128)


@router.post("/register", dependencies=[Depends(beta_write)])
def register(payload: Signup, request: Request):
    from fastapi import HTTPException
    ip = "signup:" + client_ip(request)
    if is_limited(ip):
        return limited_response()
    record_failure(ip)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,31}", payload.username):
        raise HTTPException(400, "Identifiant : 3 à 32 lettres, chiffres, points, tirets ou underscores.")
    if not accounts.enabled():
        raise HTTPException(403, "Les demandes de compte sont fermées.")
    accounts.request_account(payload.username, hash_password(payload.password))
    return {"ok": True, "message": "Demande reçue. Si cet identifiant est disponible, le propriétaire pourra la valider. Essayez ensuite de vous connecter. Les demandes expirent après 7 jours."}


class Toggle(BaseModel):
    enabled: bool


class Decision(BaseModel):
    username: str = Field(max_length=32)
    action: Literal["approve", "reject", "suspend"]


@router.get("/admin/accounts")
def account_list(user: str = Depends(get_admin)):
    return accounts.dashboard()


@router.post("/admin/registration", dependencies=[Depends(beta_write)])
def registration_toggle(payload: Toggle, user: str = Depends(get_admin)):
    accounts.set_enabled(payload.enabled)
    return {"ok": True}


@router.post("/admin/accounts", dependencies=[Depends(beta_write)])
def account_decision(payload: Decision, user: str = Depends(get_admin)):
    accounts.decide(payload.username, payload.action)
    return {"ok": True}
