import time, json, os
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
from utils import storage_basic, simple_ai

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
