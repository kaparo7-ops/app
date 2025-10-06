from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, root_validator

router = APIRouter()

class LoginIn(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None  # موجود للواجهة فقط، لا نتحقق منه الآن

    @root_validator
    def _ensure_identifier(cls, values):
        email = values.get("email")
        username = values.get("username")
        if not (email or username):
            raise ValueError("email or username required")
        if username:
            values["username"] = username.strip()
        return values

SESSION_KEY = "user"

@router.post("/login")
async def login(body: LoginIn, request: Request):
    # مصادقة بسيطة: أي إيميل مقبول، ضع جلسة
    payload = {}
    if body.email:
        payload["email"] = body.email
    if body.username:
        payload["username"] = body.username
    request.session[SESSION_KEY] = payload
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
