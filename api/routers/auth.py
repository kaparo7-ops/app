from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

router = APIRouter()

class LoginIn(BaseModel):
    email: EmailStr
    password: str | None = None  # موجود للواجهة فقط، لا نتحقق منه الآن

SESSION_KEY = "user"

@router.post("/login")
async def login(body: LoginIn, request: Request):
    # مصادقة بسيطة: أي إيميل مقبول، ضع جلسة
    request.session[SESSION_KEY] = {"email": body.email}
    return {"ok": True, "user": request.session[SESSION_KEY]}

@router.get("/session-check")
async def session_check(request: Request):
    user = request.session.get(SESSION_KEY)
    if not user:
        raise HTTPException(status_code=401, detail="No session")
    return {"ok": True, "user": user}

@router.post("/logout")
async def logout(request: Request):
    request.session.pop(SESSION_KEY, None)
    return {"ok": True}
