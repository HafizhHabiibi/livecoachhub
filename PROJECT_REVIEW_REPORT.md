# Laporan Analisis dan Review Project LiveCoachHub

**Tanggal review:** 24 Agustus 2026  
**Branch:** `main`  
**Jenis review:** static code review, architecture review, configuration review, security review, pemeriksaan build lokal, serta konfirmasi runtime dari maintainer  
**Status akhir:** **BELUM READY secara fungsional; distribusi secret merupakan accepted temporary risk untuk kebutuhan penjurian**

> **Update implementasi 24 Agustus 2026:** COR-01, COR-02, QA-01, unique-user threshold, evidence text, dan idempotency minimum telah diperbaiki. Dua belas regression test lulus, termasuk regresi endpoint polling Coach Card. Lihat [`IMPLEMENTATION_REPORT.md`](IMPLEMENTATION_REPORT.md). Status terbaru: **ready for full Docker E2E re-validation** pada Windows + Docker Desktop.

## 1. Ringkasan Eksekutif

LiveCoachHub memiliki fondasi MVP yang cukup baik: batas komponen jelas, kontrak frontend divalidasi dengan Zod, backend memakai model Pydantic, pipeline AI dipisahkan menjadi modul kecil, dan frontend production build berhasil. Arsitektur fallback juga membuat demo tetap berjalan ketika service AI gagal.

Namun, ada tiga masalah fungsional utama dan satu risiko keamanan yang perlu dicatat:

1. **Accepted temporary risk: secret Gemini dapat dipulihkan dari repository.** Tim sengaja memilih mekanisme ini agar juri cukup menjalankan `docker compose up --build`, dan berencana mencabut key setelah kompetisi. Secara teknis ciphertext dan password yang tersedia bersama tetap setara dengan secret terbuka; karena itu keputusan ini harus diperlakukan sebagai exception bertanggal, bukan kontrol keamanan.
2. **`user_id` hilang di frontend.** File demo berisi 30 komentar dari 19 user, tetapi schema, type, dan request frontend membuang/tidak meneruskan `user_id`. Backend lalu membuat user palsu dari `comment_id`, sehingga duplicate filtering dan unique-user analytics tidak valid.
3. **Fallback LLM dapat dilabel sebagai output AI yang lolos.** Client mengubah kegagalan Gemini menjadi JSON template valid. Validator dapat memberi status `PASSED`, lalu orchestrator menandai `CARD_READY` dan `fallback_used=false`. Ini merusak provenance yang menjadi klaim utama project.
4. **Smoke test formal tidak berjalan penuh.** Interaksi `set -e` dengan increment counter membuat script berhenti pada check pertama.

Kesimpulan praktis: project **layak sebagai prototype/demo kompetisi** dan Compose telah berhasil dijalankan maintainer pada fresh clone Windows dengan Docker Desktop. Masalah utama yang tersisa bukan startup Compose, melainkan correctness identitas user, provenance/fallback LLM, dan QA otomatis.

## 2. Skor Kondisi Project

| Area | Skor | Penilaian |
|---|---:|---|
| Arsitektur dan modularitas | 7/10 | Pipeline dan pembagian frontend/backend/NLP jelas |
| Correctness fitur inti | 4/10 | Alur ada, tetapi identitas user dan provenance salah |
| Kualitas kode | 6/10 | Cukup rapi dan typed, tetapi state/concurrency serta error handling rapuh |
| Testing dan QA | 2/10 | Tidak ada unit/integration test; smoke test rusak |
| Security | 4/10 | Secret recoverable diterima sementara untuk demo; endpoint dan input masih minim hardening |
| Deployment/reproducibility | 7/10 | Compose valid dan dilaporkan berhasil pada fresh clone Windows + Docker Desktop; belum direproduksi independen dalam sesi audit |
| Dokumentasi | 5/10 | README lengkap, tetapi beberapa klaim tidak sesuai implementasi |
| **Overall** | **5.0/10** | **Stack dapat dijalankan; risiko terbesar berada pada correctness dan provenance** |

## 3. Arsitektur Aktual

Alur utama yang benar-benar terlihat dari kode:

```text
React/Vite replay UI
  -> FastAPI backend
     -> normalize + duplicate/spam filter
     -> HTTP ke IndoBERT service atau heuristic fallback
     -> taxonomy adapter + rolling window
     -> deterministic action engine
     -> knowledge-base retrieval
     -> background Gemini call atau template fallback
     -> rule-based validator
  <- polling Coach Card
```

Komponen utama:

- `frontend/`: React 18, TypeScript, Vite, Zod, Nginx production image.
- `backend/`: FastAPI, session in-memory, orchestrator, AI clients, bridges ke Action Engine/Knowledge Base/Validator.
- `AI/NLP/fine-tuned-indobert/`: service inference IndoBERT berbasis Transformers/PyTorch.
- `AI/LLM/grounded_llm/`: action rules, static knowledge base, dan validator deterministik.
- `docker-compose.yml`: frontend, backend, NLP service, serta Hugging Face cache volume.

## 4. Hal yang Sudah Baik

- Pemisahan responsibility pipeline cukup jelas; normalizer, spam filter, taxonomy, window, action engine, retrieval, LLM client, dan validator tidak dicampur dalam satu file.
- Response utama divalidasi runtime di frontend menggunakan Zod dan dibatasi oleh model Pydantic di backend.
- Frontend mengirim komentar secara sequential dan memiliki guard untuk late response setelah reset.
- Action selection bersifat deterministik dan rule disimpan sebagai JSON, sehingga keputusan lebih mudah diaudit.
- Knowledge base hanya mengirim fact type yang diminta action engine.
- Dockerfile frontend memakai multi-stage build; Compose config lolos validasi sintaks.
- Type-check, frontend production build, ESLint, Python bytecode compilation, dan npm audit offline berhasil.
- Dataset demo konsisten secara file: 30 row, 19 `user_id`, tidak ada `user_id` kosong, timestamp terurut.

## 5. Temuan Prioritas

### P0 — Blocker dan Accepted Temporary Risk

#### SEC-01 — Accepted temporary risk: secret recoverable di Git

**Bukti:** `backend/.env.enc` di-track Git. `backend/entrypoint.sh:13` menyimpan password `livecoachhub2026`, lalu baris 18 memakai password tersebut untuk mendekripsi file.

**Keputusan tim:** mekanisme ini disengaja agar juri dapat menjalankan stack dengan satu command tanpa registrasi atau konfigurasi API key. Key direncanakan untuk di-revoke setelah kompetisi.

**Dampak tersisa:** siapa pun yang dapat membaca repository dapat memulihkan dan memakai key selama key masih aktif. Build image juga menyalin file tersebut ke image backend. Enkripsi hanya menyamarkan isi, bukan membatasi akses.

**Mitigasi wajib untuk accepted risk:** batasi key khusus demo dengan quota serendah mungkin; batasi API/service yang dapat diakses key; aktifkan monitoring quota; tetapkan waktu revoke yang eksplisit segera setelah batas penjurian; jangan gunakan key tersebut di sistem lain; siapkan kill switch jika terjadi penyalahgunaan. Setelah kompetisi, revoke key dan hapus mekanisme ini dari branch publik. Pembersihan Git history bersifat opsional setelah key dipastikan mati, tetapi tetap disarankan untuk mencegah pola tersebut ditiru.

#### COR-01 — `user_id` dari JSONL dibuang frontend

**Bukti:** README mendokumentasikan `user_id`, dan file demo memang memilikinya. Namun `CommentEntry` hanya berisi `comment_id`, `timestamp_ms`, dan `text` (`frontend/src/contracts/livecoach.ts:96-100`); Zod schema juga tidak mendefinisikan `user_id` (`livecoachSchemas.ts:196-203`), sehingga field tersebut di-strip. Request analyze di `useReplayController.ts:292-297` tidak mengirim `user_id`. Backend menggantinya dengan `USR-{comment_id}` (`backend/orchestrator.py:299-301`).

**Dampak:** setiap komentar terlihat berasal dari user unik. Duplicate filter tidak bekerja sesuai tujuan, unique-user count salah, dan metrik audiens mudah didominasi satu akun.

**Rekomendasi:** jadikan `user_id` field wajib pada type dan Zod schema, teruskan dalam `CommentAnalyzeRequest`, tambah ke backend replay helper, dan buat contract/integration test yang memverifikasi user yang sama tetap sama di rolling window.

#### COR-02 — Provenance fallback LLM dapat salah dilabel sebagai Gemini

**Bukti:** ketika key tidak ada atau Gemini gagal, `llm_client.generate()` mengembalikan template fallback sebagai JSON valid (`backend/llm_client.py:121-124` dan `166-169`). Template sengaja dibuat agar lolos validator (`172-176`). Orchestrator menentukan fallback hanya dari hasil validator, bukan dari provider aktual. Akibatnya template yang valid dapat menjadi `CARD_READY`, `validation_status=PASSED`, dan `fallback_used=false`.

**Konfirmasi runtime maintainer:** full Compose berhasil dijalankan dari clone project terpisah pada Windows menggunakan Docker Desktop, tetapi terdapat anomali pada bagian LLM/fallback. Gejala ini konsisten dengan jalur kode di atas dan memperkuat bahwa masalah berada pada pelabelan/provenance generation, bukan pada build Compose.

**Dampak:** UI dan demo dapat mengklaim respons berasal dari AI meskipun sebenarnya template. Ini bertentangan langsung dengan klaim provenance dan acceptance criteria audit lama.

**Rekomendasi:** return result terstruktur dari LLM client, misalnya `{raw, provider, fallback_used, error_code}`; pisahkan `generation_provider` dari `validation_status`; selalu set pipeline `FALLBACK` ketika template digunakan, walaupun template valid.

#### QA-01 — Smoke test selalu berhenti pada check pertama

**Bukti:** script memakai `set -e` dan counter `((PASS++))`/`((FAIL++))` (`scripts/smoke_test.sh:13-25`). Pada nilai awal 0, arithmetic command menghasilkan exit status 1, sehingga Bash langsung keluar. Eksekusi terhadap port offline hanya menampilkan pemeriksaan pertama.

**Dampak:** klaim “smoke test otomatis” di README tidak benar; sebagian besar checks tidak pernah berjalan.

**Rekomendasi:** gunakan `PASS=$((PASS + 1))` dan `FAIL=$((FAIL + 1))`, lalu tambah test untuk script itu sendiri. Smoke test juga harus memverifikasi status service benar-benar `READY`, provider aktual, polling card sampai selesai, dan `fallback_used` yang benar.

### P1 — High Priority

#### COR-03 — Unique-user count dihitung tetapi diabaikan Action Engine

`rolling_window/window.py:93-123` menghitung `unique_user_count`, tetapi bridge hanya meneruskan intent, support count, confidence, dan evidence (`backend/action_engine/bridge.py:60-69`). Threshold action tetap memakai jumlah komentar mentah.

**Dampak:** setelah `user_id` diperbaiki pun, satu user dengan teks berbeda masih dapat menciptakan tren palsu.

**Rekomendasi:** masukkan minimum unique-user count ke kontrak dan action rules, atau jadikan support berbobot per user.

#### COR-04 — “Evidence comments” untuk LLM sebenarnya hanya comment ID

`backend/orchestrator.py:437-446` secara eksplisit mengembalikan ID sebagai placeholder. LLM tidak menerima teks komentar, padahal dokumentasi menyatakan evidence comments dikirim sebagai konteks.

**Dampak:** respons kurang kontekstual dan klaim grounded-on-audience tidak terpenuhi.

**Rekomendasi:** simpan cleaned/original text bersama window entry atau comment store per session, lalu kirim maksimal tiga teks evidence yang sesuai.

#### REL-01 — Health LLM hanya mengecek keberadaan key

`is_llm_available()` mengembalikan true jika list key tidak kosong (`backend/llm_client.py:78-82`), bukan jika Gemini dapat dihubungi atau key valid. `/health` lalu dapat mengumumkan `READY` dan provider `Gemini API` (`backend/app/main.py:143-163`).

**Dampak:** revoked key, invalid key, quota exhausted, atau outage tetap terlihat READY sampai sebuah generation gagal.

**Rekomendasi:** bedakan `CONFIGURED`, `READY`, `DEGRADED`, dan `UNKNOWN`; simpan timestamp/error dari panggilan aktual terakhir; jangan lakukan call mahal pada setiap health check.

#### REL-02 — State session tidak bounded, tidak persisten, dan tidak thread-safe

`SessionManager` menyimpan semua session pada dictionary tanpa TTL/limit/delete (`backend/session.py:63-84`). FastAPI sync endpoints berjalan di thread pool, sementara session dan future diubah tanpa lock. Reset juga mengganti state tanpa membatalkan future lama.

**Dampak:** memory growth, race condition pada request paralel/polling/reset, orphan background work, dan kehilangan state saat restart atau multi-worker deployment.

**Rekomendasi:** untuk MVP minimal tambahkan lock per session, idempotency berdasarkan `comment_id`, TTL/cleanup, hard limit session, dan cancel pending task saat reset. Untuk produksi pindahkan state ke Redis/database.

#### REL-03 — Satu worker LLM global menjadi bottleneck lintas session

Orchestrator membuat `ThreadPoolExecutor(max_workers=1)` global. Semua session berbagi antrean tunggal. `Future.cancel()` juga tidak menghentikan task yang sudah berjalan.

**Dampak:** satu request Gemini yang lambat dapat menunda semua session; pergantian action dapat menghasilkan pekerjaan usang yang tetap menghabiskan quota.

**Rekomendasi:** gunakan async client dengan timeout/cancellation yang nyata, bounded queue, concurrency limit yang eksplisit, dan dedupe berdasarkan session/action generation id.

#### API-01 — Error contract tidak sesuai semantics

Semua `HTTPException`, termasuk 404 session, dipetakan ke `INTERNAL_ERROR` (`backend/app/main.py:97-110`), padahal contract menyediakan `SESSION_NOT_FOUND`. Error validasi FastAPI 422 juga tidak dibentuk ke `error.v1`. Detail exception pipeline dikirim ke client pada baris 265-267.

**Dampak:** frontend tidak dapat memberi recovery yang tepat; detail internal berpotensi bocor; response contract tidak konsisten.

**Rekomendasi:** mapping 404/422/429/503 ke enum contract, handler khusus `RequestValidationError`, dan simpan detail exception hanya di log server.

#### API-02 — Input NLP tidak dibatasi

`PredictRequest.texts` menerima list bebas dan `threshold` bebas (`serve.py:31-33`). Endpoint menerima list kosong yang berakhir pada `np.concatenate([])`, dan list sangat besar diproses seluruhnya. Port 8010 juga dipublish ke host dan CORS diizinkan untuk semua origin.

**Dampak:** error 500 untuk input kosong dan risiko resource exhaustion pada service model.

**Rekomendasi:** batasi 1-32 item/request, panjang teks, dan threshold 0-1; tolak list kosong dengan 422; jangan publish port NLP di deployment non-debug atau tambahkan auth/network isolation.

#### REP-01 — Dependency Python tidak reproducible

Sebagian besar dependency menggunakan lower bound saja (`>=`), termasuk `torch`, `transformers`, `google-genai`, dan FastAPI; `numpy` bahkan tanpa versi. Tidak ada lock/hash.

**Dampak:** fresh build pada waktu berbeda dapat menghasilkan kombinasi dependency berbeda atau incompatible. Frontend saat ini juga menginstal TypeScript 5.9.3 dari range `^5.2.2`, sementara ESLint parser memberi warning bahwa versi tersebut tidak didukung.

**Rekomendasi:** buat lock file Python dengan versi dan hash, pin base image dengan digest untuk release, dan selaraskan versi TypeScript dengan toolchain ESLint.

#### REP-02 — Downloader model tetap mengumumkan sukses setelah gagal

Exception download ditangkap tanpa `sys.exit(1)`, kemudian script selalu mencetak “Selesai! Model siap digunakan” (`scripts/download_models.py:77-84`). Ini adalah temuan audit lama C-10 yang belum selesai.

**Dampak:** CI/user menerima exit code sukses dan pesan palsu walau model tidak tersedia.

**Rekomendasi:** re-raise atau return non-zero pada failure; hanya cetak success setelah verifikasi lulus.

### P2 — Medium Priority

#### DOC-01 — Dokumentasi drift

- README menyebut “5 endpoints”, sedangkan backend memiliki enam endpoint karena tambahan card polling.
- README menyebut API key aman/siap di image, padahal mekanismenya merupakan blocker security.
- README menyatakan health “harus READY”, tetapi script hanya mengecek keberadaan field, bukan nilainya.
- `start.sh` hard-code PATH milik user lain (`/home/fauzi-k/...`), mengandalkan venv yang tidak disediakan, membunuh proses pada tiga port, dan tidak memiliki cleanup trap.
- `.env.example` masih mendokumentasikan QLoRA/`LLM_SERVICE_URL`, sementara config menyatakan Gemini-only.

**Rekomendasi:** tetapkan README root sebagai single source of truth, hapus jalur startup lokal yang tidak portable atau perbaiki total, dan tambahkan documentation verification pada release checklist.

#### COR-05 — Counter snapshot memiliki semantics campuran

`support_count` berasal dari rolling 60 detik, tetapi `high_readiness_count` dan `priority_count` terus bertambah sepanjang session dan juga menghitung event yang tidak masuk trend window. Nama `AudienceSnapshot` membuat ketiganya terlihat seolah berada pada window yang sama.

**Rekomendasi:** pilih semantics per-window atau beri nama eksplisit `session_*_count`; dokumentasikan dan test boundary 60 detik.

#### COR-06 — Event time tidak dilindungi backend

Rolling window memang memakai event time, tetapi API tidak menolak timestamp mundur. Pruning berdasarkan timestamp request saat ini dapat memberi hasil membingungkan untuk caller selain frontend resmi.

**Rekomendasi:** enforce timestamp non-decreasing per session atau definisikan kebijakan late event yang eksplisit.

#### QA-02 — Tidak ada automated unit/integration test

Repository hanya memiliki `scripts/smoke_test.sh`; tidak ditemukan test backend/frontend formal. Area paling berisiko—taxonomy mapping, duplicate filter, rolling-window boundary, action threshold, validator adversarial input, API contract, replay pause/reset, dan provenance fallback—tidak dilindungi regression test.

**Rekomendasi:** prioritaskan test pada kontrak dan invariant bisnis, bukan hanya snapshot UI.

#### SEC-02 — Public-facing hardening belum ada

Backend tidak memiliki auth, rate limit, request-size limit, trusted-host policy, atau security headers. Ini masih dapat diterima untuk demo localhost, tetapi tidak untuk deployment internet-facing.

**Rekomendasi:** nyatakan deployment scope secara eksplisit. Jika dipublikasi, tempatkan di belakang gateway, auth demo, TLS, rate limiting, body limit, dan logging tanpa sensitive payload.

## 6. Hasil Pemeriksaan

| Pemeriksaan | Hasil | Catatan |
|---|---|---|
| `python3 -m compileall` | PASS | Backend, grounded LLM, dan source NLP dapat dikompilasi menjadi bytecode |
| `npm run type-check` | PASS | TypeScript tanpa error |
| `npm run build` | PASS | Vite production build berhasil; bundle JS sekitar 250 kB, gzip sekitar 75 kB |
| `npm run lint` | PASS dengan warning | Parser ESLint tidak mendukung resmi TypeScript 5.9.3 yang ter-install |
| `npm audit --offline` | PASS terbatas | 0 vulnerability dari advisory cache lokal; bukan audit online terkini |
| `docker compose config -q` | PASS | Compose valid secara sintaks |
| `bash -n` | PASS | Script shell valid secara sintaks |
| `scripts/smoke_test.sh` | FAIL | Berhenti pada check pertama karena interaksi counter dengan `set -e` |
| Backend runtime lokal | NOT RUN | Dependency backend tidak ter-install pada interpreter aktif |
| Full Docker build/Compose | PASS (maintainer-reported) | Berhasil dari clone terpisah pada Windows + Docker Desktop; tidak direproduksi independen dalam sesi audit |
| Full-AI LLM behavior | FAIL/ANOMALOUS | Maintainer mengonfirmasi anomali fallback; penyebab kode paling mungkin adalah COR-02 |
| Python dependency vulnerability scan | NOT RUN | Tidak ada lock/environment runtime yang dapat diaudit secara representatif |

Catatan: keberhasilan Compose membuktikan stack dapat dibangun dan dijalankan pada environment yang diuji maintainer, tetapi belum membuktikan setiap Coach Card benar-benar berasal dari Gemini. Provenance per generation tetap harus diverifikasi.

## 7. Rencana Perbaikan yang Disarankan

### Fase 0 — Pengelolaan accepted risk secret

1. Gunakan key khusus kompetisi yang tidak dipakai di sistem lain.
2. Terapkan quota minimum, restriction yang tersedia, dan monitoring penggunaan.
3. Dokumentasikan owner serta tanggal/jam revoke segera setelah penjurian selesai.
4. Siapkan revoke lebih awal jika ada anomali quota.
5. Setelah kompetisi, revoke key, audit usage, lalu pindahkan setup normal ke environment/secret manager.

### Fase 1 — Correctness inti (1 hari)

1. Perbaiki kontrak `user_id` end-to-end.
2. Gunakan unique-user count pada Action Engine.
3. Simpan dan kirim evidence text aktual.
4. Pisahkan provider provenance dari validator result.
5. Tambah idempotency `comment_id` agar retry tidak menggandakan state.

### Fase 2 — QA dan reliability (1-2 hari)

1. Perbaiki smoke test.
2. Tambah unit test backend untuk filter/window/action/validator.
3. Tambah API contract integration test, termasuk 404 dan 422.
4. Tambah frontend test parser agar `user_id` tidak ter-strip.
5. Tambah TTL session, lock, dan cancellation/versioning untuk background generation.

### Fase 3 — Reproducibility (1 hari)

1. Lock dependency Python dan selaraskan toolchain frontend.
2. Perbaiki exit code downloader.
3. Dokumentasikan hasil fresh-clone Windows + Docker Desktop yang sudah berhasil sebagai release evidence.
4. Jalankan E2E dengan tiga mode: full AI, NLP fallback, dan LLM fallback.
5. Simpan output test sebagai release evidence.

### Fase 4 — Dokumentasi dan release gate

1. Sinkronkan README dengan enam endpoint dan setup secret yang aman.
2. Hapus/perbaiki `start.sh` dan referensi QLoRA lama.
3. Update `AUDIT.md` karena beberapa item yang ditandai selesai ternyata belum selesai secara fungsional.
4. Jangan memberi label READY sebelum seluruh acceptance criteria di bawah lulus.

## 8. Acceptance Criteria Sebelum Disebut READY

- Untuk release normal: tidak ada secret atau material dekripsi secret di current tree maupun Git history. Exception kompetisi hanya berlaku untuk key demo terbatas dengan owner, monitoring, quota, dan deadline revoke tertulis.
- Fresh clone dapat berjalan dengan secret milik pengguna melalui documented setup.
- `user_id` dari JSONL sampai ke spam filter dan rolling window tanpa berubah.
- Dua komentar berbeda dari user yang sama tidak dihitung sebagai dua unique user.
- Template fallback selalu tampil sebagai fallback, tidak pernah sebagai Gemini output.
- Health menunjukkan status aktual, bukan hanya keberadaan config.
- Evidence yang masuk prompt adalah comment text yang benar.
- Retry comment yang sama bersifat idempotent.
- Unit, contract, integration, frontend build/lint, Docker build, dan smoke test lulus.
- E2E full AI menghasilkan Coach Card dengan provider yang dapat dibuktikan.
- E2E degraded mode tetap aman dan provenance-nya jujur.

## 9. Keputusan Review

**CONDITIONAL GO untuk menjalankan demo Compose; NO-GO untuk mengklaim full-AI correctness sampai COR-01, COR-02, dan QA-01 selesai. SEC-01 dicatat sebagai accepted temporary risk, bukan blocker submission yang tidak disengaja.**

Project dapat menjadi **GO untuk penjurian terbatas** setelah COR-01, COR-02, dan QA-01 diperbaiki serta full Docker E2E lulus. Exception secret harus memiliki quota, monitoring, owner, dan deadline revoke. Untuk deployment publik setelah kompetisi, key wajib dicabut dan setup secret harus diganti.
