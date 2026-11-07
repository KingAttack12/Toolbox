from fastapi import APIRouter, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from .. import config, accounts, email_accounts, mail
from ..auth import check_credentials, create_session, destroy_session, get_current_user, get_admin, hash_password, revoke_user, authenticate_session
from ..ratelimit import clear, client_ip, is_limited, limited_response, record_failure
from fastapi import Depends

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
def login(payload: dict, request: Request, response: Response):
    ip = client_ip(request)
    if is_limited(ip):
        return limited_response()
    username = str(payload.get("username", ""))[:254].strip()
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
    username = email_accounts.resolve(username)
    token = authenticate_session(username, password)
    if not token:
        record_failure(ip)  # 401 loggé par Nginx -> exploité par fail2ban
        return JSONResponse(status_code=401, content={"ok": False, "error": "Identifiants invalides."})
    clear(ip)
    destroy_session(request.cookies.get(config.SESSION_COOKIE))
    if username != config.USERNAME:
        import time
        with accounts.database() as db: db.execute("UPDATE accounts SET last_login=? WHERE username=?", (time.time(), username))
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
    with accounts.database() as db:
        row = db.execute("SELECT email,verified FROM accounts WHERE username=?", (user,)).fetchone()
    return {"user": user, "email": row["email"] if row else None, "verified": bool(row and row["verified"]), "is_admin": user == config.USERNAME, "ai_enabled": bool(config.AI_API_KEY)}


# Custom same-origin header is required for the new state-changing beta APIs.
# CORS is deliberately not enabled; foreign origins cannot send this header.
def beta_write(request: Request):
    if request.headers.get("x-toolbox-request") != "1" or request.headers.get("sec-fetch-site") == "cross-site":
        from fastapi import HTTPException
        raise HTTPException(403, "Requête non autorisée.")


@router.get("/registration")
def registration_status():
    return {"enabled": accounts.enabled() and mail.ready(), "mail_ready": mail.ready(), "beta": False}


from pydantic import BaseModel, Field
from typing import Literal
import re


class Signup(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=15, max_length=128)


@router.post("/register", dependencies=[Depends(beta_write)])
def register(payload: Signup, request: Request, background: BackgroundTasks):
    ip = "signup:" + client_ip(request)
    if is_limited(ip): return limited_response()
    record_failure(ip)
    email = email_accounts.normalize(payload.email)
    email_accounts.register(email, hash_password(payload.password))
    background.add_task(email_accounts.send_requested_link, email, "verify")
    return {"ok": True, "message": "Si cette adresse est disponible, vous recevrez un lien de confirmation. Votre compte devra ensuite être approuvé par le propriétaire."}


class Toggle(BaseModel):
    enabled: bool
    password: str = Field(max_length=128)


class Decision(BaseModel):
    password: str = Field(max_length=128)
    username: str = Field(max_length=32)
    action: Literal["approve", "reject", "suspend", "reactivate", "revoke", "delete"]


@router.get("/admin/accounts")
def account_list(user: str = Depends(get_admin)):
    return accounts.dashboard()


@router.post("/admin/registration", dependencies=[Depends(beta_write)])
def registration_toggle(payload: Toggle, request: Request, user: str = Depends(get_admin)):
    require_owner_password(payload.password, request)
    if payload.enabled and not mail.ready(): raise HTTPException(503, "Configurez l’envoi Gmail avant d’ouvrir les inscriptions.")
    accounts.set_enabled(payload.enabled)
    return {"ok": True}


@router.post("/admin/accounts", dependencies=[Depends(beta_write)])
def account_decision(payload: Decision, request: Request, user: str = Depends(get_admin)):
    require_owner_password(payload.password, request)
    if payload.action == "revoke": revoke_user(payload.username)
    else: accounts.decide(payload.username, payload.action)
    return {"ok": True}


class MailRequest(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    purpose: Literal["verify","reset"]


@router.post("/account/email-link", dependencies=[Depends(beta_write)])
def request_link(payload: MailRequest, request: Request, background: BackgroundTasks):
    ip="mail:"+client_ip(request)
    if is_limited(ip):return limited_response()
    record_failure(ip)
    if not mail.ready():raise HTTPException(503,"L’envoi d’e-mails n’est pas encore configuré.")
    background.add_task(email_accounts.send_requested_link,email_accounts.normalize(payload.email),payload.purpose)
    return {"ok":True,"message":"Si un compte éligible existe, un e-mail vous sera envoyé. Vérifiez aussi vos courriers indésirables."}


class TokenRequest(BaseModel):
    token: str = Field(min_length=32,max_length=128)
    purpose: Literal["verify","reset"]
    password: str | None = Field(default=None,min_length=8,max_length=128)


@router.post("/account/confirm", dependencies=[Depends(beta_write)])
def confirm_account(payload: TokenRequest, request: Request):
    ip="token:"+client_ip(request)
    if is_limited(ip):return limited_response()
    record_failure(ip)
    if payload.purpose=='reset' and (not payload.password or len(payload.password)<15):raise HTTPException(400,"Choisissez un nouveau mot de passe.")
    email_accounts.consume(payload.token,payload.purpose,hash_password(payload.password) if payload.purpose=="reset" and payload.password else None,payload.password)
    return {"ok":True,"message":"Adresse confirmée. Votre demande attend maintenant la validation du propriétaire." if payload.purpose=='verify' else "Mot de passe modifié. Reconnectez-vous."}


class LegacyEmail(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


@router.post("/account/link-email", dependencies=[Depends(beta_write)])
def link_email(payload: LegacyEmail, request: Request, background: BackgroundTasks, user: str = Depends(get_current_user)):
    if user == config.USERNAME:raise HTTPException(400,"Le compte propriétaire reste sans adresse e-mail.")
    ip="link:"+client_ip(request)
    if is_limited(ip):return limited_response()
    record_failure(ip)
    if not mail.ready():raise HTTPException(503,"L’envoi d’e-mails n’est pas encore configuré.")
    if not check_credentials(user,payload.password):raise HTTPException(403,"Mot de passe incorrect.")
    email=email_accounts.normalize(payload.email);email_accounts.link_legacy(user,email)
    background.add_task(email_accounts.send_requested_link,email,'verify')
    return {"ok":True,"message":"Confirmez votre adresse avec le lien envoyé par e-mail."}



def require_owner_password(password, request):
    ip='admin-confirm:'+client_ip(request)
    if is_limited(ip):raise HTTPException(429,'Trop de tentatives. Réessayez dans une minute.')
    if not check_credentials(config.USERNAME,password):
        record_failure(ip);raise HTTPException(403,'Confirmez votre mot de passe administrateur.')
    clear(ip)
