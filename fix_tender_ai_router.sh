set -euo pipefail
echo "==> البحث عن ملف FastAPI داخل هذا المجلد:"
APPFILE=$(grep -R --include="*.py" -n "FastAPI(" . | awk -F: '{print $1}' | head -n1 || true)
if [ -z "${APPFILE:-}" ]; then
  # محاولة ثانية: ابحث عن from fastapi import FastAPI
  APPFILE=$(grep -R --include="*.py" -n "from fastapi import FastAPI" . | awk -F: '{print $1}' | head -n1 || true)
fi
if [ -z "${APPFILE:-}" ]; then
  echo "❌ لم أجد ملف تطبيق FastAPI. افتح docker-compose.yml لمعرفة مسار ملف التشغيل."
  exit 1
fi
echo "✔ Found: $APPFILE"

# أضف import + include
if ! grep -q "from app.routers import tender_ai" "$APPFILE"; then
  sed -i '1i from app.routers import tender_ai' "$APPFILE"
  echo "✔ import أضيف في أعلى $APPFILE"
else
  echo "ℹ import موجود مسبقًا"
fi

if ! grep -q "include_router(tender_ai.router)" "$APPFILE"; then
  sed -i '0,/^app *= *.*/s//&\
app.include_router(tender_ai.router)/' "$APPFILE"
  echo "✔ include_router(tender_ai.router) أضيف"
else
  echo "ℹ include_router موجود مسبقًا"
fi
