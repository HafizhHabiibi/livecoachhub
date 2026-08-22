# LiveCoachHub

**AI Decision-Support Copilot untuk Live Commerce**

> COMPFEST 18 — AI Innovation Challenge 2026

Sistem membaca komentar audiens, mengidentifikasi pola/intent menggunakan **IndoBERT fine-tuned**, lalu memberikan **recommended action** dan **suggested seller script** melalui **Qwen2.5 + QLoRA** yang grounded pada fakta produk.

---

## 🚀 Quick Start

### Prasyarat

| Kebutuhan | Minimum |
|-----------|---------|
| Docker & Docker Compose | v2.0+ |
| RAM | 8 GB |
| GPU (opsional) | NVIDIA dengan CUDA (untuk LLM service) |
| Internet | Koneksi untuk download model HuggingFace (~3.5 GB total, sekali saja) |

> **Tanpa GPU**: Sistem tetap berjalan — NLP menggunakan keyword heuristic fallback, LLM menggunakan template fallback. Untuk demo penuh dengan AI, GPU NVIDIA diperlukan.

### Satu Command Startup

```bash
git clone https://github.com/HafizhHabiibi/livecoachhub.git
cd livecoachhub
docker compose up --build
```

Tunggu hingga semua service ready (~2-5 menit pertama kali, model akan di-download otomatis).

| Service | URL | Deskripsi |
|---------|-----|-----------|
| Frontend | http://localhost:3000 | Dashboard demo |
| Backend API | http://localhost:8000 | FastAPI pipeline |
| NLP Service | http://localhost:8010 | IndoBERT intent classifier |
| LLM Service | http://localhost:8020 | QLoRA seller script generator |

### Verifikasi

```bash
# Health check (harus return status READY atau DEGRADED)
curl http://localhost:8000/health

# Smoke test lengkap
bash scripts/smoke_test.sh
```

---

## 🏗️ Arsitektur Pipeline

```
Comment → Preprocessing → Spam Filter → NLP (IndoBERT)
  → Taxonomy Adapter → Rolling Window 60s
  → [Trend Lane] → Action Engine → Fact Retrieval → LLM (QLoRA) → Validator → Coach Card
  → [Priority Lane] → Priority Alert
```

### Komponen AI

| Komponen | Model/Teknik | Fungsi |
|----------|-------------|--------|
| **NLP** | IndoBERT fine-tuned | Klasifikasi intent komentar (8 kelas) |
| **LLM** | Qwen2.5-1.5B + QLoRA | Generate seller script yang grounded |
| **Validator** | Rule-based | Verifikasi JSON, grounding, fallback |
| **Action Engine** | Threshold + priority | Pilih tindakan berdasarkan audience state |

---

## 📁 Struktur Repository

```
LiveCoachHub/
├── frontend/                  # React + TypeScript + Vite
│   ├── Dockerfile             # Multi-stage: dev & production
│   └── src/                   # Source code frontend
├── backend/                   # FastAPI pipeline
│   ├── Dockerfile             # Runtime-only
│   ├── app/main.py            # Entry point (5 endpoints)
│   ├── orchestrator.py        # Pipeline orchestrator
│   ├── preprocessing/         # Normalisasi teks
│   ├── spam_filter/           # Deteksi spam/duplikat
│   ├── rolling_window/        # Agregasi sinyal 60 detik
│   ├── priority_detector/     # Deteksi komentar high-value
│   ├── taxonomy_adapter/      # Mapping NLP → Action Engine
│   ├── action_engine/         # Wrapper Action Engine
│   ├── knowledge/             # Wrapper Knowledge Base
│   ├── validator/             # Wrapper Validator
│   └── replay/                # Replay engine utility
├── AI/
│   ├── NLP/                   # IndoBERT NLP subproject
│   │   └── fine-tuned-indobert/
│   │       ├── Dockerfile     # Inference-only
│   │       └── serve.py       # FastAPI inference service (:8010)
│   └── LLM/                   # QLoRA LLM subproject
│       ├── Dockerfile         # Inference service
│       ├── serve_llm.py       # FastAPI inference service (:8020)
│       ├── livecoach-qlora-adapter/  # QLoRA adapter weights
│       └── grounded_llm/      # Action Engine, KB, Validator, dataset
├── data/
│   ├── replay/                # File replay demo (.jsonl)
│   └── product_facts/         # Fakta produk (mock catalog)
├── scripts/
│   ├── download_models.py     # Download model dari HuggingFace
│   └── smoke_test.sh          # End-to-end smoke test
├── docker-compose.yml         # Orchestrasi semua service
└── README.md                  # (file ini)
```

---

## 📡 API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/health` | Health check + provenance (AI vs fallback) |
| GET | `/api/v1/demo-config` | Konfigurasi demo |
| POST | `/api/v1/session/start` | Buat session replay baru |
| POST | `/api/v1/comments/analyze` | **Core**: jalankan pipeline per komentar |
| POST | `/api/v1/session/reset` | Reset session |

---

## 🎯 Skenario Demo

Replay data (`data/replay/comments-demo.jsonl`) mensimulasikan sesi live selling 52 detik dengan 8 komentar dari 6 user:

1. **Size confusion** — Beberapa user bertanya ukuran → `SHOW_SIZE_GUIDE`
2. **Purchase intent** — User menyatakan niat checkout → Priority Alert
3. **Stock inquiry** — User bertanya ketersediaan warna → `CONFIRM_STOCK`

---

## ⚠️ Limitations (Preliminary)

- **Replay mode only** — bukan real-time stream (fitur final jika lolos)
- **Satu produk mock** — Essential Cotton T-Shirt
- **GPU diperlukan** untuk AI penuh — tanpa GPU, menggunakan fallback
- **Model download** — perlu koneksi internet saat pertama kali
- **Belum ada auth/login** — sesuai batas MVP preliminary

---

## 🔧 Development (tanpa Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm run dev

# NLP (perlu model — jalankan download dulu)
python scripts/download_models.py --nlp
cd AI/NLP/fine-tuned-indobert
pip install -r requirements-inference.txt
python serve.py --port 8010

# LLM (perlu GPU)
cd AI/LLM
pip install -r grounded_llm/LLM\ dengan\ QLoRA/requirements_qlora.txt
python serve_llm.py --port 8020
```
