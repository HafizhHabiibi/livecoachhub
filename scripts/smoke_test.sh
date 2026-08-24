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
REQUIRE_FULL_AI="${REQUIRE_FULL_AI:-1}"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
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
    check "NLP model reports READY" "$(echo "$HEALTH_BODY" | grep -q '"nlp_model":"READY"' && echo 0 || echo 1)"

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
echo "4️⃣  Pipeline E2E (trend + Coach Card provenance)"
if [ -n "$SESSION_ID" ]; then
    ANALYZE_RESP_1=$(curl -s -X POST "$BASE_URL/api/v1/comments/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\",\"comment_id\":\"CMT-SMOKE-1\",\"user_id\":\"USR-SMOKE-1\",\"timestamp_ms\":1000,\"text\":\"bb 55 ambil size apa kak\"}" 2>/dev/null || echo "{}")
    ANALYZE_RESP_2=$(curl -s -X POST "$BASE_URL/api/v1/comments/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\",\"comment_id\":\"CMT-SMOKE-2\",\"user_id\":\"USR-SMOKE-2\",\"timestamp_ms\":2000,\"text\":\"ukuran untuk bb 60 pilih apa\"}" 2>/dev/null || echo "{}")
    check "Pipeline returns nlp_prediction" "$(echo "$ANALYZE_RESP_2" | grep -q 'nlp_prediction' && echo 0 || echo 1)"
    check "Pipeline returns audience_snapshot" "$(echo "$ANALYZE_RESP_2" | grep -q 'audience_snapshot' && echo 0 || echo 1)"
    check "Pipeline selects an action from two unique users" "$(echo "$ANALYZE_RESP_2" | grep -q 'SHOW_SIZE_GUIDE' && echo 0 || echo 1)"

    # Retry comment pertama harus mengembalikan hasil cache (processed_count tetap 1).
    RETRY_RESP=$(curl -s -X POST "$BASE_URL/api/v1/comments/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\",\"comment_id\":\"CMT-SMOKE-1\",\"user_id\":\"USR-SMOKE-1\",\"timestamp_ms\":1000,\"text\":\"bb 55 ambil size apa kak\"}" 2>/dev/null || echo "{}")
    check "Retry is idempotent" "$(echo "$RETRY_RESP" | grep -q '"processed_count":1' && echo 0 || echo 1)"

    CARD_RESP="{}"
    for _ in $(seq 1 15); do
        CARD_RESP=$(curl -s "$BASE_URL/api/v1/session/card?session_id=$SESSION_ID" 2>/dev/null || echo "{}")
        if echo "$CARD_RESP" | grep -q 'generation_provider'; then
            break
        fi
        sleep 1
    done
    check "Coach Card produced" "$(echo "$CARD_RESP" | grep -q 'generation_provider' && echo 0 || echo 1)"
    if [ "$REQUIRE_FULL_AI" = "1" ]; then
        check "Coach Card provider is Gemini" "$(echo "$CARD_RESP" | grep -q '"generation_provider":"GEMINI"' && echo 0 || echo 1)"
        check "Coach Card is not fallback" "$(echo "$CARD_RESP" | grep -q '"fallback_used":false' && echo 0 || echo 1)"
        POST_GENERATION_HEALTH=$(curl -s "$BASE_URL/health" 2>/dev/null || echo "{}")
        check "Health reports Gemini READY after real generation" "$(echo "$POST_GENERATION_HEALTH" | grep -q '"llm_model":"READY"' && echo 0 || echo 1)"
    else
        check "Fallback provenance is explicit" "$(echo "$CARD_RESP" | grep -Eq '"generation_provider":"(GEMINI|TEMPLATE)"' && echo 0 || echo 1)"
    fi
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
