import base64
import hashlib
import hmac
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from session_guard import (
    issue_session,
    clear_session,
    rotate_all_sessions,
    require_session,
    bind_session_user,
    get_session_user,
    drop_session,
)
from storage import read_db


class LoginBody(BaseModel):
    username: str
    password: str


def _normalize_user(user: dict) -> dict:
    base = {
        "id": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role", "member"),
    }
    for extra in ("canSeeProjects", "canSeeTenders", "permissions"):
        if extra in user:
            base[extra] = user[extra]
    return base


def _verify_password(user: dict, password: str) -> bool:
    stored = user.get("passHash") or ""
    if stored.startswith("PLAINTEXT:"):
        return stored.split(":", 1)[1] == password
    salt_b64 = user.get("salt") or ""
    try:
        salt = base64.b64decode(salt_b64)
    except Exception:
        return False
    iterations = int(user.get("iterations") or 150000)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations).hex()
    return hmac.compare_digest(derived, stored)


def attach_auth_endpoints(app):
    @app.post("/api/auth/login")
    def login(body: LoginBody, request: Request):
        username = body.username.strip().lower()
        db = read_db()
        users = db.get("nwgd_users") or []
        user = next((u for u in users if str(u.get("username", "")).lower() == username), None)
        if not user or not _verify_password(user, body.password):
            raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")

        session_id = secrets.token_urlsafe(32)
        payload = _normalize_user(user)
        resp = JSONResponse({"ok": True, "user": payload})
        issue_session(resp, request, session_id)
        bind_session_user(session_id, payload)
        return resp

    @app.get("/api/auth/session-check")
    def session_check(request: Request):
        sid, meta = require_session(request)
        user = get_session_user(sid)
        if not user:
            drop_session(sid)
            raise HTTPException(status_code=401, detail="Session user missing")
        return {"ok": True, "session_id": sid, "user": user, **meta}

    @app.post("/api/auth/logout")
    def logout(request: Request):
        sid = None
        try:
            sid, _ = require_session(request)
        except HTTPException:
            pass
        resp = JSONResponse({"ok": True})
        if sid:
            drop_session(sid)
        clear_session(resp)
        return resp

    @app.post("/api/auth/logout_all")
    def logout_all():
        rotate_all_sessions()
        return {"ok": True}
