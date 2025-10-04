from app.routers import tender_ai
import os, json, threading
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
SYNC_TOKEN = os.environ.get("SYNC_TOKEN")  # must be set in compose

def read_db() -> Dict[str, Any]:
    with LOCK:
        if not os.path.exists(DB_FILE):
            return {}
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}

def write_db(data: Dict[str, Any]):
    tmp = DB_FILE + ".tmp"
    with LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DB_FILE)

class KVItem(BaseModel):
    value: Any

app = FastAPI(title="Nawafed Team API", version="1.0")
app.include_router(tender_ai.router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

def require_token(req: Request):
    tok = req.headers.get("x-sync-token") or req.query_params.get("token")
    if not SYNC_TOKEN or tok != SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()+"Z"}

@app.get("/kv/{key}")
def kv_get(key: str):
    db = read_db()
    return {"key": key, "value": db.get(key, None)}

@app.put("/kv/{key}")
async def kv_put(key: str, request: Request):
    require_token(request)
    body = await request.json()
    if not isinstance(body, dict) or "value" not in body:
        raise HTTPException(400, "Body must be JSON with 'value'")
    db = read_db()
    db[key] = body["value"]
    write_db(db)
    return {"ok": True}

@app.patch("/kv/{key}")
async def kv_merge(key: str, request: Request):
    require_token(request)
    body = await request.json()
    if not isinstance(body, dict) or "value" not in body:
        raise HTTPException(400, "Body must be JSON with 'value'")
    db = read_db()
    cur = db.get(key, {})
    if isinstance(cur, dict) and isinstance(body["value"], dict):
        cur.update(body["value"])
        db[key] = cur
    else:
        db[key] = body["value"]
    write_db(db)
    return {"ok": True}
