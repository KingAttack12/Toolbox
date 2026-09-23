from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from .. import config
from ..auth import check_credentials, create_session, destroy_session, get_current_user
from ..ratelimit import clear, client_ip, is_limited, limited_response, record_failure
from fastapi import Depends

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
def login(payload: dict, request: Request, response: Response):
    ip = client_ip(request)
    if is_limited(ip):
        return limited_response()
    username = str(payload.get("username", ""))[:128]
    password = str(payload.get("password", ""))[:256]
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
    token = create_session(username)
    response.set_cookie(
        key=config.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # passer à True derrière HTTPS (Nginx) en prod
        max_age=config.SESSION_TTL_SECONDS,
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response, user: str = Depends(get_current_user)):
    from fastapi import Request  # noqa
    response.delete_cookie(key=config.SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user, "ai_enabled": bool(config.AI_API_KEY)}
