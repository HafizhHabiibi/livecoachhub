#!/bin/sh
set -e

# ============================================================
# LiveCoachHub — Backend Entrypoint
#
# Otomatis dekripsi .env.enc → .env saat container pertama start.
# Juri cuma perlu: docker compose up
# ============================================================

ENV_FILE="/app/.env"
ENV_ENC_FILE="/app/.env.enc"
DECRYPT_PASS="livecoachhub2026"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_ENC_FILE" ]; then
        echo "Decrypting environment configuration..."
        openssl enc -aes-256-cbc -d -pbkdf2 -in "$ENV_ENC_FILE" -out "$ENV_FILE" -pass pass:"$DECRYPT_PASS" 2>/dev/null && {
            echo "Environment loaded successfully"
        } || {
            echo "Decryption failed — running in fallback mode"
        }
    else
        echo "No .env or .env.enc found — running in fallback mode"
    fi
fi

# Jalankan command asli (uvicorn)
exec "$@"
