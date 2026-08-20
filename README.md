# LiveCoachHub

AI Decision-Support Copilot untuk Live Commerce.

Sistem membaca komentar audiens, mengidentifikasi pola/intent, lalu memberikan **recommended action** dan **suggested seller script** yang dapat dipilih host.

## Quick Start

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Vite + React)

```bash
cd frontend
npm install
npm run dev
```

Frontend akan berjalan di `http://localhost:5173` dan menghubungi backend di `http://localhost:8000`.

### 3. NLP Service (Opsional — jika model IndoBERT sudah di-train)

```bash
cd ai/intent_classifier
pip install -r requirements-ml.txt
python ml/serve.py --port 8010
```

Jika NLP service tidak dijalankan, backend otomatis menggunakan keyword-based fallback.

## Arsitektur Pipeline

```
Comment → Preprocessing → Spam Filter → NLP (IndoBERT)
→ Taxonomy Adapter → Rolling Window 60s
→ [Trend Lane] → Action Engine → Fact Retrieval → LLM → Validator → Coach Card
→ [Priority Lane] → Priority Alert
```

## Struktur Repository

```
LiveCoachHub/
├── frontend/          # React + TypeScript + Vite
├── backend/           # FastAPI pipeline
│   ├── app/           # Entry point (main.py)
│   ├── preprocessing/ # Normalisasi teks
│   ├── spam_filter/   # Deteksi spam/duplikat
│   ├── rolling_window/# Agregasi sinyal 60 detik
│   ├── priority_detector/ # Deteksi komentar high-value
│   ├── taxonomy_adapter/  # Mapping NLP → Action Engine
│   ├── action_engine/ # Wrapper Action Engine
│   ├── knowledge/     # Wrapper Knowledge Base
│   ├── validator/     # Wrapper Validator
│   └── replay/        # Replay engine utility
├── ai/
│   ├── intent_classifier/  # IndoBERT NLP (fine-tuned)
│   └── grounded_llm/       # Action Engine + KB + QLoRA + Validator
├── data/
│   ├── replay/        # File replay demo (.jsonl)
│   └── product_facts/ # Fakta produk (mock catalog)
├── models/            # Model artifacts
├── docs/              # Dokumentasi teknis
└── docker-compose.yml # Orchestrasi semua service
```

## API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/health` | Health check |
| GET | `/api/v1/demo-config` | Konfigurasi demo |
| POST | `/api/v1/session/start` | Buat session baru |
| POST | `/api/v1/comments/analyze` | **Core**: jalankan pipeline |
| POST | `/api/v1/session/reset` | Reset session |

## Limitations (Preliminary)

- Replay mode only (bukan real-time stream)
- Satu produk mock (Essential Cotton T-Shirt)
- LLM fallback menggunakan template jika QLoRA belum di-train
- NLP fallback menggunakan keyword heuristic jika IndoBERT belum tersedia
