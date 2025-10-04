from routers import tender_ai
import os, json, threading, sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
from datetime import datetime

DATA_PATH = os.environ.get("DATA_PATH", "/data")
os.makedirs(DATA_PATH, exist_ok=True)
DB_FILE = os.path.join(DATA_PATH, "kv.json")
LOCK = threading.Lock()
SYNC_TOKEN = os.environ.get("SYNC_TOKEN")

def log(*a):
    print("[API]", *a, file=sys.stdout, flush=True)

def read_db() -> Dict[str, Any]:
    with LOCK:
        if not os.path.exists(DB_FILE):
            return {}
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log("read_db error:", e)
            return {}

def write_db(data: Dict[str, Any]):
    tmp = DB_FILE + ".tmp"
    with LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DB_FILE)

app = FastAPI(title="Nawafed Team API", version="1.1")
app.include_router(tender_ai.router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

def require_token(req: Request):
    tok = req.headers.get("x-sync-token") or req.query_params.get("token")
    if not SYNC_TOKEN or tok != SYNC_TOKEN:
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

class Body(BaseModel):
    value: Any

@app.put("/kv/{key}")
async def kv_put(key: str, request: Request, body: Body):
    require_token(request)
    db = read_db()
    db[key] = body.value
    write_db(db)
    return {"ok": True}

@app.patch("/kv/{key}")
async def kv_merge(key: str, request: Request, body: Body):
    require_token(request)
    db = read_db()
    cur = db.get(key, {})
    if isinstance(cur, dict) and isinstance(body.value, dict):
        cur.update(body.value)
        db[key] = cur
    else:
        db[key] = body.value
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
