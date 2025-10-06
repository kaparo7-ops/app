from starlette.middleware.sessions import SessionMiddleware
from routers.auth import router as auth_router
from routers import tender_ai
import base64
import binascii
import json
import os, sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from storage import read_db, write_db  # absolute import ensures uvicorn resolves helpers correctly

SYNC_TOKEN = os.environ.get("SYNC_TOKEN")

def log(*a):
    print("[API]", *a, file=sys.stdout, flush=True)

app = FastAPI(title="Nawafed Team API", version="1.1")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET","change-me"))
app.include_router(auth_router, prefix="/auth")
app.include_router(tender_ai.router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

def _basic_matches(auth_header: str) -> bool:
    """Return True when the Basic-Auth credentials include the sync token."""

    try:
        scheme, _, value = auth_header.partition(" ")
        if scheme.lower() != "basic" or not value:
            return False
        decoded = base64.b64decode(value).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False

    username, _, password = decoded.partition(":")
    return SYNC_TOKEN in (username, password)


def require_token(req: Request):
    tok = req.headers.get("x-sync-token") or req.query_params.get("token")
    if SYNC_TOKEN and tok == SYNC_TOKEN:
        return

    auth = req.headers.get("authorization", "")
    if SYNC_TOKEN and auth and _basic_matches(auth):
        return

    raise HTTPException(status_code=401, detail="Unauthorized")

@app.middleware("http")
async def logger(request: Request, call_next):
    started = datetime.utcnow().isoformat()+"Z"
    try:
        resp = await call_next(request)
        log(request.method, request.url.path, resp.status_code, started)
        return resp
    except Exception as e:
        log("ERR", request.method, request.url.path, e)
        raise

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()+"Z"}

@app.get("/kv/{key}")
def kv_get(key: str):
    db = read_db()
    return {"key": key, "value": db.get(key, None)}

async def _extract_value(request: Request):
    """Return the JSON value sent in the request body.

    Legacy clients wrap the data as {"value": ...} while the browser code sends
    the JSON payload directly. We accept both formats so the UI can persist
    settings without breaking existing integrations.
    """

    body = await request.body()
    if not body.strip():
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if isinstance(payload, dict) and set(payload.keys()) == {"value"}:
        return payload["value"]
    return payload


@app.put("/kv/{key}")
async def kv_put(key: str, request: Request):
    require_token(request)
    value = await _extract_value(request)
    db = read_db()
    db[key] = value
    write_db(db)
    return {"ok": True}


@app.patch("/kv/{key}")
async def kv_merge(key: str, request: Request):
    require_token(request)
    value = await _extract_value(request)
    db = read_db()
    cur = db.get(key, {})
    if isinstance(cur, dict) and isinstance(value, dict):
        cur.update(value)
        db[key] = cur
    else:
        db[key] = value
    write_db(db)
    return {"ok": True}

# --- auto-attach session endpoints (added by setup) ---
try:
    from auth_extra import attach_auth_endpoints
    attach_auth_endpoints(app)
except Exception as _e:
    # لا توقف التطبيق إذا فشل الربط
    pass
# --- end auto-attach ---
