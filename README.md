<div align="center">

# LiveCoachHub

**AI Decision-Support Copilot untuk Live Commerce**

[![COMPFEST 18](https://img.shields.io/badge/COMPFEST_18-AI_Innovation_Challenge_2026-blue?style=for-the-badge)]()
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)]()
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black)]()

Sistem real-time yang membaca komentar audiens, mengidentifikasi pola/intent menggunakan **IndoBERT fine-tuned**, lalu memberikan **recommended action** dan **suggested seller script** melalui **LLM dual-mode** (Gemini API / Qwen2.5 + QLoRA) yang di-ground pada fakta produk.

</div>

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Arsitektur Pipeline](#-arsitektur-pipeline)
- [Prasyarat](#-prasyarat)
- [Quick Start — Docker (Linux / macOS)](#-quick-start--docker-linux--macos)
- [Quick Start — Docker (Windows)](#-quick-start--docker-windows)
- [Setup GPU (Opsional)](#-setup-gpu-opsional)
- [Menjalankan Tanpa GPU (Fallback Mode)](#-menjalankan-tanpa-gpu-fallback-mode)
- [Verifikasi & Smoke Test](#-verifikasi--smoke-test)
- [Development Lokal (Tanpa Docker)](#-development-lokal-tanpa-docker)
- [Struktur Repository](#-struktur-repository)
- [API Endpoints](#-api-endpoints)
- [Skenario Demo](#-skenario-demo)
- [Docker Commands Reference](#-docker-commands-reference)
- [Troubleshooting](#-troubleshooting)
- [Limitations](#-limitations)
- [Referensi](#-referensi)

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 🧠 **NLP Intent Classification** | IndoBERT fine-tuned mengklasifikasikan intent komentar ke 8 kelas |
| 🤖 **Dual-Mode LLM Generation** | **Gemini API** (cloud) atau **Qwen2.5 + QLoRA** (local GPU) menghasilkan seller script yang di-ground pada fakta produk |
| 🔄 **Auto-Rotation API Key** | Rotasi otomatis antar multi API key saat rate limit — demo tanpa gangguan |
| 📊 **Rolling Window Analytics** | Agregasi sinyal audiens per 60 detik untuk mendeteksi tren |
| 🚨 **Priority Alert System** | Deteksi komentar high-value (purchase intent, complaint) secara real-time |
| 🛡️ **Spam Filter** | Filtrasi spam dan duplikat sebelum diproses NLP |
| ✅ **Output Validator** | Verifikasi JSON, grounding, dan fallback otomatis |
| 📦 **Dockerized Full Stack** | Satu command untuk menjalankan semua service |

---

## 🏗️ Arsitektur Pipeline

```
Comment → Preprocessing → Spam Filter → NLP (IndoBERT)
  → Taxonomy Adapter → Rolling Window 60s
  → [Trend Lane] → Action Engine → Fact Retrieval → LLM (QLoRA) → Validator → Coach Card
  → [Priority Lane] → Priority Alert
```

### Komponen AI

| Komponen | Model / Teknik | Fungsi |
|----------|----------------|--------|
| **NLP** | IndoBERT fine-tuned | Klasifikasi intent komentar (8 kelas) |
| **LLM (Cloud)** | Gemini API (gemini-2.0-flash) | Generate seller script — default, tanpa GPU |
| **LLM (Local)** | Qwen2.5-1.5B + QLoRA | Generate seller script — opsional, butuh GPU |
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
│                      │  LLM Client   │──▶  ☁️ Gemini API (default)  │
│                      │  (dual-mode)  │                               │
│                      └───────────────┘    ┌────────────────────┐    │
│                                           │  🤖 QLoRA Service   │    │
│                          (opsional) ◀─────│ (Qwen2.5: 8020)    │    │
│                                           │ [profile: qlora]   │    │
│  Volumes:                                 └────────────────────┘    │
│    hf-cache-nlp → /root/.cache/huggingface (NLP model cache)        │
│    hf-cache-llm → /root/.cache/huggingface (LLM model cache)        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📌 Prasyarat

### Semua Platform

| Kebutuhan | Minimum |
|-----------|---------|
| **Docker & Docker Compose** | Docker v24+, Compose v2.0+ |
| **RAM** | 8 GB (disarankan 16 GB jika pakai LLM) |
| **Disk Space** | ~10 GB (image + model HuggingFace) |
| **Internet** | Koneksi untuk download model pertama kali (~3.5 GB total, sekali saja) |
| **GPU** _(opsional)_ | NVIDIA dengan CUDA (untuk LLM service penuh) |

> [!NOTE]
> **Tanpa GPU**: Sistem tetap berjalan penuh menggunakan **Gemini API** (default). GPU hanya diperlukan jika ingin menggunakan mode **QLoRA local**.

### Khusus Windows

| Kebutuhan | Minimum |
|-----------|---------|
| **OS** | Windows 10 (Build 19041+) atau Windows 11 |
| **WSL 2** | Wajib aktif (backend Docker Desktop) |
| **Git** | [Git for Windows](https://git-scm.com/download/win) |

---

## 🚀 Quick Start — Docker (Linux / macOS)

### 1. Clone & Jalankan

```bash
git clone https://github.com/HafizhHabiibi/livecoachhub.git
cd livecoachhub
docker compose up --build
```

Tunggu hingga semua service ready (~2-5 menit pertama kali, model akan di-download otomatis).

### 2. Akses Aplikasi

| Service | URL | Deskripsi |
|---------|-----|-----------|
| **Frontend** | http://localhost:3000 | Dashboard demo LiveCoachHub |
| **Backend API** | http://localhost:8000 | FastAPI pipeline |
| **NLP Service** | http://localhost:8010 | IndoBERT intent classifier |
| **LLM Service** | http://localhost:8020 | QLoRA seller script generator |

### 3. Verifikasi

```bash
# Health check (harus return status READY atau DEGRADED)
curl http://localhost:8000/health

# Smoke test lengkap
bash scripts/smoke_test.sh
```

---

## 🪟 Quick Start — Docker (Windows)

### Step 1 — Aktifkan WSL 2

Buka **PowerShell sebagai Administrator**:

```powershell
# Aktifkan fitur WSL dan Virtual Machine Platform
wsl --install

# Restart komputer jika diminta, lalu set WSL 2 sebagai default
wsl --set-default-version 2
```

> [!NOTE]
> Jika `wsl --install` gagal, aktifkan secara manual melalui:
> **Control Panel → Programs → Turn Windows Features on or off**
> → Centang **Windows Subsystem for Linux** dan **Virtual Machine Platform**, lalu restart.

### Step 2 — Install Docker Desktop

1. Download dari [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Jalankan installer, pastikan opsi **"Use WSL 2 instead of Hyper-V"** tercentang
3. Restart komputer setelah instalasi selesai
4. Buka **Docker Desktop** dan tunggu hingga status di taskbar berubah menjadi **"Docker Desktop is running"**

### Step 3 — Verifikasi Instalasi Docker

```powershell
docker --version
# Output contoh: Docker version 27.x.x, build xxxxx

docker compose version
# Output contoh: Docker Compose version v2.x.x
```

### Step 4 — Alokasi Resource Docker (Disarankan)

Buka **Docker Desktop → Settings → Resources → Advanced**:

| Resource | Rekomendasi |
|----------|-------------|
| CPUs | 4+ cores |
| Memory | 8 GB (16 GB jika pakai LLM) |
| Swap | 2 GB |
| Disk | 50 GB+ |

Klik **Apply & Restart**.

### Step 5 — Clone & Jalankan

Buka **PowerShell** atau **Git Bash**:

```powershell
git clone https://github.com/HafizhHabiibi/livecoachhub.git
cd livecoachhub
docker compose up --build
```

> [!IMPORTANT]
> **Pertama kali menjalankan akan memakan waktu ~5-15 menit** karena:
> - Build Docker image untuk 4 service
> - Download model HuggingFace (IndoBERT ~500 MB, Qwen2.5 ~3 GB)
> - Model akan di-cache ke Docker volume, jadi download hanya sekali

Tunggu hingga muncul log seperti:

```
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend-1  | ... ready in ...
nlp-1       | INFO:     Uvicorn running on http://0.0.0.0:8010
llm-1       | INFO:     Uvicorn running on http://0.0.0.0:8020
```

### Step 6 — Akses Aplikasi

Buka browser dan kunjungi URL yang sama seperti di [tabel service](#2-akses-aplikasi).

---

## 🎮 Setup GPU (Opsional)

> [!NOTE]
> GPU **hanya diperlukan** untuk service **LLM (Qwen2.5 + QLoRA)**. Tanpa GPU, sistem tetap
> berjalan menggunakan **fallback mode** (template-based).

### Prasyarat GPU

1. **GPU NVIDIA** (GTX 1060+ / RTX series disarankan, VRAM minimum 4 GB)
2. **NVIDIA Driver** terbaru — download dari [https://www.nvidia.com/drivers](https://www.nvidia.com/drivers)
3. **NVIDIA Container Toolkit**
   - **Linux**: Install sesuai [panduan resmi](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
   - **Windows**: Otomatis tersedia via Docker Desktop + WSL 2

### Verifikasi GPU

<details>
<summary><strong>Linux / macOS</strong></summary>

```bash
# Cek driver
nvidia-smi

# Test GPU di Docker
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
# Pastikan driver NVIDIA terdeteksi di WSL
wsl -- nvidia-smi

# Test GPU di Docker container
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

</details>

Jika perintah di atas menampilkan info GPU, jalankan dengan **GPU override**:

```bash
# Dengan GPU — gunakan file override tambahan
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

---

## 💻 Menjalankan Tanpa GPU (Default — Gemini API)

Tanpa GPU, cukup jalankan seperti biasa — **tidak perlu konfigurasi tambahan**:

```bash
docker compose up --build
```

Backend secara default menggunakan **Gemini API** sebagai LLM provider. API key di-download otomatis saat pertama kali start.

### Mode QLoRA (Butuh GPU NVIDIA)

Jika ingin menggunakan QLoRA local (Qwen2.5 + adapter), aktifkan profile `qlora`:

```bash
# Dengan GPU + QLoRA
docker compose --profile qlora -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

### Perbandingan Mode

| Komponen | Gemini API (Default) | QLoRA (Opsional) | Template Fallback |
|----------|---------------------|------------------|-------------------|
| **LLM Provider** | ☁️ Google Gemini | 🤖 Qwen2.5 + QLoRA | 📝 Template bawaan |
| **Kebutuhan** | Internet + API Key | GPU NVIDIA (4GB+ VRAM) | Tidak ada |
| **Kecepatan** | ~1-3 detik | ~5-15 detik | Instan |
| **Kualitas Output** | Tinggi | Menengah | Dasar |
| **Docker Profile** | Default | `--profile qlora` | Otomatis jika LLM gagal |
| **Health Status** | `READY` | `READY` | `DEGRADED` |

> [!TIP]
> Untuk demo dan evaluasi, mode **Gemini API (default)** sudah memberikan pengalaman AI penuh tanpa perlu GPU.

---

## 🎬 Panduan Demo

Berikut langkah-langkah untuk menjalankan demo LiveCoachHub setelah semua service berjalan:

### 1. Siapkan File Replay

File demo sudah tersedia di repo:

```
data/replay/comments-demo.jsonl
```

File ini berisi **30 komentar** dari **19 user** yang mensimulasikan sesi live selling **~90 detik**, mencakup semua kategori intent:

| Intent | Contoh Komentar |
|--------|----------------|
| `size_inquiry` | "bb 55 ambil m atau l kak?" |
| `size_recommendation` | "aku TB 170 BB 65 cocok L atau XL?" |
| `product_inquiry` | "bahannya apa kak? adem gak?" |
| `color_inquiry` | "warnanya ada apa aja kak?" |
| `price_inquiry` | "harganya berapa kak?" |
| `stock_availability` | "yang hitam masih ready gak?" |
| `purchase_intent` | "ok fix order navy L ya kak" |
| `not_relevant` | "semangat kak jualan nya" |

### 2. Jalankan Demo

1. Buka **http://localhost:3000** di browser
2. Pastikan status di header menunjukkan **"Sistem siap"** (hijau) atau **"Sistem terdegradasi"** (kuning)
3. **Drag & drop** file `comments-demo.jsonl` ke area upload, atau klik untuk browse
4. Klik tombol **▶ Start**
5. Amati dashboard:
   - **Kiri**: Progress replay dan komentar masuk
   - **Kanan atas**: Stream komentar real-time dengan intent classification chips
   - **Kanan tengah**: Audience snapshot (agregasi 60 detik)
   - **Kanan bawah**: Seller script yang di-generate AI

### 3. Kontrol Replay

| Tombol | Fungsi |
|--------|--------|
| ▶ **Start** | Mulai replay |
| ⏸ **Pause** | Jeda replay |
| ▶ **Resume** | Lanjutkan dari jeda |
| ↺ **Reset** | Reset dan mulai ulang |

> [!TIP]
> Juri juga bisa membuat file `.jsonl` sendiri dengan format yang sama untuk menguji skenario custom.
> Setiap baris berisi: `{"comment_id": "...", "user_id": "...", "timestamp_ms": ..., "text": "..."}`

---

## ✅ Verifikasi & Smoke Test

### Health Check

```bash
# Harus return status READY atau DEGRADED
curl http://localhost:8000/health
```

### Smoke Test Otomatis

```bash
bash scripts/smoke_test.sh
```

> [!NOTE]
> **Windows**: Jalankan smoke test melalui **Git Bash** atau **WSL terminal** (bukan PowerShell/CMD).

### Smoke Test Manual — PowerShell (Windows)

<details>
<summary>Klik untuk melihat perintah PowerShell</summary>

```powershell
# 1. Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# 2. Demo config
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/demo-config"

# 3. Start session
$session = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/session/start" `
    -ContentType "application/json" `
    -Body '{"product_id":"TSHIRT-01"}'
$session.session_id

# 4. Analyze comment
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/comments/analyze" `
    -ContentType "application/json" `
    -Body "{`"session_id`":`"$($session.session_id)`",`"comment_id`":`"CMT-01`",`"user_id`":`"USR-01`",`"timestamp_ms`":1000,`"text`":`"bb 55 ambil size apa kak`"}"

# 5. Reset session
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
# Download model terlebih dahulu
python scripts/download_models.py --nlp

cd AI/NLP/fine-tuned-indobert
pip install -r requirements-inference.txt
python serve.py --port 8010
```

</details>

<details>
<summary><strong>LLM Service (Qwen2.5 + QLoRA) — Butuh GPU</strong></summary>

```bash
cd AI/LLM
pip install -r grounded_llm/LLM\ dengan\ QLoRA/requirements_qlora.txt
python serve_llm.py --port 8020
```

</details>

---

## 📁 Struktur Repository

```
LiveCoachHub/
├── frontend/                      # React + TypeScript + Vite
│   ├── Dockerfile                 # Multi-stage: dev & production
│   ├── nginx.conf                 # SPA routing config
│   └── src/                       # Source code frontend
├── backend/                       # FastAPI pipeline
│   ├── Dockerfile                 # Runtime-only
│   ├── app/main.py                # Entry point (5 endpoints)
│   ├── orchestrator.py            # Pipeline orchestrator
│   ├── preprocessing/             # Normalisasi teks
│   ├── spam_filter/               # Deteksi spam/duplikat
│   ├── rolling_window/            # Agregasi sinyal 60 detik
│   ├── priority_detector/         # Deteksi komentar high-value
│   ├── taxonomy_adapter/          # Mapping NLP → Action Engine
│   ├── action_engine/             # Wrapper Action Engine
│   ├── knowledge/                 # Wrapper Knowledge Base
│   ├── validator/                 # Wrapper Validator
│   └── replay/                    # Replay engine utility
├── AI/
│   ├── NLP/                       # IndoBERT NLP subproject
│   │   └── fine-tuned-indobert/
│   │       ├── Dockerfile         # Inference-only
│   │       └── serve.py           # FastAPI inference service (:8010)
│   └── LLM/                      # QLoRA LLM subproject
│       ├── Dockerfile             # Inference service
│       ├── serve_llm.py           # FastAPI inference service (:8020)
│       ├── livecoach-qlora-adapter/   # QLoRA adapter weights
│       └── grounded_llm/          # Action Engine, KB, Validator, dataset
├── data/
│   ├── replay/                    # File replay demo (.jsonl)
│   └── product_facts/             # Fakta produk (mock catalog)
├── scripts/
│   ├── download_models.py         # Download model dari HuggingFace
│   └── smoke_test.sh              # End-to-end smoke test
├── docs/                          # Dokumentasi tambahan
├── docker-compose.yml             # Orchestrasi semua service
└── README.md                      # (file ini)
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

## 🎯 Skenario Demo

Replay data (`data/replay/comments-demo.jsonl`) mensimulasikan sesi live selling **~90 detik** dengan **30 komentar** dari **19 user**:

| # | Skenario | Trigger | Aksi Pipeline |
|---|----------|---------|---------------|
| 1 | **Size confusion** | Banyak user bertanya ukuran & rekomendasi | `SHOW_SIZE_GUIDE` |
| 2 | **Product detail** | Pertanyaan bahan, fit, dan fitur produk | `EXPLAIN_PRODUCT_DETAIL` |
| 3 | **Color & stock** | User bertanya warna dan ketersediaan | `CONFIRM_STOCK` |
| 4 | **Price & promo** | Pertanyaan harga, diskon, ongkir | `EXPLAIN_PRICE_PROMO` |
| 5 | **Purchase intent** | User menyatakan niat checkout/order | Priority Alert |
| 6 | **Not relevant** | Sapaan, semangat, dan komentar umum | `NO_ACTION` |

---

## 📝 Docker Commands Reference

### Lifecycle

```bash
# Start semua service (foreground)
docker compose up --build

# Start semua service (background/detached)
docker compose up --build -d

# Stop semua service
docker compose down

# Stop dan hapus volume (reset model cache — akan download ulang!)
docker compose down -v

# Restart satu service saja
docker compose restart backend
```

### Logs & Monitoring

```bash
# Lihat log semua service
docker compose logs -f

# Lihat log service tertentu
docker compose logs -f backend
docker compose logs -f nlp
docker compose logs -f llm

# Lihat status semua container
docker compose ps

# Lihat resource usage
docker stats
```

### Debugging

```bash
# Masuk ke dalam container (contoh: backend)
docker compose exec backend bash

# Rebuild satu service saja (contoh: setelah edit backend code)
docker compose up --build backend

# Force rebuild tanpa cache
docker compose build --no-cache
docker compose up
```

---

## 🔥 Troubleshooting

<details>
<summary><strong>❌ <code>docker compose</code> tidak dikenali</strong></summary>

**Penyebab**: Docker Desktop belum running atau PATH belum ter-set.

**Solusi**:
1. Buka Docker Desktop dan pastikan statusnya **running**
2. Restart terminal (PowerShell/CMD/bash)
3. Jika masih gagal, coba `docker-compose` (dengan tanda hubung — versi lama)

</details>

<details>
<summary><strong>❌ Port sudah dipakai (port already in use)</strong></summary>

**Penyebab**: Aplikasi lain menggunakan port 3000, 8000, 8010, atau 8020.

**Solusi (Linux/macOS)**:
```bash
lsof -i :8000
kill -9 <PID>
```

**Solusi (Windows)**:
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Atau ubah port mapping di `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"   # Ganti 8000 ke 9000 di host
```

</details>

<details>
<summary><strong>❌ Build NLP/LLM gagal — out of memory</strong></summary>

**Penyebab**: Docker tidak punya cukup RAM.

**Solusi**:
- **Windows**: Docker Desktop → Settings → Resources → Naikkan **Memory** (min 8 GB, 16 GB untuk LLM)
- **Linux**: Pastikan host punya cukup RAM, atau tambah swap

</details>

<details>
<summary><strong>❌ LLM service crash / restart loop</strong></summary>

**Penyebab**: Tidak ada GPU atau VRAM tidak cukup.

**Solusi**: Jalankan tanpa GPU menggunakan override file — lihat [Menjalankan Tanpa GPU](#-menjalankan-tanpa-gpu-fallback-mode).

</details>

<details>
<summary><strong>❌ <code>nvidia-smi</code> tidak ditemukan di WSL</strong></summary>

**Penyebab**: NVIDIA Driver belum ter-install atau versi WSL terlalu lama.

**Solusi**:
1. Update NVIDIA Driver ke versi terbaru: [https://www.nvidia.com/drivers](https://www.nvidia.com/drivers)
2. Update WSL: `wsl --update`
3. Restart Docker Desktop

</details>

<details>
<summary><strong>❌ Model download lambat / timeout</strong></summary>

**Penyebab**: Koneksi internet lambat (model total ~3.5 GB).

**Solusi**:
1. Pastikan koneksi internet stabil
2. Model di-cache di Docker volume (`hf-cache-nlp`, `hf-cache-llm`), jadi hanya perlu download sekali
3. Jika timeout, restart service yang gagal:
   ```bash
   docker compose restart nlp
   docker compose restart llm
   ```

</details>

<details>
<summary><strong>❌ <code>Error: ENOENT</code> saat build frontend</strong></summary>

**Penyebab**: File `package-lock.json` tidak ada atau corrupt.

**Solusi**:
```bash
cd frontend
npm install
cd ..
docker compose up --build frontend
```

</details>

<details>
<summary><strong>❌ Line ending issue — CRLF vs LF (Windows)</strong></summary>

**Penyebab**: Git di Windows otomatis mengubah line ending menjadi CRLF, yang bisa menyebabkan error di container Linux.

**Solusi**:
```powershell
# Set git agar tidak mengubah line ending
git config --global core.autocrlf input

# Re-clone repository
git clone https://github.com/HafizhHabiibi/livecoachhub.git
```

Atau tambahkan file `.gitattributes` di root project:
```
* text=auto eol=lf
*.sh text eol=lf
Dockerfile text eol=lf
```

</details>

---

## ⚠️ Limitations

- **Replay mode only** — bukan real-time stream (fitur final jika lolos)
- **Satu produk mock** — Essential Cotton T-Shirt
- **GPU diperlukan** untuk AI penuh — tanpa GPU, menggunakan fallback
- **Model download** — perlu koneksi internet saat pertama kali
- **Belum ada auth/login** — sesuai batas MVP preliminary

---

## 📚 Referensi

| Resource | Link |
|----------|------|
| Docker Desktop (Windows) | [docs.docker.com/desktop/install/windows-install](https://docs.docker.com/desktop/install/windows-install/) |
| WSL 2 Installation | [learn.microsoft.com/windows/wsl/install](https://learn.microsoft.com/en-us/windows/wsl/install) |
| NVIDIA Container Toolkit | [docs.nvidia.com/container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| Docker Compose Docs | [docs.docker.com/compose](https://docs.docker.com/compose/) |
| Dokumentasi Teknis | [`docs/README.md`](docs/README.md) |
| Desain Sistem | [`PROJECT.md`](PROJECT.md) |
| Audit Checklist | [`AUDIT.md`](AUDIT.md) |
