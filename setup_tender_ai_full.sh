#!/bin/bash
set -euo pipefail

echo "==> Creating folders"
mkdir -p app/routers app/services app/utils alembic/versions

# -------------------- ROUTER --------------------
cat > app/routers/tender_ai.py <<'PY'
from fastapi import APIRouter, UploadFile, File, Depends, Body, HTTPException
from typing import List, Optional
from ..services.tender_ai_service import TenderAIService

# TODO: بدّل هذا بالتحقق الحقيقي عندك (session/auth)
def require_user():
    return {"id": 1, "name": "system"}

router = APIRouter(prefix="/api", tags=["tender-ai"])

@router.post("/tenders/{tid}/files")
async def upload_tender_file(tid: int, f: UploadFile = File(...), user=Depends(require_user)):
    svc = TenderAIService(user)
    rec = await svc.save_file(tid, f)
    return {"file_id": rec["id"], "filename": rec["filename"], "size": rec["size"]}

@router.post("/tenders/{tid}/analyze")
async def analyze_tender(
    tid: int,
    file_ids: Optional[List[int]] = Body(default=None),
    lang: str = Body(default="bi"),
    user=Depends(require_user)
):
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

# -------------------- SERVICE --------------------
cat > app/services/tender_ai_service.py <<'PY'
import time, json
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
from ..utils import storage_basic, simple_ai

# ميموري DB مؤقتة (بدّلها لاحقًا بـ ORM/DB)
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

# -------------------- UTILS: STORAGE --------------------
cat > app/utils/storage_basic.py <<'PY'
import os
_BASE = os.environ.get("STORAGE_BASE","/var/data/minio")

def put_bytes(key:str, b:bytes):
    path = os.path.join(_BASE, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fp:
        fp.write(b)

def get_bytes(key:str) -> bytes:
    path = os.path.join(_BASE, key)
    with open(path, 'rb') as fp:
        return fp.read()
PY

# -------------------- UTILS: SIMPLE AI STUB --------------------
cat > app/utils/simple_ai.py <<'PY'
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
        "summary_ar": "ملخص مبدئي للمناقصة: تم استخراج متطلبات فنية ومالية بشكل أولي — الرجاء المراجعة قبل التوليد النهائي.",
        "summary_en": "Preliminary tender summary: rough technical/financial requirements extracted — please review before final generation.",
        "requirements_tech": req_tech,
        "requirements_fin": req_fin,
        "questions": ["ما مدة التسليم؟","هل الزيارة إلزامية؟","ما العملة المعتمدة؟"]
    }
PY

# -------------------- ALEMBIC MIGRATION --------------------
STAMP="20250913_tender_ai_intake"
REV_FILE="alembic/versions/${STAMP}.py"

# حاول تحديد آخر down_revision تلقائيًا (محليًا أو داخل Docker service=api)
DOWN_REV="None"
if command -v alembic >/dev/null 2>&1; then
  H=$(alembic heads 2>/dev/null | tail -n 1 | awk '{print $1}'); [ -n "$H" ] && DOWN_REV="'$H'"
elif command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ]; then
  H=$(docker compose exec -T api alembic heads 2>/dev/null | tail -n 1 | awk '{print $1}') || true
  [ -n "$H" ] && DOWN_REV="'$H'"
fi

cat > "$REV_FILE" <<PY
from alembic import op
import sqlalchemy as sa

revision = "$STAMP"
down_revision = $DOWN_REV
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'tender_files',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tender_id', sa.Integer, sa.ForeignKey('tenders.id'), index=True),
        sa.Column('filename', sa.String(260)),
        sa.Column('mime', sa.String(100)),
        sa.Column('size', sa.Integer),
        sa.Column('storage_key', sa.String(400)),
        sa.Column('uploaded_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.text('now()')),
    )

    op.create_table(
        'tender_ai_analysis',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tender_id', sa.Integer, sa.ForeignKey('tenders.id'), index=True),
        sa.Column('file_id', sa.Integer, sa.ForeignKey('tender_files.id'), nullable=True),
        sa.Column('model', sa.String(100)),
        sa.Column('summary_ar', sa.Text),
        sa.Column('summary_en', sa.Text),
        sa.Column('requirements_tech_json', sa.Text),
        sa.Column('requirements_fin_json', sa.Text),
        sa.Column('questions_json', sa.Text),
        sa.Column('raw_json', sa.Text),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )

def downgrade():
    op.drop_table('tender_ai_analysis')
    op.drop_table('tender_files')
PY

# -------------------- PATCH main.py (best-effort) --------------------
MAIN="app/main.py"
if [ -f "$MAIN" ]; then
  if ! grep -q "from app.routers import tender_ai" "$MAIN"; then
    sed -i '1i from app.routers import tender_ai' "$MAIN"
  fi
  # حاول إدراج include_router بعد تعريف app =
  if grep -q "app = " "$MAIN" && ! grep -q "include_router(tender_ai.router)" "$MAIN"; then
    sed -i 's/^app = .*/&\napp.include_router(tender_ai.router)/' "$MAIN"
  fi
  echo "==> Patched app/main.py (import + include_router)"
else
  echo "⚠️  app/main.py not found. Add manually:\n   from app.routers import tender_ai\n   app.include_router(tender_ai.router)"
fi

echo
echo "==============================================="
echo "✅ Files created:"
echo "  - app/routers/tender_ai.py"
echo "  - app/services/tender_ai_service.py"
echo "  - app/utils/storage_basic.py"
echo "  - app/utils/simple_ai.py"
echo "  - alembic/versions/${STAMP}.py"
echo
echo "➡️  NEXT STEPS:"
echo "1) Apply migration:"
echo "   If Docker:"
echo "     docker compose exec api alembic upgrade head"
echo "   Else:"
echo "     alembic upgrade head"
echo
echo "2) Restart API service if using Docker:"
echo "     docker compose restart api"
echo
echo "3) Test endpoints (replace 12 with a real tender_id):"
echo "   Upload:"
echo "     curl -F \"f=@/path/to/tender.pdf\" http://YOUR_HOST/api/tenders/12/files"
echo "   Analyze:"
echo "     curl -X POST -H 'Content-Type: application/json' -d '{\"file_ids\":null,\"lang\":\"bi\"}' http://YOUR_HOST/api/tenders/12/analyze"
echo "   Get latest analysis:"
echo "     curl http://YOUR_HOST/api/tenders/12/analysis"
echo "==============================================="
