#!/bin/bash
# ============================================================
# LiveCoachHub — Smoke Test
# Jalankan SETELAH docker compose up --build berhasil
#
# Usage: bash scripts/smoke_test.sh
# ============================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        echo "  ✅ $desc"
        ((PASS++))
    else
        echo "  ❌ $desc"
        ((FAIL++))
    fi
}

echo ""
echo "🔍 LiveCoachHub Smoke Test"
echo "========================="
echo "Backend:  $BASE_URL"
echo "Frontend: $FRONTEND_URL"
echo ""

# ---- 1. Health check ----
echo "1️⃣  Health Check"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
check "Backend /health returns 200" "$([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1)"

if [ "$HTTP_CODE" = "200" ]; then
    HEALTH_BODY=$(curl -s "$BASE_URL/health")
    check "Health body contains 'status'" "$(echo "$HEALTH_BODY" | grep -q '"status"' && echo 0 || echo 1)"
    check "Health body contains 'services'" "$(echo "$HEALTH_BODY" | grep -q '"services"' && echo 0 || echo 1)"
    check "Health body contains 'provider'" "$(echo "$HEALTH_BODY" | grep -q '"provider"' && echo 0 || echo 1)"

    # Tampilkan status service
    echo ""
    echo "   Health response:"
    echo "$HEALTH_BODY" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_BODY"
    echo ""
fi

# ---- 2. Demo config ----
echo "2️⃣  Demo Config"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/demo-config" 2>/dev/null || echo "000")
check "GET /api/v1/demo-config returns 200" "$([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1)"

# ---- 3. Session start ----
echo "3️⃣  Session Start"
SESSION_RESP=$(curl -s -X POST "$BASE_URL/api/v1/session/start" \
    -H "Content-Type: application/json" \
    -d '{"product_id":"TSHIRT-01"}' 2>/dev/null || echo "{}")
SESSION_ID=$(echo "$SESSION_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
check "Session created" "$([ -n "$SESSION_ID" ] && echo 0 || echo 1)"
if [ -n "$SESSION_ID" ]; then
    echo "   Session ID: $SESSION_ID"
fi

# ---- 4. Pipeline end-to-end ----
echo "4️⃣  Pipeline E2E (single comment)"
if [ -n "$SESSION_ID" ]; then
    ANALYZE_RESP=$(curl -s -X POST "$BASE_URL/api/v1/comments/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\",\"comment_id\":\"CMT-SMOKE\",\"user_id\":\"USR-SMOKE\",\"timestamp_ms\":1000,\"text\":\"bb 55 ambil size apa kak\"}" 2>/dev/null || echo "{}")
    check "Pipeline returns nlp_prediction" "$(echo "$ANALYZE_RESP" | grep -q 'nlp_prediction' && echo 0 || echo 1)"
    check "Pipeline returns audience_snapshot" "$(echo "$ANALYZE_RESP" | grep -q 'audience_snapshot' && echo 0 || echo 1)"
    check "Pipeline returns action_decision" "$(echo "$ANALYZE_RESP" | grep -q 'action_decision' && echo 0 || echo 1)"
    check "Pipeline returns pipeline_status" "$(echo "$ANALYZE_RESP" | grep -q 'pipeline_status' && echo 0 || echo 1)"
else
    echo "  ⏭️  Skipped — no session ID"
fi

# ---- 5. Session reset ----
echo "5️⃣  Session Reset"
if [ -n "$SESSION_ID" ]; then
    RESET_RESP=$(curl -s -X POST "$BASE_URL/api/v1/session/reset" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\"}" 2>/dev/null || echo "{}")
    check "Session reset returns RESET" "$(echo "$RESET_RESP" | grep -q 'RESET' && echo 0 || echo 1)"
else
    echo "  ⏭️  Skipped — no session ID"
fi

# ---- 6. Frontend ----
echo "6️⃣  Frontend"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null || echo "000")
check "Frontend accessible at $FRONTEND_URL" "$([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1)"

# ---- Summary ----
echo ""
echo "========================="
echo "Results: ✅ $PASS passed, ❌ $FAIL failed"
if [ "$FAIL" = "0" ]; then
    echo "🎉 All smoke tests passed!"
else
    echo "⚠️  Some tests failed — review above."
fi
exit "$FAIL"
