import os
from fastapi import HTTPException, Query

SYNC_TOKEN = os.getenv("SYNC_TOKEN", "")

def require_sync_token(token: str = Query(..., description="SYNC token")):
    if not SYNC_TOKEN or token != SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
