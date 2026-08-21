# Decisions Log — M3/SCR-3

Catatan kronologis keputusan yang diambil saat review & perbaikan folder M3
tanggal **19 Agustus 2026**, sebelum submission babak Penyisihan. Ditulis
supaya (a) tim lain paham kenapa sesuatu berubah dari versi sebelumnya, dan
(b) bisa dilampirkan sebagai bukti "proses & alasan keputusan" di proposal
(dokumen Section 2.1: bobot penilaian proposal & proses 15%).

---

## 1. Temuan utama sebelum perbaikan

Review terhadap folder kerja menemukan 4 masalah utama:

1. **Kontrak enum tidak sinkron dengan dokumen.** `action_rules.json` versi
   lama memakai `audience_state`/`selected_action` buatan sendiri
   (`STOCK_COLOR_CONCERN`, `MATERIAL_SAFETY_CONCERN`, `SHOW_PROMO_INFO`, dst)
   yang tidak cocok dengan 8 pasang enum resmi di Section 4.2 & 11 dokumen.
   Dokumen eksplisit: *"Enum dibandingkan secara exact; jangan mengandalkan
   label tampilan untuk logika."*
2. **Kode tidak bisa dijalankan langsung dari struktur folder yang dikirim.**
   `action_engine.py` mencari `action_rules.json`, file aslinya bernama
   `action_rules (1).json`. `validator.py` mencari `product_facts_v2.json` di
   folder yang sama, padahal file itu ada di folder lain (`Knowlage Base`,
   juga salah eja).
3. File 171 MB `claude-desktop_amd64.deb` ikut ter-zip di folder Knowledge
   Base (ke-drag tidak sengaja).
4. `livecoach-dashboard-shadcn.html` menampilkan fitur yang eksplisit
   dilarang di Section 1.3 dokumen untuk babak penyisihan (viewer count,
   grafik engagement, tombol Done/Skip).

## 2. Keputusan yang diambil (dikonfirmasi user/M3 pada sesi yang sama)

| # | Keputusan | Pilihan yang diambil |
|---|---|---|
| 1 | Cara menyikapi mismatch enum | **Ikuti 8 enum resmi dokumen persis** — bukan mempertahankan taxonomy custom, bukan hybrid |
| 2 | Cakupan perbaikan action | **Perbaiki 4 pasang yang datanya sudah ada dulu**; 3 pasang yang butuh konten benar-benar baru (fact + dataset dari nol) ditunda menyusul |
| 3 | File `.deb` dan HTML dashboard di luar scope | **Dihapus dari zip final**, tidak disimpan sebagai referensi |

## 3. Detail pemetaan taxonomy lama → resmi

| Lama (v1, custom) | Resmi (v2, dipakai sekarang) | Alasan |
|---|---|---|
| `PRICE_FRICTION` → `SHOW_PROMO_INFO` | `PRICE_FRICTION` → `EXPLAIN_PRICE_PROMO` | Rename action agar sama persis dengan dokumen |
| `SIZE_FRICTION` → `SHOW_SIZE_GUIDE` | tidak berubah | Sudah cocok dari awal |
| `STOCK_COLOR_CONCERN` → `CONFIRM_STOCK_COLOR` | `STOCK_FRICTION` → `CONFIRM_STOCK` | Digabung; "color" bukan Intent resmi terpisah (Section 4.1), pertanyaan warna terkait stok dianggap `STOCK_AVAILABILITY` |
| `MATERIAL_SAFETY_CONCERN` → `EXPLAIN_MATERIAL` | `PRODUCT_INFO_GAP` → `EXPLAIN_PRODUCT_DETAIL` | Bahan/keamanan produk = detail produk; ini state resmi ke-4 yang datanya (fact + 15 contoh dataset) sudah ada, jadi diaktifkan sekarang, bukan ditunda — **ini satu-satunya tempat asisten membuat judgment call di luar 4 pilihan literal, tolong di-review ulang oleh M3/ketua** |

**Yang TIDAK ikut berubah:** `response_text`, `evidence_comments`, dan
`fact_id` di setiap entry dataset — semua konten sudah grounded dari awal,
yang berubah murni label `selected_action`/`audience_state` (metadata).

## 4. Perubahan struktural lain

- `Knowlage Base/` → `Knowledge Base/` (perbaikan ejaan).
- `product_facts_v2.json` naik ke `product_facts.v3`: tiap fact dapat field
  `fact_type` baru (nilai resmi: `PRICE_PROMO`/`SIZE_GUIDE`/`STOCK`/
  `PRODUCT_DETAIL`/`SHIPPING`/`FAQ_PLAYBOOK`/`CHECKOUT_GUIDE`) untuk
  dicocokkan ke `required_fact_types`. Field `category` lama (granular, mis.
  `SIZE_GUIDE_ANAK`) tetap dipertahankan untuk organisasi internal.
  `RETURN_POLICY`/`WARRANTY` ditag `FAQ_PLAYBOOK` (siap dipakai begitu
  `OBJECTION_SPIKE` diaktifkan). `SHIPPING` ditag siap juga. `CHECKOUT_GUIDE`
  **belum ada fact sama sekali** — perlu dibuat dari nol nanti.
- `knowledge_base.py` (baru): fungsi `get_facts(fact_types)` untuk
  menjembatani `ActionDecision.required_fact_types` → daftar fact aktual.
  Sebelumnya tidak ada kode untuk langkah ini sama sekali.
- Folder `Response Dataset/` sekarang jadi lokasi **canonical** untuk
  `generate_response_dataset.py` + `response_dataset.jsonl`. Salinan
  duplikat yang sebelumnya ada di folder `Validator/` dihapus.
- `validator.py`: `FACTS_PATH` diperbaiki (ambil dari `../Knowledge Base/`),
  `ACTION_FALLBACK_TEMPLATES` di-rename ikut enum resmi, ditambah catatan
  soal inkonsistensi `ValidationStatus` di dokumen (lihat §5).
- `run_validation_report.py`: `DATASET_PATH` diperbaiki (ambil dari
  `../Response Dataset/`). Sudah dites ulang: **60/60 PASSED**.

## 5. Hal yang TIDAK diputuskan sepihak — perlu keputusan tim

- **`ValidationStatus` di dokumen tidak konsisten**: Section 7.5 & 10.4 pakai
  `PASSED`/`FALLBACK`, Section 11 (Enum Registry) pakai
  `PASSED`/`FAILED`/`NOT_RUN`. `validator.py` saat ini ikut Section 7.5/10.4
  karena itu yang muncul di contoh payload nyata & Coach Card. **Perlu
  konfirmasi ke M1/ketua** sebelum ini dianggap final.
- **Intent taxonomy `source_intents`** di `action_rules.json` diasumsikan
  sama dengan Intent enum resmi Section 4.1 — belum pernah diverifikasi
  langsung ke kode M2/SCR-2.

## 6. Belum dikerjakan (sengaja, sesuai keputusan §2 poin 2)

`SHIPPING_FRICTION` → `EXPLAIN_SHIPPING`, `OBJECTION_SPIKE` →
`HANDLE_OBJECTION`, `PURCHASE_MOMENT` → `GUIDE_CHECKOUT`. Status kesiapan
data ada di `Action Engine/action_rules.json` key `not_yet_implemented`.
`PURCHASE_MOMENT` perlu effort paling besar karena fact `CHECKOUT_GUIDE`
belum ada sama sekali di Knowledge Base — padahal ini "purchase moment" /
momen closing, salah satu yang paling penting secara bisnis untuk live
commerce. Disarankan diprioritaskan duluan begitu lanjut ke action baru.

## 7. Item lain dari review yang belum digarap di sesi ini

- Belum ada `requirements.txt` untuk `action_engine.py`/`validator.py`
  (keduanya cuma pakai standard library Python jadi sebenarnya tidak wajib,
  tapi baik untuk didokumentasikan eksplisit).
- Belum ada unit test otomatis (pytest) — saat ini baru manual
  smoke-check (`__main__` blocks) dan `validation_report`.
- QLoRA belum pernah dijalankan end-to-end (tidak ada GPU di sandbox
  pengembangan) — lihat `LLM dengan QLoRA/README.md`.
