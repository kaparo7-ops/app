set -euo pipefail

: "${SESSION_SECRET:=dev-session-secret-please-change}"
export SESSION_SECRET
sed -i 's/from api\.services /from services /' api/routers/tender_ai.py || true
sed -i 's/from api\.utils /from utils /' api/services/tender_ai_service.py || true
docker compose build api
docker compose up -d api
echo '--- LOGS ---'
docker compose logs api --tail=80
echo '--- IMPORT TEST IN CONTAINER ---'
docker compose exec -T api python - <<'PY'
import pkgutil
mods={m.name for m in pkgutil.iter_modules()}
print("HAS:", {"routers","services","utils"} & mods)
import routers.tender_ai as t
print("ROUTER:", hasattr(t,"router"))
PY
echo '--- OPENAPI IN CONTAINER ---'
docker compose exec -T api sh -lc 'apk add --no-cache curl 2>/dev/null || true; curl -s http://localhost:8000/openapi.json | grep -o "/api/tenders/{tid}/files" || echo NO_ROUTE_IN_CONTAINER'
