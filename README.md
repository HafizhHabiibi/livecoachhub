<div align="center">

# LiveCoachHub

**AI Decision-Support Copilot untuk Live Commerce**

[![COMPFEST 18](https://img.shields.io/badge/COMPFEST_18-AI_Innovation_Challenge_2026-blue?style=for-the-badge)](https://compfest.id/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)

Sistem real-time yang membaca komentar audiens, mengidentifikasi pola/intent menggunakan **IndoBERT fine-tuned**, lalu memberikan **recommended action** dan **suggested seller script** melalui **Gemini API** yang di-ground pada fakta produk.

</div>

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Arsitektur Pipeline](#-arsitektur-pipeline)
- [Prasyarat](#-prasyarat)
- [Quick Start](#-quick-start)
- [Skenario Demo](#-skenario-demo)
- [Verifikasi & Smoke Test](#-verifikasi--smoke-test)
- [Development Lokal](#-development-lokal-tanpa-docker)
- [Struktur Repository](#-struktur-repository)
- [API Endpoints](#-api-endpoints)
- [Docker Commands Reference](#-docker-commands-reference)
- [Troubleshooting](#-troubleshooting)
- [Limitations](#-limitations)
- [Referensi](#-referensi)

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 🧠 **NLP Intent Classification** | IndoBERT fine-tuned mengklasifikasikan intent komentar ke 8 kelas |
| 🤖 **Gemini API LLM Generation** | **Gemini API** menghasilkan seller script yang di-ground pada fakta produk |
| 🔄 **Auto-Rotation API Key** | Rotasi otomatis antar multi Gemini API key saat rate limit — demo tanpa gangguan |
| 📊 **Rolling Window Analytics** | Agregasi sinyal audiens per 60 detik untuk mendeteksi tren |
| 🚨 **Priority Alert System** | Deteksi komentar high-value (purchase intent, complaint) secara real-time |
| 🛡️ **Spam Filter** | Filtrasi spam dan duplikat sebelum diproses NLP |
| ✅ **Output Validator** | Verifikasi JSON, grounding, dan fallback otomatis |
| 📦 **Dockerized Full Stack** | Satu command untuk menjalankan seluruh pipeline |

---

## 🏗️ Arsitektur Pipeline

```
Comment → Preprocessing → Spam Filter → NLP (IndoBERT)
  → Taxonomy Adapter → Rolling Window 60s
  → [Trend Lane]    → Action Engine → Fact Retrieval → LLM (Gemini) → Validator → Coach Card
  → [Priority Lane] → Priority Alert
```

### Komponen AI

| Komponen | Model / Teknik | Fungsi |
|----------|----------------|--------|
| **NLP** | IndoBERT fine-tuned | Klasifikasi intent komentar (8 kelas) |
| **LLM** | Gemini API (`gemini-2.5-flash`) | Generate seller script — tanpa GPU |
| **Validator** | Rule-based | Verifikasi JSON, grounding, fallback |
| **Action Engine** | Threshold + priority | Pilih tindakan berdasarkan audience state |

### Arsitektur Docker

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Docker Compose Network (livecoach)              │
│                                                                      │
│  ┌──────────────┐    ┌───────────────┐    ┌────────────────────┐    │
│  │   Frontend    │    │    Backend    │    │    NLP Service      │    │
│  │  (Nginx:80)  │───▶│  (FastAPI:    │───▶│  (IndoBERT: 8010)  │    │
│  │  :3000→:80   │    │   8000)       │    └────────────────────┘    │
│  └──────────────┘    │               │                               │
│                      │  LLM Client   │──▶  ☁️ Gemini API             │
│                      └───────────────┘                               │
│                                                                      │
│  Volumes:                                                            │
│    hf-cache-nlp → /root/.cache/huggingface (NLP model cache)        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📌 Prasyarat

| Kebutuhan | Minimum |
|-----------|---------|
| **Docker & Docker Compose** | Docker v24+, Compose v2.0+ |
| **RAM** | 8 GB |
| **Disk Space** | ~5 GB (image + model IndoBERT) |
| **Internet** | Koneksi untuk download model pertama kali (~500 MB, sekali saja) |

> [!NOTE]
> **GPU tidak diperlukan.** Sistem menggunakan **Gemini API** (cloud) untuk LLM generation dan IndoBERT untuk NLP classification.

### Khusus Windows

| Kebutuhan | Keterangan |
|-----------|-----------|
| **OS** | Windows 10 (Build 19041+) atau Windows 11 |
| **WSL 2** | Wajib aktif — jalankan `wsl --install` di PowerShell Admin lalu restart |
| **Docker Desktop** | Download dari [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/), pastikan opsi **"Use WSL 2"** tercentang |
| **Git** | [git-scm.com/download/win](https://git-scm.com/download/win) |

> [!TIP]
> **Alokasi resource yang disarankan** (Docker Desktop → Settings → Resources): RAM 8 GB+, Disk 50 GB+, lalu klik *Apply & Restart*.

---

## 🚀 Quick Start

Langkah yang sama untuk **Linux, macOS, dan Windows** (di Git Bash/WSL):

```bash
git clone https://github.com/HafizhHabiibi/livecoachhub.git
cd livecoachhub
docker compose up --build
```

Tunggu hingga semua service ready. **Pertama kali** memakan waktu ~5-10 menit karena download model (~500 MB). Selanjutnya akan lebih cepat karena model di-cache ke Docker volume.

Setelah semua siap, buka browser:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **NLP Service** | http://localhost:8010 |

> [!IMPORTANT]
> **API key Gemini sudah terkonfigurasi** di dalam image — tidak perlu setup apapun. Sistem langsung aktif menggunakan Gemini API.

---

## 🎬 Skenario Demo

File demo tersedia di `data/replay/comments-demo.jsonl` — berisi **30 komentar** dari **19 user** yang mensimulasikan sesi live selling **~90 detik**.

### Cara Menjalankan Demo

1. Buka **http://localhost:3000**
2. **Drag & drop** file `comments-demo.jsonl` ke area upload
3. Klik tombol **▶ Start**
4. Amati dashboard:
   - **Kiri**: Progress replay dan komentar masuk
   - **Kanan atas**: Stream komentar real-time dengan intent classification
   - **Kanan tengah**: Audience snapshot (agregasi 60 detik)
   - **Kanan bawah**: Seller script yang di-generate AI

| Tombol | Fungsi |
|--------|--------|
| ▶ **Start** | Mulai replay |
| ⏸ **Pause** | Jeda replay |
| ▶ **Resume** | Lanjutkan dari jeda |
| ↺ **Reset** | Reset dan mulai ulang |

### Cakupan Intent

| Intent | Contoh Komentar | Aksi Pipeline |
|--------|----------------|---------------|
| `size_inquiry` | "bb 55 ambil m atau l kak?" | `SHOW_SIZE_GUIDE` |
| `size_recommendation` | "aku TB 170 BB 65 cocok L atau XL?" | `SHOW_SIZE_GUIDE` |
| `product_inquiry` | "bahannya apa kak? adem gak?" | `EXPLAIN_PRODUCT_DETAIL` |
| `color_inquiry` | "warnanya ada apa aja kak?" | `CONFIRM_STOCK` |
| `price_inquiry` | "harganya berapa kak?" | `EXPLAIN_PRICE_PROMO` |
| `stock_availability` | "yang hitam masih ready gak?" | `CONFIRM_STOCK` |
| `purchase_intent` | "ok fix order navy L ya kak" | Priority Alert |
| `not_relevant` | "semangat kak jualan nya" | `NO_ACTION` |

> [!TIP]
> Juri juga bisa membuat file `.jsonl` sendiri. Format setiap baris: `{"comment_id": "...", "user_id": "...", "timestamp_ms": ..., "text": "..."}`

---

## ✅ Verifikasi & Smoke Test

```bash
# Health check — harus return status READY
curl http://localhost:8000/health

# Smoke test otomatis (Linux/macOS/Git Bash)
bash scripts/smoke_test.sh
```

<details>
<summary><strong>Smoke Test Manual — PowerShell (Windows)</strong></summary>

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Start session
$session = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/session/start" `
    -ContentType "application/json" `
    -Body '{"product_id":"TSHIRT-01"}'
$session.session_id

# Analyze comment
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/comments/analyze" `
    -ContentType "application/json" `
    -Body "{`"session_id`":`"$($session.session_id)`",`"comment_id`":`"CMT-01`",`"user_id`":`"USR-01`",`"timestamp_ms`":1000,`"text`":`"bb 55 ambil size apa kak`"}"

# Reset session
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/session/reset" `
    -ContentType "application/json" `
    -Body "{`"session_id`":`"$($session.session_id)`"}"
```

</details>

---

## 🔧 Development Lokal (Tanpa Docker)

<details>
<summary><strong>Backend (FastAPI)</strong></summary>

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

</details>

<details>
<summary><strong>Frontend (Vite + React)</strong></summary>

```bash
cd frontend
npm install && npm run dev
```

</details>

<details>
<summary><strong>NLP Service (IndoBERT)</strong></summary>

```bash
python scripts/download_models.py --nlp

cd AI/NLP/fine-tuned-indobert
pip install -r requirements-inference.txt
python serve.py --port 8010
```

</details>

---

## 📁 Struktur Repository

```
LiveCoachHub/
├── frontend/                      # React + TypeScript + Vite
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
├── backend/                       # FastAPI pipeline
│   ├── Dockerfile
│   ├── entrypoint.sh              # Auto-decrypt .env.enc saat start
│   ├── .env.enc                   # API key terenkripsi (AES-256)
│   ├── app/main.py                # Entry point (5 endpoints)
│   ├── llm_client.py              # Gemini API client + auto-rotation key
│   ├── config.py                  # Konfigurasi global
│   ├── orchestrator.py
│   ├── preprocessing/
│   ├── spam_filter/
│   ├── rolling_window/
│   ├── priority_detector/
│   ├── taxonomy_adapter/
│   ├── action_engine/
│   ├── knowledge/
│   ├── validator/
│   └── replay/
├── AI/
│   ├── NLP/fine-tuned-indobert/   # IndoBERT inference service (:8010)
│   └── LLM/grounded_llm/         # Action Engine, Knowledge Base, Validator
├── data/
│   ├── replay/                    # File replay demo (.jsonl)
│   └── product_facts/             # Fakta produk (mock catalog)
├── scripts/
│   ├── download_models.py
│   └── smoke_test.sh
├── docs/                          # Dokumentasi tambahan
├── docker-compose.yml
└── README.md
```

---

## 📡 API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| `GET` | `/health` | Health check + provenance (AI vs fallback) |
| `GET` | `/api/v1/demo-config` | Konfigurasi demo |
| `POST` | `/api/v1/session/start` | Buat session replay baru |
| `POST` | `/api/v1/comments/analyze` | **Core** — jalankan pipeline per komentar |
| `POST` | `/api/v1/session/reset` | Reset session |

---

## 📝 Docker Commands Reference

```bash
# Start (foreground)
docker compose up --build

# Start (background)
docker compose up --build -d

# Stop
docker compose down

# Stop + hapus volume cache (akan download ulang model!)
docker compose down -v

# Lihat log
docker compose logs -f
docker compose logs -f backend

# Status container
docker compose ps

# Resource usage
docker stats

# Restart satu service
docker compose restart backend

# Masuk ke container
docker compose exec backend bash

# Force rebuild tanpa cache
docker compose build --no-cache && docker compose up
```

---

## 🔥 Troubleshooting

<details>
<summary><strong>❌ <code>docker compose</code> tidak dikenali</strong></summary>

Docker Desktop belum running atau PATH belum ter-set.

1. Buka Docker Desktop dan pastikan statusnya **running**
2. Restart terminal
3. Jika masih gagal, coba `docker-compose` (dengan tanda hubung — versi lama)

</details>

<details>
<summary><strong>❌ Port sudah dipakai (port already in use)</strong></summary>

**Linux/macOS:**
```bash
lsof -i :8000
kill -9 <PID>
```

**Windows:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Atau ubah port di `docker-compose.yml`: `"9000:8000"` (ganti 8000 host ke 9000).

</details>

<details>
<summary><strong>❌ Build gagal — out of memory</strong></summary>

Docker tidak punya cukup RAM.

- **Windows**: Docker Desktop → Settings → Resources → Naikkan **Memory** ke minimum 8 GB
- **Linux**: Tambah swap atau tutup aplikasi lain

</details>

<details>
<summary><strong>❌ Model download lambat / timeout</strong></summary>

Model di-cache di Docker volume, jadi hanya perlu download sekali. Jika timeout saat pertama:

```bash
docker compose restart nlp
```

</details>

<details>
<summary><strong>❌ Line ending issue — CRLF vs LF (Windows)</strong></summary>

```powershell
git config --global core.autocrlf input
git clone https://github.com/HafizhHabiibi/livecoachhub.git
```

</details>

---

## ⚠️ Limitations

- **Replay mode only** — bukan real-time stream (fitur final jika lolos)
- **Satu produk mock** — Essential Cotton T-Shirt
- **Membutuhkan internet** — untuk Gemini API dan download model pertama kali
- **Belum ada auth/login** — sesuai batas MVP preliminary

---

## 📚 Referensi

| Resource | Link |
|----------|------|
| Docker Desktop | [docs.docker.com/desktop](https://docs.docker.com/desktop/install/windows-install/) |
| WSL 2 Installation | [learn.microsoft.com/windows/wsl/install](https://learn.microsoft.com/en-us/windows/wsl/install) |
| Docker Compose Docs | [docs.docker.com/compose](https://docs.docker.com/compose/) |
| Dokumentasi Teknis | [`docs/README.md`](docs/README.md) |
| Desain Sistem | [`PROJECT.md`](PROJECT.md) |
| Audit Checklist | [`AUDIT.md`](AUDIT.md) |
