set -euo pipefail

echo "==> Create folders under ./api"
mkdir -p api/routers api/services api/utils

# -------- Router (api/routers/tender_ai.py) --------
cat > api/routers/tender_ai.py <<'PY'
from fastapi import APIRouter, UploadFile, File, Depends, Body, HTTPException
from typing import List, Optional
from api.services.tender_ai_service import TenderAIService

# مؤقت: بدّلها بتحقق الجلسة الحقيقي عندك
def require_user():
    return {"id": 1, "name": "system"}

router = APIRouter(prefix="/api", tags=["tender-ai"])

@router.post("/tenders/{tid}/files")
async def upload_tender_file(tid: int, f: UploadFile = File(...), user=Depends(require_user)):
    svc = TenderAIService(user)
    rec = await svc.save_file(tid, f)
    return {"file_id": rec["id"], "filename": rec["filename"], "size": rec["size"]}

@router.post("/tenders/{tid}/analyze")
async def analyze_tender(tid: int, file_ids: Optional[List[int]] = Body(default=None), lang: str = Body(default="bi"), user=Depends(require_user)):
    svc = TenderAIService(user)
    a = await svc.analyze(tid, file_ids=file_ids, lang=lang)
    return {"analysis_id": a["id"], "model": a["model"]}

@router.get("/tenders/{tid}/analysis")
async def get_latest_analysis(tid: int, user=Depends(require_user)):
    svc = TenderAIService(user)
    a = await svc.get_latest_analysis(tid)
    if not a:
        raise HTTPException(status_code=404, detail="no analysis")
    return a
PY

# -------- Service (api/services/tender_ai_service.py) --------
cat > api/services/tender_ai_service.py <<'PY'
import time, json, os
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
from api.utils import storage_basic, simple_ai

# ميموري DB مؤقتة (استبدلها لاحقًا بقاعدة البيانات)
_FAKE_DB = {"tender_files": [], "tender_ai_analysis": []}

class TenderAIService:
    def __init__(self, user:dict):
        self.user = user

    async def save_file(self, tid:int, f:UploadFile) -> Dict[str,Any]:
        key = f"tenders/{tid}/uploads/{int(time.time())}_{f.filename}"
        b = await f.read()
        storage_basic.put_bytes(key, b)
        rec = {
            "id": len(_FAKE_DB["tender_files"]) + 1,
            "tender_id": tid,
            "filename": f.filename,
            "mime": f.content_type,
            "size": len(b),
            "storage_key": key,
            "uploaded_by": self.user["id"],
            "uploaded_at": datetime.utcnow().isoformat()+"Z",
        }
        _FAKE_DB["tender_files"].append(rec)
        return rec

    async def analyze(self, tid:int, file_ids:Optional[List[int]], lang:str="bi") -> Dict[str,Any]:
        file_rec = None
        if file_ids:
            for r in _FAKE_DB["tender_files"]:
                if r["id"] in file_ids:
                    file_rec = r; break
        else:
            for r in reversed(_FAKE_DB["tender_files"]):
                if r["tender_id"] == tid:
                    file_rec = r; break
        content = storage_basic.get_bytes(file_rec["storage_key"])[:2_000_000] if file_rec else b""
        result = simple_ai.analyze_doc(content, lang=lang)
        rec = {
            "id": len(_FAKE_DB["tender_ai_analysis"]) + 1,
            "tender_id": tid,
            "file_id": file_rec["id"] if file_rec else None,
            "model": result["model"],
            "summary_ar": result["summary_ar"],
            "summary_en": result["summary_en"],
            "requirements_tech_json": json.dumps(result["requirements_tech"], ensure_ascii=False),
            "requirements_fin_json": json.dumps(result["requirements_fin"], ensure_ascii=False),
            "questions_json": json.dumps(result["questions"], ensure_ascii=False),
            "raw_json": json.dumps(result, ensure_ascii=False),
            "created_by": self.user["id"],
            "created_at": datetime.utcnow().isoformat()+"Z",
        }
        _FAKE_DB["tender_ai_analysis"].append(rec)
        return {"id": rec["id"], "model": rec["model"]}

    async def get_latest_analysis(self, tid:int) -> Optional[Dict[str,Any]]:
        for r in reversed(_FAKE_DB["tender_ai_analysis"]):
            if r["tender_id"] == tid:
                out = dict(r)
                import json as _json
                out["requirements_tech"] = _json.loads(r["requirements_tech_json"]) if r.get("requirements_tech_json") else []
                out["requirements_fin"]  = _json.loads(r["requirements_fin_json"])  if r.get("requirements_fin_json")  else []
                out["questions"]         = _json.loads(r["questions_json"])         if r.get("questions_json")         else []
                for k in ("requirements_tech_json","requirements_fin_json","questions_json"):
                    out.pop(k, None)
                return out
        return None
PY

# -------- Utils: storage_basic (api/utils/storage_basic.py) --------
cat > api/utils/storage_basic.py <<'PY'
import os
# داخل الحاوية عندك Volume على /data حسب docker-compose
_BASE = os.environ.get("STORAGE_BASE","/data")

def put_bytes(key:str, b:bytes):
    path = os.path.join(_BASE, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'wb') as fp: fp.write(b)

def get_bytes(key:str) -> bytes:
    path = os.path.join(_BASE, key)
    with open(path,'rb') as fp: return fp.read()
PY

# -------- Utils: simple_ai (api/utils/simple_ai.py) --------
cat > api/utils/simple_ai.py <<'PY'
from typing import List, Dict
MODEL = "simple-ai-v0"

def analyze_doc(content: bytes, lang: str = "bi") -> Dict:
    text = content.decode(errors='ignore')
    req_tech: List[Dict] = []
    if text:
        req_tech.append({"item":"Router CCR2004","qty":2,"specs":"...","notes":"..."})
        req_tech.append({"item":"Switch 24 PoE","qty":3,"specs":"...","notes":"..."})
    req_fin = [{ "item": r["item"], "unit":"pcs","qty":r["qty"],"est_price":0,"currency":"USD"} for r in req_tech]
    return {
        "model": MODEL,
        "summary_ar": "ملخص مبدئي للمناقصة: متطلبات فنية/مالية تقريبية — راجع وعدّل قبل التوليد.",
        "summary_en": "Preliminary tender summary: rough technical/financial requirements — review before final generation.",
        "requirements_tech": req_tech,
        "requirements_fin": req_fin,
        "questions": ["ما مدة التسليم؟","هل الزيارة إلزامية؟","ما العملة المعتمدة؟"]
    }
PY

# -------- Patch api/main.py to include router --------
MAIN="api/main.py"
if [ -f "$MAIN" ]; then
  grep -q "from api.routers import tender_ai" "$MAIN" || sed -i '1i from api.routers import tender_ai' "$MAIN"
  grep -q "include_router(tender_ai.router)" "$MAIN" || sed -i '0,/^app *= *.*/s//&\
app.include_router(tender_ai.router)/' "$MAIN"
  echo "✔ Patched $MAIN (import + include_router)"
else
  echo "❌ لم أجد api/main.py — راجع هيكلة مشروعك."
  exit 1
fi

echo "==> Build & restart API container"
if [ -z "${SESSION_SECRET:-}" ]; then
  export SESSION_SECRET=dev-session-secret-please-change
fi
if command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ]; then
  docker compose build api
  docker compose up -d api
  docker compose exec -T api bash -lc 'mkdir -p /data && chmod -R 775 /data'
fi

echo "==> Quick check on host port 8001"
curl -s http://localhost:8001/openapi.json | grep -o "/api/tenders/{tid}/files" || echo "⚠ route not visible on 8001 (check reverse proxy)"
