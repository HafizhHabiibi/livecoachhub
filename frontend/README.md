# 🎯 LiveCoach AI — Frontend

> AI Real-Time Coach untuk Penjual Live Commerce TikTok Shop & Shopee Live Indonesia

**AIC COMPFEST 18 · Smart Commerce · Babak Penyisihan**

---

## Tentang Project

90% penjual UMKM di TikTok Shop dan Shopee Live tidak memiliki kemampuan analitik real-time. Mereka tidak tahu kapan penonton sedang peak, kapan harus flash sale, atau bagaimana merespons komentar negatif.

**LiveCoach AI** membaca replay komentar live commerce, mengenali pola hambatan pembelian yang dominan, memilih satu tindakan terbaik, lalu menampilkan saran ucapan host yang sudah diperiksa terhadap fakta produk — secara real-time selama live berlangsung.

Repository ini berisi **frontend** aplikasi LiveCoach AI yang dibangun dengan React 18 + TypeScript.

---

## Tech Stack

| Teknologi | Versi | Keterangan |
|-----------|-------|------------|
| React | 18.3 | UI framework |
| TypeScript | 5.2 | Strict mode aktif |
| Vite | 5.3 | Build tool + dev server |
| React Router | v6 | Routing — hanya `/demo` |
| Zod | 3.23 | Runtime API response validation |
| CSS Variables | — | Design tokens, tanpa UI library |

---

## Struktur Folder

```
src/
├── main.tsx                          # Entry point React
├── vite-env.d.ts                     # Type untuk import.meta.env
│
├── app/
│   └── App.tsx                       # Root component + routing
│
├── styles/
│   └── tokens.css                    # Design tokens (warna, spacing, radius, animasi)
│
├── pages/
│   └── DemoPage.tsx                  # Halaman /demo — satu-satunya route
│
├── contracts/
│   ├── livecoach.ts                  # Semua TypeScript types dan enums
│   └── livecoachSchemas.ts           # Zod schemas untuk validasi runtime API
│
├── mocks/
│   ├── fixtures.ts                   # Mock data 3 skenario (WAITING/CARD_READY/FALLBACK)
│   └── comments-demo.jsonl           # File replay contoh untuk demo
│
├── services/
│   └── livecoachApi.ts               # Semua 5 endpoint API + mock mode support
│
├── features/replay/
│   ├── useReplayController.ts        # Hook utama — sequential replay, pause/resume
│   ├── replayState.ts                # State machine, label helpers, format helpers
│   └── jsonlParser.ts                # Parser + validator file .jsonl
│
└── components/
    ├── AppHeader.tsx                  # Header + health status dot + elapsed clock
    ├── ReplayInputPanel.tsx           # Upload file .jsonl + progress bar + tombol kontrol
    ├── CommentStream.tsx              # 5 komentar terbaru + intent chips dari backend
    ├── AudienceSnapshot.tsx           # Agregat audiens 60 detik
    ├── CoachCard.tsx                  # Output utama AI — 3 state tampilan ⭐
    ├── DecisionDetails.tsx            # Detail teknis pipeline (collapsible)
    └── StatusBanner.tsx               # Error dan warning banner
```

---

## Prasyarat

- [Node.js](https://nodejs.org) v20 ke atas
- npm v9 ke atas (sudah include bersama Node.js)

Cek versi:
```bash
node --version
npm --version
```

---

## Cara Menjalankan

### Langkah 1 — Clone dan masuk ke folder frontend

```bash
git clone https://github.com/<username>/livecoach-ai.git
cd livecoach-ai/frontend
```

### Langkah 2 — Install dependencies

```bash
npm install
```

### Langkah 3 — Setup environment

```bash
cp .env.example .env
```

Isi file `.env`:

```env
# Aktifkan mock mode — tidak perlu backend untuk jalankan frontend
VITE_USE_MOCK=true
VITE_API_BASE_URL=http://localhost:8000
```

### Langkah 4 — Jalankan dev server

```bash
npm run dev
```

Buka browser: **http://localhost:3000**

Aplikasi akan redirect otomatis ke `/demo`.

---

## Cara Demo

Setelah aplikasi terbuka di browser:

1. **Upload file replay** — klik area upload atau drag & drop file `src/mocks/comments-demo.jsonl`
2. **Tekan Mulai Replay** — tombol aktif setelah file valid ter-upload
3. **Lihat AI bekerja** — komentar mengalir di kolom tengah, coaching card muncul di kolom kanan
4. **Coba Jeda / Lanjutkan / Reset** — tombol kontrol di panel kiri

> Saat `VITE_USE_MOCK=true`, data yang ditampilkan berasal dari `src/mocks/fixtures.ts` — bukan dari model AI sungguhan. Ini by design untuk development frontend tanpa bergantung pada backend.

---

## Format File Replay (.jsonl)

File replay adalah file teks dengan format JSONL — satu komentar per baris:

```jsonl
{"comment_id":"CMT-001","timestamp_ms":0,"text":"halo kak"}
{"comment_id":"CMT-002","timestamp_ms":5000,"text":"bahannya apa?"}
{"comment_id":"CMT-003","timestamp_ms":12000,"text":"bb 55 ambil m atau l?"}
```

Aturan validasi:
- `comment_id` harus unik dalam satu file
- `timestamp_ms` harus integer `>= 0` dan urut dari kecil ke besar
- `text` tidak boleh kosong
- File harus berekstensi `.jsonl`

File contoh tersedia di `src/mocks/comments-demo.jsonl`.

---

## Menyambungkan ke Backend

Setelah backend API siap, cukup ubah **satu baris** di file `.env`:

```env
# Sebelum (mock mode)
VITE_USE_MOCK=true

# Sesudah (sambung ke backend)
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:8000
```

Kemudian restart dev server:

```bash
npm run dev
```

Tidak ada perubahan kode frontend yang diperlukan. Semua API call di `src/services/livecoachApi.ts` sudah siap mengarah ke backend.

### Endpoint yang dibutuhkan dari backend

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| `GET` | `/health` | Status sistem dan model |
| `GET` | `/api/v1/demo-config` | Konfigurasi produk dan model |
| `POST` | `/api/v1/session/start` | Mulai sesi baru |
| `POST` | `/api/v1/comments/analyze` | Analisis satu komentar — inti pipeline |
| `POST` | `/api/v1/session/reset` | Reset sesi |

Kontrak lengkap setiap endpoint (schema request dan response) ada di `src/contracts/livecoach.ts` dan `src/contracts/livecoachSchemas.ts`.

---

## Scripts

```bash
# Jalankan development server
npm run dev

# Build untuk production
npm run build

# Preview hasil build
npm run preview

# Type check tanpa build
npm run type-check

# Lint
npm run lint
```

---

## Catatan Penting

- **Frontend tidak menghitung apapun** — semua intent, audience state, dan coach card harus datang 100% dari backend
- **Sequential request** — komentar berikutnya baru dikirim setelah response komentar sebelumnya diterima
- **Jangan push file `.env`** — hanya `.env.example` yang boleh ada di repository
- **Tidak ada nama institusi** di kode maupun commit message sesuai rulebook AIC

---

*LiveCoach AI · Frontend · AIC COMPFEST 18 · Deadline: 25 Agustus 2026*