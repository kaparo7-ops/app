from fastapi import Request, Response
from session_guard import issue_session, clear_session, rotate_all_sessions, require_session

def attach_auth_endpoints(app):
    @app.get("/api/auth/session-check")
    def session_check(request: Request):
        sid, meta = require_session(request)
        return {"ok": True, "session_id": sid, **meta}

    @app.post("/api/auth/logout")
    def logout(request: Request):
        resp = Response(content='{"ok":true}', media_type="application/json")
        clear_session(resp)
        return resp

    @app.post("/api/auth/logout_all")
    def logout_all():
        rotate_all_sessions()
        return {"ok": True}
