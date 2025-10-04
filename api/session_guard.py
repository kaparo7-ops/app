import os, time, hmac, hashlib, base64
from typing import Optional, Tuple
from fastapi import Request, Response, HTTPException

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
SESSION_IDLE = int(os.getenv("SESSION_IDLE_SECONDS", "1800"))
COOKIE_NAME   = os.getenv("SESSION_COOKIE_NAME", "nwgd_session")
SAMESITE      = os.getenv("SESSION_SAMESITE", "Lax")

if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET is empty")

_SESS = {}  # session_id -> (ua_hash, ip_prefix, last_seen)

def _sign(val: bytes) -> str:
    import hashlib, hmac, base64
    sig = hmac.new(SESSION_SECRET.encode(), val, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")

def _pack(session_id: str) -> str:
    raw = session_id.encode()
    sig = _sign(raw)
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + sig
    return token

def _unpack(token: str) -> Optional[str]:
    try:
        raw_b64, sig = token.split(".", 1)
        raw = base64.urlsafe_b64decode(raw_b64 + "==")
        import hmac
        if hmac.compare_digest(sig, _sign(raw)):
            return raw.decode()
    except Exception:
        return None
    return None

def _ua_hash(req: Request) -> str:
    ua = req.headers.get("user-agent","").strip()
    return hashlib.sha1(ua.encode()).hexdigest()

def _ip_prefix(req: Request) -> str:
    ip = req.client.host if req.client else "0.0.0.0"
    parts = ip.split(".")
    return ".".join(parts[:3]) if len(parts)==4 else ip

def issue_session(resp: Response, req: Request, session_id: str) -> None:
    _SESS[session_id] = (_ua_hash(req), _ip_prefix(req), int(time.time()))
    resp.set_cookie(
        COOKIE_NAME, _pack(session_id),
        httponly=True, secure=True, samesite=SAMESITE, path="/"
    )

def clear_session(resp: Response) -> None:
    resp.delete_cookie(COOKIE_NAME, path="/")

def rotate_all_sessions() -> None:
    _SESS.clear()

def require_session(req: Request) -> Tuple[str, dict]:
    c = req.cookies.get(COOKIE_NAME)
    if not c:
        raise HTTPException(status_code=401, detail="No session")
    sid = _unpack(c)
    if not sid:
        raise HTTPException(status_code=401, detail="Bad session")

    rec = _SESS.get(sid)
    if not rec:
        raise HTTPException(status_code=401, detail="Session expired")

    ua_h, ip_p, last = rec
    now = int(time.time())
    if now - last > SESSION_IDLE:
        _SESS.pop(sid, None)
        raise HTTPException(status_code=401, detail="Idle timeout")

    if ua_h != _ua_hash(req):
        raise HTTPException(status_code=401, detail="Browser changed")
    if ip_p != _ip_prefix(req):
        raise HTTPException(status_code=401, detail="Network changed")

    _SESS[sid] = (ua_h, ip_p, now)
    return sid, {"ua": ua_h, "ip": ip_p, "last": last}
