# LiveCoach AI — M3/SCR-3 (LLM · Knowledge · Policy)

Folder ini berisi seluruh deliverable milik **M3/SCR-3** untuk babak
Penyisihan AIC COMPFEST 18 — sesuai pembagian peran: *"Knowledge base,
response dataset, QLoRA, validator, action rules"*, di-review silang oleh
M2/SCR-2, dan dependency-nya diintegrasikan oleh M4/SCR-1 (backend).

Acuan tunggal untuk semua keputusan di sini adalah
`LiveCoach_AI_Spesifikasi_Web_Penyisihan.docx` (v1.0, 5 Agustus 2026) yang
dibagikan tim — kalau ada bagian repo ini yang kelihatan beda dari dokumen,
**dokumen yang menang**, bukan repo ini (kecuali sudah disepakati bersama dan
`schema_version` dinaikkan).

## Status per 19 Agustus 2026

Repo ini baru saja melalui review menyeluruh yang menemukan bahwa versi
sebelumnya memakai taxonomy `audience_state`/`selected_action` buatan sendiri
yang **tidak cocok** dengan enum resmi di dokumen (Section 4.2 & 11). Semua
file di bawah sudah ditulis ulang supaya selaras. **Baca `DECISIONS_LOG.md`**
di folder ini untuk kronologi lengkap apa yang salah, apa yang diperbaiki, dan
apa yang masih sengaja ditunda — dokumen itu juga berguna sebagai bukti
"proses & alasan keputusan" untuk proposal (bobot penilaian 15%).

## Peta folder → langkah pipeline

Mengacu ke alur satu-komentar di Section 3.2 dokumen:

```
Comment → [NLP: M2] → [Aggregator 60s: M2] → Action Engine (M3) → Knowledge Base (M3)
          → Grounded LLM/QLoRA (M3) → Validator (M3) → Coach Card (frontend: M5)
```

| Folder | Tanggung jawab | Langkah pipeline |
|---|---|---|
| `Knowledge Base/` | Fakta produk statis + fungsi lookup by fact_type | Step "Backend mengambil fakta produk statis yang relevan" |
| `Action Engine/` | Aturan deterministik: sinyal 60 detik → audience_state + selected_action + required_fact_types | Step "Jika sinyal cukup, Action Engine memilih satu action" |
| `Response Dataset/` | Dataset (input, output) untuk fine-tuning Grounded LLM | Bahan training step "LLM dengan QLoRA" |
| `LLM dengan QLoRA/` | Fine-tuning + system prompt Grounded LLM | Step "Grounded LLM menyusun response candidate" |
| `Validator/` | Cek struktur/fakta/angka/panjang output LLM sebelum tampil | Step "Validator meloloskan response atau menggantinya dengan fallback" |

Urutan baca yang disarankan untuk orang baru: `Knowledge Base` → `Action
Engine` → `Response Dataset` → `LLM dengan QLoRA` → `Validator`. Tiap folder
punya `README.md` sendiri yang lebih detail.

## Cara jalankan cepat (tanpa GPU, tanpa training)

```bash
cd "Action Engine"   && python3 action_engine.py
cd "../Knowledge Base" && python3 knowledge_base.py
cd "../Response Dataset" && python3 generate_response_dataset.py
cd "../Validator" && python3 run_validation_report.py
```

Semua path di atas relatif antar-folder (`Path(__file__).parent.parent /
"Knowledge Base" / ...` dst) — kalau struktur folder ini dipindah/direstruktur
ulang oleh M4 saat integrasi ke repo backend utama, sesuaikan konstanta
`FACTS_PATH` / `DATASET_PATH` di masing-masing file.

Training QLoRA (`LLM dengan QLoRA/qlora_train.py`) **wajib** dijalankan di
Google Colab (GPU) — lihat README di folder itu.

## Yang masih perlu dikoordinasikan ke tim lain

- **Ke M2/SCR-2:** konfirmasi Intent enum resmi (`source_intents` di
  `action_rules.json`) benar-benar sama dengan output model IndoBERTweet
  mereka.
- **Ke M1/Ketua:** klarifikasi inkonsistensi `ValidationStatus` di dokumen
  (Section 7.5/10.4 vs Section 11) — lihat catatan di
  `Validator/validator.py` dan `DECISIONS_LOG.md`.
- **Ke M4:** modul ini di-`import` sebagai Python biasa (bukan package
  ter-install), jadi cara load-nya (`sys.path`, relative import) perlu
  disesuaikan begitu digabung ke repo backend utama.

## Yang sengaja belum dikerjakan (bukan kelupaan)

3 dari 8 pasang `audience_state`/`selected_action` resmi (`SHIPPING_FRICTION`,
`OBJECTION_SPIKE`, `PURCHASE_MOMENT`) belum diaktifkan di `action_rules.json`
— keputusan tim 19 Agustus 2026 untuk stabilkan 4 yang sudah ada dulu. Detail
dan status kesiapan Knowledge Base untuk masing-masing ada di
`Action Engine/action_rules.json` (key `not_yet_implemented`) dan
`DECISIONS_LOG.md`.
