#!/bin/bash
# LiveCoachHub — Script 1 Perintah untuk Menjalankan Seluruh Service

# 1. Bersihkan port lama jika ada yang nyangkut agar tidak error
fuser -k 3000/tcp 8000/tcp 8010/tcp >/dev/null 2>&1

export PATH=/home/fauzi-k/node-bin/bin:$PATH
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Menjalankan LiveCoachHub (NLP, Backend, & Frontend)..."

# 2. Jalankan NLP Service (Port 8010)
(cd "$PROJECT_ROOT/AI/NLP" && venv/bin/python fine-tuned-indobert/serve.py --port 8010) &

# 3. Jalankan Backend API (Port 8000)
(cd "$PROJECT_ROOT/backend" && venv/bin/uvicorn app.main:app --reload --port 8000) &

# 4. Jalankan Frontend (Port 3000)
cd "$PROJECT_ROOT/frontend" && npm run dev
