# Report Implementasi Prioritas LiveCoachHub

**Tanggal:** 24 Agustus 2026  
**Scope:** provenance/fallback LLM, user identity, post-NLP semantic signals, slot extraction, ranking/hysteresis, structured retrieval, Priority Lane, frontend reliability, smoke test, dan regression test
**Status:** **IMPLEMENTED — menunggu re-validasi full Docker E2E pada Windows + Docker Desktop**

## 1. Ringkasan Hasil

Paket prioritas kompetisi telah diimplementasikan. Perubahan utama:

1. Template fallback tidak lagi dapat dilabel sebagai output Gemini.
2. `user_id` sekarang wajib dan diteruskan dari JSONL sampai backend.
3. Action Engine membutuhkan sedikitnya dua user unik untuk membentuk tren.
4. LLM menerima teks evidence aktual, bukan hanya `comment_id`.
5. Retry `comment_id` yang sama tidak lagi menggandakan state.
6. Polling mempertahankan status `FALLBACK`; status tidak berubah menjadi `CARD_READY` pada polling berikutnya.
7. Smoke test tidak lagi berhenti pada check pertama dan sekarang memeriksa provenance.
8. Health frontend sekarang pulih setelah Gemini terverifikasi dan provenance card tampil eksplisit.
9. Polling, retry, dan validasi file replay diperketat.
10. Empat puluh regression test berjalan dan seluruhnya lulus.
11. Intent size/color/stock tidak lagi digabung menjadi sinyal generik.
12. Fact retrieval memakai query dan slot terstruktur; ranking dominan tetap dipertahankan dengan hysteresis.

## 2. Status Prioritas

| Prioritas | Status | Hasil |
|---|---|---|
| COR-02 — Provenance/fallback LLM | SELESAI di kode | Provider dipisahkan dari validation status |
| COR-01 — `user_id` end-to-end | SELESAI | Field wajib di type, Zod, request, backend replay |
| Unique-user Action Engine | SELESAI | Minimum 2 user unik sebelum action |
| QA-01 — Smoke test | SELESAI | Counter aman terhadap `set -e`; flow tidak berhenti dini |
| Frontend reliability | SELESAI | Health refresh, typed polling, retry, generation state, input guard |
| Regression tests | SELESAI | 40/40 test lulus |
| COR-04 — Evidence text | SELESAI | Window menyimpan dan mengambil teks evidence |
| Retry idempotency | SELESAI | Hasil per `comment_id` di-cache per session |
| Session concurrency minimum | SELESAI | Analyze dan polling memakai lock per session |
| Full Windows Docker E2E | PERLU DIULANG | Docker Desktop tidak terhubung ke WSL workspace audit |
| Secret kompetisi | TIDAK DIUBAH | Tetap accepted temporary risk sesuai keputusan tim |

## 3. Perubahan Teknis

### 3.1 Provenance LLM

Ditambahkan `GenerationResult` pada `backend/llm_client.py`:

```text
raw_output
provider: GEMINI | TEMPLATE
```

Provider tidak lagi diturunkan dari hasil validator. Resolver murni baru di `backend/generation_provenance.py` menerapkan invariant:

| Kondisi | Provider | Pipeline | Fallback |
|---|---|---|---|
| Gemini berhasil dan valid | `GEMINI` | `CARD_READY` | `false` |
| Template client valid | `TEMPLATE` | `FALLBACK` | `true` |
| Gemini gagal validasi dan validator memakai fallback | `TEMPLATE` | `FALLBACK` | `true` |

`CoachCard` sekarang membawa `generation_provider`. Frontend memvalidasinya dengan Zod dan menampilkan label `Gemini` atau `Template` di samping status validasi.

Status fallback juga disimpan sebagai `latest_pipeline_status`, sehingga polling kedua dan seterusnya tidak mengubah fallback menjadi `CARD_READY`.

### 3.2 Health LLM

Health tidak lagi menyatakan Gemini `READY` hanya karena API key tersedia:

- Belum ada call aktual: `UNKNOWN`, provider `Gemini API (unverified)`.
- Generation Gemini berhasil: `READY`, provider `Gemini API`.
- Key tidak ada/call gagal: `DEGRADED`, provider `Template Fallback`.

Ini tidak menambah call API berbayar pada endpoint health.

### 3.3 User Identity dan Unique-user Trend

`user_id` sekarang:

- Wajib pada `CommentEntry` TypeScript.
- Wajib pada `CommentEntrySchema` Zod.
- Diteruskan oleh replay controller ke analyze API.
- Tersedia pada backend replay loader.
- Dipertahankan dalam rolling-window entry.

Action rules mendapat `min_unique_users_60s: 2`. Bridge meneruskan `unique_user_count` ke Action Engine. Empat komentar dari satu user tidak lagi cukup untuk memicu tren; dua komentar dari dua user dapat memicu tren jika threshold lain terpenuhi.

### 3.4 Evidence Text

Rolling-window entry sekarang menyimpan:

```text
(timestamp, comment_id, user_id, signal, confidence, cleaned_text, slots)
```

Saat membuat prompt, orchestrator mengambil teks berdasarkan evidence IDs dengan urutan yang sama. Gemini sekarang menerima komentar aktual seperti `bb 55 ambil size apa`, bukan string `CMT-001`.

### 3.5 Idempotency dan Concurrency Minimum

- Setiap session menyimpan `processed_results` berdasarkan `comment_id`.
- Retry ID yang sama mengembalikan deep copy hasil sebelumnya tanpa menambah counter/window/priority lagi.
- Analyze dan card polling dilindungi `RLock` per session.
- Reset mencoba membatalkan pending LLM future.

Ini adalah hardening MVP, bukan pengganti Redis/database untuk deployment multi-worker.

### 3.6 Smoke Test

Perbaikan pada `scripts/smoke_test.sh`:

- Increment counter tidak lagi memicu `set -e`.
- Dua komentar dari dua user dipakai untuk memicu action.
- Retry idempotency diperiksa.
- Card dipoll maksimal 15 detik.
- `generation_provider` dan `fallback_used` diperiksa.
- Pada mode full AI, health harus berubah menjadi Gemini READY setelah generation nyata.
- `REQUIRE_FULL_AI=0` dapat digunakan untuk menguji degraded/template mode secara jujur.

Perintah:

```bash
# Release/kompetisi: wajib Gemini
bash scripts/smoke_test.sh

# Uji graceful fallback
REQUIRE_FULL_AI=0 bash scripts/smoke_test.sh
```

## 4. Regression Tests

File baru: `tests/test_core_regressions.py`.

Test yang lulus:

1. Gemini valid menjadi `CARD_READY`.
2. Template valid tetap menjadi `FALLBACK`.
3. Validator fallback mengubah provider akhir menjadi `TEMPLATE`.
4. Frontend runtime schema mewajibkan `generation_provider`.
5. Frontend mewajibkan dan meneruskan `user_id`.
6. Dataset demo memiliki identitas user berulang yang valid.
7. Rolling window mempertahankan unique-user count dan evidence text.
8. Satu user tidak dapat menciptakan tren.
9. Dua user dapat menciptakan tren.
10. Frontend tidak mempromosikan fallback lama menjadi `CARD_READY` saat komentar baru belum membawa card.
11. Showcase replay memiliki contract valid dan urutan trigger phase yang benar.
12. Polling Coach Card tidak mengakses `comment_id`; lookup idempotensi hanya berada di pipeline komentar.
13. Response polling divalidasi Zod tanpa `as any`.
14. Health membedakan Gemini belum diverifikasi, siap, dan mode fallback.
15. Coach Card membedakan provenance Gemini, template berbasis KB, dan validator fallback.
16. Retry hanya ditawarkan untuk error retryable dan transisi `ERROR` dapat pulih.
17. Polling tidak memakai async interval dan berhenti setelah hasil final tersedia.
18. Parser menolak timestamp menurun tanpa mengurutkan input secara diam-diam.
19. Tiga key dicoba tepat sekali dari setiap posisi awal.
20. Jumlah key dinamis 1, 2, 5, dan 6 tidak menyebabkan key dilewati atau diulang.
21. Konfigurasi tanpa key menghasilkan urutan percobaan kosong.
22. LLM client memakai snapshot urutan dan tidak lagi menghitung dari cursor yang dimutasi.
23. Context generation valid yang identik menggunakan kembali Coach Card.
24. Perubahan evidence material menghasilkan fingerprint baru.
25. Fallback untuk action yang sama digunakan ulang selama cooldown dan boleh dicoba kembali setelah 30 detik.
26. Perubahan evidence kecil tidak menembus cooldown fallback untuk action yang sama.
27. Versi TypeScript terkunci pada versi yang didukung toolchain ESLint.
28. Raw intent size, color, dan stock tidak digabung menjadi sinyal generik.
29. Slot extractor mempertahankan BB, TB, size, dan warna eksplisit.
30. Dominance audiens mengalahkan static business priority.
31. Hysteresis membutuhkan margin dua pengguna unik untuk berganti sinyal.
32. Snapshot mengekspos jumlah pengguna unik dan context retrieval.
33. Size recommendation retrieval memfilter fakta memakai BB/TB.
34. Size options retrieval mengambil fakta single-purpose.
35. Validator menolak respons yang tidak selaras dengan action.
36. Validator menolak warna yang bertentangan dengan requested slot.
37. Validator membedakan size ready dan habis secara spesifik.
38. Priority Event tervalidasi runtime dan terlihat di frontend.
39. Slot dari pengguna berbeda tidak digabung menjadi profil fiktif.
40. Validator menolak klaim stock putih XXL berdasarkan fakta KB aktual.

Perintah:

```bash
python3 -m unittest -v tests/test_core_regressions.py
```

Hasil: **40 passed, 0 failed**.

## 5. Hasil Verifikasi

| Pemeriksaan | Hasil |
|---|---|
| Regression test | PASS — 40/40 |
| Python compileall | PASS |
| Action rules JSON parse | PASS |
| Frontend TypeScript type-check | PASS |
| Frontend production build | PASS |
| ESLint | PASS tanpa warning kompatibilitas TypeScript |
| Shell syntax | PASS |
| Smoke test control-flow pada service offline | PASS — seluruh tahap dijalankan dan summary benar |
| Full Docker E2E | BELUM DIJALANKAN dalam workspace audit |

Docker Desktop tidak terhubung ke distro WSL saat verifikasi final. Compose file tidak diubah dalam paket ini dan sebelumnya telah berhasil dijalankan maintainer dari clone Windows.

## 6. Checklist Re-validasi Windows

Jalankan dari fresh clone/branch berisi perubahan ini:

```bash
docker compose up --build -d
bash scripts/smoke_test.sh
docker compose logs --no-color backend
```

Acceptance criteria:

- Smoke test berakhir `0 failed`.
- Dua komentar user berbeda menghasilkan `SHOW_SIZE_GUIDE`.
- Card full AI memiliki `generation_provider: GEMINI`.
- `fallback_used` bernilai `false` untuk Gemini.
- Jika Gemini sengaja dibuat gagal, card memiliki `generation_provider: TEMPLATE`, `pipeline_status: FALLBACK`, dan `fallback_used: true`.
- Polling ulang tidak mengubah `FALLBACK` menjadi `CARD_READY`.
- `/health` berubah dari `UNKNOWN` menjadi `READY` setelah generation Gemini sukses.

## 7. Remaining Work

Yang belum dikerjakan karena berada setelah prioritas kompetisi:

- Lock dependency Python.
- Pecah `useReplayController` menjadi hook kecil dan migrasikan state utama ke reducer.
- Tambahkan Vitest/React Testing Library setelah dependency tooling diselaraskan; invariant kritis saat ini dilindungi dependency-light regression tests.
- TTL dan cleanup session.
- State eksternal untuk multi-worker.
- Perbaikan error contract 404/422.
- Pembatasan input/rate limiting NLP.
- Perbaikan exit code downloader model.
- Revoke secret setelah kompetisi sesuai accepted-risk plan.

## 8. Keputusan

Kode saat ini **READY FOR FULL DOCKER E2E RE-VALIDATION**. Status final `GO` baru diberikan setelah smoke test full AI lulus pada Windows + Docker Desktop, karena environment itulah target runtime yang digunakan tim.

## 9. Audit Tambahan: TypeScript dan Data Demo

### 9.1 Kompatibilitas TypeScript

Versi aktual pada workspace:

- TypeScript `5.9.3`
- `@typescript-eslint/parser` `7.18.0`
- `@typescript-eslint/eslint-plugin` `7.18.0`
- ESLint `8.57.1`

Parser menampilkan warning karena rentang TypeScript yang didukung resmi adalah `>=4.7.4 <5.6.0`. Dampak saat ini **tidak mengganggu aplikasi**: type-check, production build, dan lint tetap lulus. TypeScript juga hanya digunakan saat build dan tidak ikut berjalan di browser.

Risiko tersisa berada pada tooling lint: syntax atau AST TypeScript baru dapat salah dibaca, menghasilkan false positive/negative. Prioritasnya P2, bukan blocker demo. Perbaikan paling konservatif sebelum upgrade toolchain adalah pin TypeScript ke versi 5.5.x; alternatifnya upgrade seluruh keluarga `@typescript-eslint` dan ESLint secara bersamaan lalu ulangi lint/build.

### 9.2 Validitas `comments-demo.jsonl`

Hasil pemeriksaan `data/replay/comments-demo.jsonl`:

| Pemeriksaan | Hasil |
|---|---|
| JSON valid | PASS |
| Field `comment_id`, `user_id`, `timestamp_ms`, `text` | PASS seluruh row |
| Jumlah komentar | 30 |
| User unik | 19 |
| Duplicate `comment_id` | 0 |
| Duplicate text/row | 0 |
| Timestamp negatif | 0 |
| Timestamp terurut | PASS |
| Interval | Konsisten 3 detik |
| Durasi | 87 detik, sesuai klaim sekitar 90 detik |
| User berulang untuk menguji identity | PASS; beberapa user memiliki 2-3 komentar |

Secara format dan contract, file **siap dipakai** setelah perubahan `user_id`.

### 9.3 Kualitas Choreography Demo

Data mencakup bahan/detail produk, ukuran, warna/stok, harga, purchase intent, komentar tidak relevan, ongkir, dan COD. Namun urutannya belum ideal untuk memperlihatkan variasi Coach Card:

1. Product questions muncul lebih dulu.
2. Size questions mulai pada detik 9 dan terus muncul sampai detik 51.
3. `SIZE_FRICTION` memiliki priority rank tertinggi.
4. Dengan rolling window 60 detik, sinyal size terakhir masih aktif sampai akhir replay detik 87.
5. Stock/product/price yang muncul setelahnya berpotensi tidak pernah menggantikan Size Card karena priority rank lebih rendah.

Akibatnya file kemungkinan besar memperlihatkan transisi **Product Detail -> Size Guide**, tetapi tidak menjamin `CONFIRM_STOCK` dan `EXPLAIN_PRICE_PROMO` terlihat sebagai Coach Card terpisah.

Komentar shipping/COD juga tidak memiliki kelas khusus dalam taxonomy IndoBERT delapan kelas saat ini; `SHIPPING_FRICTION` masih tercatat belum aktif di action rules. Komentar tersebut berguna sebagai contoh graceful non-action, tetapi jangan dipresentasikan sebagai fitur shipping aktif.

Rekomendasi choreography tanpa mengubah engine: urutkan cluster dari priority terendah menuju tertinggi, yaitu **price -> product detail -> stock -> size -> purchase intent**. Dengan begitu, sinyal berprioritas lebih tinggi yang datang belakangan dapat menggantikan card sebelumnya meskipun semuanya masih berada dalam window 60 detik.

Rekomendasi tersebut sudah diterapkan dalam `data/replay/comments-demo-showcase.jsonl`. File asli dipertahankan sebagai mixed-natural demo, sedangkan file baru menjadi demo deterministik untuk penjurian.

## 10. Update Frontend Reliability dan Presentasi AI

Perbaikan frontend setelah validasi runtime Docker Desktop:

1. `/health` diambil ulang ketika Coach Card baru diterima, sehingga status awal `Gemini API (unverified)` tidak tertinggal setelah generation berhasil.
2. Status header sekarang membedakan `Gemini belum diverifikasi`, `Sistem siap`, `Mode fallback`, gangguan NLP, dan backend offline.
3. Operator dapat menjalankan health check ulang dari panel replay tanpa reload halaman.
4. Coach Card menampilkan provenance yang tidak ambigu:
   - `Gemini · Lolos validasi KB`
   - `Template aman · Berbasis KB`
   - `Fallback aman · Output Gemini ditolak`
5. Response `/api/v1/session/card` memiliki schema Zod penuh; `pipeline_status as any` dihapus dan invariant `fallback_used` diperiksa terhadap provider.
6. `is_generating` dan `pending_action` sekarang terlihat di UI. Kartu lama diberi keterangan jika rekomendasi baru sedang disiapkan.
7. Poller memakai recursive timeout agar request tidak overlap dan berhenti saat replay selesai serta generation final sudah terkumpul.
8. Retry menghormati `retryable`. Kegagalan start dapat kembali ke `STARTING`, sedangkan kegagalan komentar dapat kembali ke `RUNNING`.
9. File replay dibatasi 5 MB/10.000 komentar, mempertahankan nomor baris asli, dan menolak timestamp menurun.

Verifikasi update frontend:

| Pemeriksaan | Hasil |
|---|---|
| TypeScript type-check | PASS |
| ESLint | PASS tanpa warning kompatibilitas TypeScript |
| Vite production build | PASS |
| Regression tests | PASS — 40/40 |
| `git diff --check` | PASS |

Full visual/runtime re-validation tetap perlu dilakukan dari clone Windows karena Docker Desktop tidak terhubung ke workspace WSL ini.

## 11. Update Rotasi Key dan Penghematan Quota

Analisis log Docker menemukan pola rotasi lama `1 → 3 → 3`. Penyebabnya adalah cursor key dimutasi di dalam loop dan langsung dipakai lagi untuk menghitung iterasi selanjutnya.

Perbaikan yang diterapkan:

1. Urutan key dihitung sekali melalui helper murni `key_attempt_order` sebelum request pertama dilakukan.
2. Setiap slot dicoba tepat satu kali, mulai dari cursor aktif. Contoh tiga key: `1 → 2 → 3`, `2 → 3 → 1`, atau `3 → 1 → 2`.
3. Jumlah key tetap dinamis; penambahan menjadi lima atau enam cukup melalui `GEMINI_API_KEYS`.
4. Log keberhasilan mencatat nomor slot key tanpa menampilkan secret.
5. Context generation memiliki fingerprint dari action, audience state, evidence IDs, dan required fact types.
6. Coach Card valid digunakan ulang selama fingerprint tidak berubah.
7. Template fallback untuk action yang sama digunakan ulang selama 30 detik walau evidence bertambah, lalu diizinkan mencoba Gemini kembali agar layanan dapat pulih.

Dampak yang diharapkan:

- Tidak ada key yang dilewati atau dicoba dua kali dalam satu putaran failover.
- Repeated `SHOW_SIZE_GUIDE` dengan evidence sama tidak lagi membuat request Gemini baru.
- Penambahan API key tidak memerlukan perubahan kode.
- Pesan `All N Gemini API keys exhausted` baru terjadi setelah seluruh slot benar-benar dicoba.

Pekerjaan lanjutan P1 yang belum termasuk paket ini: cooldown per-key berdasarkan metadata `retryDelay`, klasifikasi `401/403`, dan perbaikan lifecycle task yang sudah berjalan ketika action berubah.
