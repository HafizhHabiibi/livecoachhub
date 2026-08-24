<div align="center">

# LiveCoachHub

**AI decision-support copilot untuk live commerce**

[![COMPFEST 18](https://img.shields.io/badge/COMPFEST_18-AI_Innovation_Challenge_2026-blue?style=for-the-badge)](https://compfest.id/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)

LiveCoachHub membaca komentar audiens, mengklasifikasikan intent menggunakan IndoBERT fine-tuned, mengubahnya menjadi sinyal operasional, lalu memberi host satu recommended action dan seller script yang di-ground pada fakta produk.

</div>

## Daftar isi

- [Fitur utama](#fitur-utama)
- [Arsitektur](#arsitektur)
- [Cara sistem mengambil keputusan](#cara-sistem-mengambil-keputusan)
- [Prasyarat](#prasyarat)
- [Quick start dengan Docker](#quick-start-dengan-docker)
- [Menjalankan demo](#menjalankan-demo)
- [Health check dan smoke test](#health-check-dan-smoke-test)
- [Konfigurasi Gemini](#konfigurasi-gemini)
- [Development lokal tanpa Docker](#development-lokal-tanpa-docker)
- [API](#api)
- [Struktur repository](#struktur-repository)
- [Pengujian](#pengujian)
- [Troubleshooting](#troubleshooting)
- [Batasan MVP](#batasan-mvp)

## Fitur utama

| Fitur | Implementasi |
|---|---|
| Intent classification | IndoBERT fine-tuned dengan delapan raw intent |
| Semantic routing | Taxonomy Adapter mempertahankan perbedaan size, warna, stok, harga, produk, dan purchase intent |
| Slot extraction | Rule-based extraction untuk size, warna, BB, TB, atribut produk, dan topik harga |
| Rolling analytics | Window 60 detik dengan support, pengguna unik, confidence, evidence, timestamp, dan representative slots |
| Action Engine | Deterministic dominance ranking, minimum dua pengguna unik, dan hysteresis |
| Priority Lane | Purchase intent high-confidence ditampilkan sebagai alert terpisah |
| Knowledge retrieval | Structured fact query dengan product, topic, dan slot filters |
| Seller script | Gemini API menyusun respons dari action dan fakta terpilih |
| Validation | Grounding fact ID/angka serta konsistensi action, warna, size, dan stok |
| Safe fallback | Template berbasis Knowledge Base dengan provenance yang eksplisit |
| Multi-key Gemini | Rotasi otomatis untuk jumlah API key yang dinamis |
| Full-stack demo | React, FastAPI, IndoBERT service, Nginx, dan Docker Compose |

## Arsitektur

```text
Comment
  → Preprocessing
  → Spam / duplicate filter
  → IndoBERT intent classification
  → Taxonomy Adapter + Slot Extractor
  ├─ Trend Lane
  │    → Rolling Window 60s
  │    → Action Engine
  │    → Structured Fact Retrieval
  │    → Gemini Generator
  │    → Validator
  │    → Coach Card
  └─ Priority Lane
       → Purchase Intent Alert
```

### Service Docker

| Service | Teknologi | Port host | Tanggung jawab |
|---|---|---:|---|
| `frontend` | React + TypeScript + Vite, disajikan Nginx | `3000` | Replay UI, audience snapshot, Priority Alert, dan Coach Card |
| `backend` | FastAPI + Uvicorn | `8000` | Session, orchestration, Action Engine, retrieval, Gemini, dan validator |
| `nlp` | IndoBERT + FastAPI | `8010` | Intent inference |

Nginx meneruskan request `/api/*` dan `/health` dari frontend ke backend. Backend mengakses NLP melalui network internal Compose pada `http://nlp:8010`.

## Cara sistem mengambil keputusan

### Mapping post-NLP

| Raw intent | Normalized signal | Audience state | Action |
|---|---|---|---|
| `size_inquiry` | `SIZE_AVAILABILITY` | `SIZE_INFORMATION_GAP` | `SHOW_SIZE_OPTIONS` |
| `size_recommendation` | `SIZE_RECOMMENDATION` | `SIZE_FRICTION` | `SHOW_SIZE_GUIDE` |
| `color_inquiry` | `COLOR_AVAILABILITY` | `COLOR_INFORMATION_GAP` | `SHOW_COLOR_OPTIONS` |
| `stock_availability` | `STOCK_AVAILABILITY` | `STOCK_FRICTION` | `CONFIRM_STOCK` |
| `price_inquiry` | `PRICE_PROMO` | `PRICE_FRICTION` | `EXPLAIN_PRICE_PROMO` |
| `product_inquiry` | `PRODUCT_DETAIL` | `PRODUCT_INFO_GAP` | `EXPLAIN_PRODUCT_DETAIL` |
| `purchase_intent` | `PURCHASE_INTENT` | Priority Lane | Priority Alert |
| `not_relevant` / `other` | `IRRELEVANT` | Tidak masuk Trend Lane | `NO_ACTION` |

### Ranking dan stabilitas

Action Engine hanya memilih state yang memenuhi seluruh threshold berikut:

- minimal dua komentar pendukung dalam 60 detik;
- minimal dua pengguna unik;
- confidence agregat minimal `0.70`.

Jika beberapa signal eligible, ranking dilakukan dengan urutan:

1. `unique_user_count` terbesar;
2. `support_count` terbesar;
3. `state_confidence` terbesar;
4. business `priority_rank` sebagai tie-break terakhir.

Ranking tidak dilakukan ulang di frontend. Hysteresis mempertahankan signal aktif selama masih eligible; challenger harus memiliki sedikitnya dua pengguna unik lebih banyak untuk menggantikannya.

### Structured fact retrieval

Action Engine menghasilkan query seperti berikut:

```json
{
  "product_id": "TSHIRT-01",
  "fact_type": "SIZE_GUIDE",
  "topic": "size_recommendation",
  "filters": {
    "body_weight": 55,
    "body_height": 160
  }
}
```

Retrieval bersifat konservatif dan mengirim maksimal lima fakta kepada Gemini. Slot dari pengguna berbeda tidak digabung menjadi satu profil. Jika fakta yang cukup tidak tersedia, sistem memilih respons aman tanpa membuat klaim baru.

### Gemini, validator, dan fallback

Gemini bertugas menyusun bahasa, bukan menentukan action. Input Gemini berisi selected action, selected signal, evidence comments, representative slots, fact query, dan fakta produk terpilih.

Output kemudian diperiksa oleh Validator. Pemeriksaan meliputi:

- schema JSON;
- fact ID dan claim grounding;
- angka harga, ukuran, berat, tinggi, dan satuan;
- batas panjang respons;
- keselarasan dengan selected action;
- konsistensi requested color dan requested size;
- konsistensi stok ready atau habis.

Jika Gemini tidak tersedia atau output tetap gagal setelah satu retry, sistem menggunakan template aman. UI membedakan provenance secara eksplisit:

| Kondisi | Provider | Pipeline status | `fallback_used` |
|---|---|---|---|
| Gemini berhasil dan valid | `GEMINI` | `CARD_READY` | `false` |
| Template atau validator fallback | `TEMPLATE` | `FALLBACK` | `true` |

## Prasyarat

### Docker workflow yang direkomendasikan

| Kebutuhan | Rekomendasi |
|---|---|
| Docker Engine / Docker Desktop | Docker 24+ dengan Compose v2 |
| RAM | 8 GB atau lebih |
| Disk kosong | Minimal 5 GB; 10 GB disarankan |
| Internet | Diperlukan saat build pertama dan untuk Gemini API |
| GPU | Tidak diperlukan |

### Windows

- Windows 10 dengan WSL 2 atau Windows 11;
- Docker Desktop menggunakan WSL 2 engine;
- Git untuk Windows;
- Git Bash jika ingin menjalankan smoke test shell.

Clone project di filesystem Windows seperti `E:\Programs\livecoachhub` diperbolehkan dan sudah digunakan untuk validasi Docker Desktop.

## Quick start dengan Docker

### 1. Clone

```powershell
git clone https://github.com/HafizhHabiibi/livecoachhub.git
Set-Location livecoachhub
```

### 2. Build dan jalankan

```powershell
docker compose up --build -d
```

Build pertama mengunduh model IndoBERT dari Hugging Face. Tunggu sampai NLP dan backend sehat:

```powershell
docker compose ps
```

Target:

```text
backend   Up ... (healthy)
nlp       Up ... (healthy)
frontend  Up ...
```

Status `health: starting` selama startup awal adalah normal. Pantau bila dibutuhkan:

```powershell
docker compose logs -f nlp backend
```

### 3. Buka aplikasi

| Komponen | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend health | http://localhost:8000/health |
| Backend API | http://localhost:8000 |
| NLP health | http://localhost:8010/health |

> [!IMPORTANT]
> **File demo yang harus diunggah ke frontend:**
> `data/replay/comments-demo.jsonl`
>
> Pada Windows, pilih file dari folder hasil clone:
> `livecoachhub\data\replay\comments-demo.jsonl`
>
> Buka http://localhost:3000, klik area upload, pilih file tersebut, lalu tekan **Start**.

### 4. Hentikan service

```powershell
docker compose down
```

Jangan gunakan `docker compose down -v` kecuali memang ingin menghapus cache model dan mengunduhnya kembali pada build berikutnya.

## Menjalankan demo

Repository menyediakan satu replay utama:

```text
data/replay/comments-demo.jsonl
```

Dataset berisi 30 komentar dengan identitas pengguna dan timestamp berurutan. Format setiap baris:

```json
{"comment_id":"CMT-001","user_id":"USR-001","timestamp_ms":0,"text":"halo kak, lagi live ya"}
```

Langkah demo:

1. buka http://localhost:3000;
2. upload `data/replay/comments-demo.jsonl`;
3. tekan **Start**;
4. amati klasifikasi komentar dan Audience Snapshot;
5. buka **Detail keputusan** untuk melihat raw intent, normalized signal, slots, dominant signal, jumlah pengguna unik, dan fact query;
6. perhatikan Priority Alert ketika purchase intent terdeteksi;
7. periksa label provenance pada Coach Card.

Kontrol replay mendukung Start, Pause, Resume, dan Reset. File JSONL buatan sendiri harus memiliki `comment_id` unik, `user_id` tidak kosong, timestamp yang tidak menurun, dan teks komentar.

## Health check dan smoke test

### Health lifecycle

Sebelum generation Gemini pertama, kondisi berikut masih valid:

```json
{
  "status": "DEGRADED",
  "services": {
    "api": "READY",
    "nlp_model": "READY",
    "llm_model": "UNKNOWN"
  }
}
```

Endpoint health sengaja tidak memanggil Gemini agar tidak menghabiskan quota. Setelah Coach Card Gemini berhasil dibuat, targetnya:

```json
{
  "schema_version": "health.v1",
  "status": "READY",
  "services": {
    "api": "READY",
    "nlp_model": "READY",
    "llm_model": "READY"
  },
  "provider": {
    "nlp": "IndoBERT",
    "llm": "Gemini API"
  }
}
```

Periksa melalui PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Depth 5
```

### Smoke test otomatis

Jalankan dari Git Bash setelah container sehat:

```bash
bash scripts/smoke_test.sh
```

Default smoke test mewajibkan Gemini. Untuk menguji graceful fallback secara sengaja:

```bash
REQUIRE_FULL_AI=0 bash scripts/smoke_test.sh
```

Smoke test memeriksa health, demo config, session, dua pengguna unik, action selection, idempotency, Coach Card, provenance, reset, dan frontend.

### Pemeriksaan log

```powershell
docker compose logs --tail=300 backend |
    Select-String -Pattern "ERROR|Traceback|500|429|quota|fallback|Gemini"
```

Generation normal memiliki pola:

```text
HTTP Request: POST ...generateContent "HTTP/1.1 200 OK"
Gemini generation berhasil dengan key 1/N
LLM async selesai ... status=CARD_READY
```

## Konfigurasi Gemini

### Konfigurasi kompetisi

Checkout kompetisi menyertakan `backend/.env.enc`. Saat backend container mulai, `backend/entrypoint.sh` mendekripsinya menjadi `/app/.env`. Karena itu juri cukup menjalankan:

```powershell
docker compose up --build -d
```

Key tersebut merupakan accepted temporary risk untuk kemudahan penjurian dan harus direvoke setelah kompetisi.

### Menggunakan konfigurasi sendiri

Salin template di root project:

```powershell
Copy-Item .env.example .env
```

Isi minimal:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEYS=key_pertama,key_kedua,key_ketiga
GEMINI_MODEL=nama_model_gemini
NLP_SERVICE_URL=http://localhost:8010
```

Jumlah key dinamis. Penambahan menjadi lima atau enam key cukup dilakukan pada `GEMINI_API_KEYS`; kode tidak perlu diubah.

Untuk Docker, generate ulang file terenkripsi dari Git Bash:

```bash
openssl enc -aes-256-cbc -salt -pbkdf2 \
  -in .env \
  -out backend/.env.enc \
  -pass pass:livecoachhub2026
```

Kemudian rebuild backend:

```powershell
docker compose build --no-cache backend
docker compose up -d
```

Jangan memasukkan `.env` plaintext ke Git. Log aplikasi hanya menampilkan nomor slot key, bukan isi key.

## Development lokal tanpa Docker

Docker Compose adalah jalur utama. Setup lokal memerlukan tiga terminal dan Python 3.11.

### 1. Environment

```bash
cp .env.example .env
```

Isi `GEMINI_API_KEYS` dan model yang ingin digunakan.

### 2. NLP service

```bash
python -m venv .venv-nlp
source .venv-nlp/bin/activate
pip install -r AI/NLP/fine-tuned-indobert/requirements-inference.txt
python scripts/download_models.py --nlp
cd AI/NLP/fine-tuned-indobert
python serve.py --host 0.0.0.0 --port 8010
```

Pada PowerShell, aktivasi virtual environment menggunakan:

```powershell
.\.venv-nlp\Scripts\Activate.ps1
```

### 3. Backend

```bash
python -m venv .venv-backend
source .venv-backend/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite meneruskan `/api` dan `/health` ke backend pada port `8000`.

## API

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/health` | Health API, NLP, dan status Gemini yang sudah diverifikasi |
| `GET` | `/api/v1/demo-config` | Product, replay, dan model metadata |
| `POST` | `/api/v1/session/start` | Membuat replay session |
| `POST` | `/api/v1/comments/analyze` | Menjalankan pipeline untuk satu komentar |
| `GET` | `/api/v1/session/card?session_id=...` | Polling hasil generation async |
| `POST` | `/api/v1/session/reset` | Membersihkan state session |

Request analyze minimum:

```json
{
  "session_id": "LIVE-XXXXXXXX",
  "comment_id": "CMT-001",
  "user_id": "USR-001",
  "timestamp_ms": 1000,
  "text": "bb 55 tb 160 cocok size apa kak?"
}
```

`user_id` wajib dan harus konsisten untuk pengguna yang sama. `comment_id` bersifat idempotency key per session.

## Struktur repository

```text
livecoachhub/
├── AI/
│   ├── NLP/fine-tuned-indobert/          # IndoBERT inference service
│   └── LLM/grounded_llm/
│       ├── Action Engine/                # rules, ranking, hysteresis
│       ├── Knowledge Base/               # product facts + structured retrieval
│       └── Validator/                    # grounding and consistency checks
├── backend/
│   ├── app/main.py                       # FastAPI endpoints
│   ├── orchestrator.py                   # end-to-end pipeline
│   ├── taxonomy_adapter/                 # raw intent → semantic signal
│   ├── slot_extractor/                   # deterministic slot extraction
│   ├── rolling_window/                   # 60-second aggregation
│   ├── priority_detector/                # Priority Lane
│   ├── action_engine/                    # integration bridge
│   ├── knowledge/                        # retrieval bridge
│   ├── validator/                        # validator bridge
│   └── .env.enc                          # encrypted competition configuration
├── frontend/
│   ├── src/components/                   # dashboard and Priority Alert
│   ├── src/contracts/                    # TypeScript + Zod contracts
│   └── nginx.conf                        # SPA and API proxy
├── data/
│   ├── replay/comments-demo.jsonl        # replay utama
│   └── product_facts/                    # synchronized KB copy
├── scripts/
│   ├── download_models.py
│   └── smoke_test.sh
├── tests/test_core_regressions.py
├── docker-compose.yml
└── README.md
```

## Pengujian

### Backend dan invariant pipeline

```bash
python3 -m unittest -v tests/test_core_regressions.py
python3 -m compileall -q backend AI/LLM/grounded_llm
```

Regression suite melindungi provenance, key rotation, generation deduplication, unique-user threshold, signal mapping, slot isolation, ranking, hysteresis, structured retrieval, stock validation, frontend contracts, dan replay contract.

### Frontend

```bash
npm run type-check --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

Project menggunakan TypeScript `5.5.4`, sesuai rentang toolchain ESLint yang digunakan.

## Troubleshooting

### Container masih `health: starting`

IndoBERT membutuhkan waktu untuk memuat model. Tunggu dan periksa:

```powershell
docker compose ps
docker compose logs --tail=200 nlp backend
```

### Health `DEGRADED` dan LLM `UNKNOWN`

Normal sebelum generation Gemini pertama. Jalankan replay sampai Coach Card terbentuk, lalu periksa `/health` kembali.

### Health tetap `DEGRADED` setelah generation

```powershell
docker compose logs --tail=300 backend |
    Select-String -Pattern "Gemini|429|quota|401|403|fallback|ERROR"
```

- `429` atau `quota`: seluruh key yang tersedia dapat sedang terkena limit;
- `401/403`: key atau permission tidak valid;
- provider `TEMPLATE`: sistem berada pada safe fallback mode.

### Port sudah dipakai

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Periksa juga port `3000` dan `8010`.

### Model download lambat atau gagal

Pastikan internet tersedia, lalu rebuild NLP:

```powershell
docker compose build --no-cache nlp
docker compose up -d nlp
docker compose logs -f nlp
```

### Masalah line ending Windows

Entrypoint Docker menormalisasi CRLF secara otomatis. Jika file shell lain bermasalah, clone ulang dengan:

```powershell
git config --global core.autocrlf input
```

### Reset seluruh stack

```powershell
docker compose down
docker compose up --build -d
```

Tambahkan `-v` hanya jika cache model memang ingin dihapus.

## Batasan MVP

- input masih berupa replay JSONL, belum live connector TikTok atau platform commerce;
- Knowledge Base masih single-product mock catalog untuk `TSHIRT-01`;
- session disimpan in-memory dan ditujukan untuk satu backend worker;
- belum ada authentication, rate limiting, Redis, atau persistent database;
- shipping dan objection belum memiliki signal khusus karena label NLP saat ini belum membedakannya secara andal;
- Gemini membutuhkan internet dan quota API;
- task Gemini yang sudah berjalan tidak dapat dihentikan paksa oleh thread executor; stale result tidak dipakai, tetapi request dapat tetap menghabiskan quota;
- secret kompetisi harus direvoke setelah penjurian selesai.

## Status validasi terakhir

Validasi Windows + Docker Desktop telah menghasilkan:

```text
System health: READY
API: READY
IndoBERT: READY
Gemini API: READY
Coach Card: CARD_READY
```

Seluruh request analyze, polling, health, dan reset pada pengujian tersebut mengembalikan HTTP `200` tanpa traceback atau internal server error.
