#!/bin/bash
set -e

# ============================================================
# LiveCoachHub — Backend Entrypoint
#
# Auto-download .env dari Secret Gist jika belum ada.
# Ini memungkinkan zero-config demo: juri cuma docker compose up.
# ============================================================

ENV_FILE="/app/.env"

# URL Secret Gist — dikonfigurasi via docker-compose.yml environment
GIST_URL="${ENV_GIST_URL:-}"

if [ ! -f "$ENV_FILE" ]; then
    if [ -n "$GIST_URL" ]; then
        echo "📥 Downloading environment configuration..."
        curl -sfL "$GIST_URL" -o "$ENV_FILE" 2>/dev/null && {
            echo "✅ Environment loaded successfully"
        } || {
            echo "⚠️  Could not download .env — running in fallback mode"
        }
    else
        echo "ℹ️  No .env file found and no ENV_GIST_URL set — running in fallback mode"
    fi
fi

# Jalankan command asli (uvicorn)
exec "$@"
