from fastapi import APIRouter, UploadFile, File, Depends, Body, HTTPException, Request
from typing import List, Optional
from services.tender_ai_service import TenderAIService  # انتبه: بدون api.
from session_guard import require_session, get_session_user


def require_active_user(req: Request):
    sid, _ = require_session(req)
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="Session user missing")
    return user

router = APIRouter(prefix="/api", tags=["tender-ai"])

@router.post("/tenders/{tid}/files")
async def upload_tender_file(tid: int, f: UploadFile = File(...), user=Depends(require_active_user)):
    svc = TenderAIService(user)
    rec = await svc.save_file(tid, f)
    return {"file_id": rec["id"], "filename": rec["filename"], "size": rec["size"]}

@router.post("/tenders/{tid}/analyze")
async def analyze_tender(
    tid: int,
    file_ids: Optional[List[int]] = Body(default=None),
    lang: str = Body(default="bi"),
    user=Depends(require_active_user),
):
    svc = TenderAIService(user)
    a = await svc.analyze(tid, file_ids=file_ids, lang=lang)
    return {"analysis_id": a["id"], "model": a["model"]}

@router.get("/tenders/{tid}/analysis")
async def get_latest_analysis(tid: int, user=Depends(require_active_user)):
    svc = TenderAIService(user)
    a = await svc.get_latest_analysis(tid)
    if not a:
        raise HTTPException(status_code=404, detail="no analysis")
    return a
