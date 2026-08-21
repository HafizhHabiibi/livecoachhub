# Fine-Tuning IndoBERT untuk Klasifikasi Intent Komentar TikTok

Dokumen ini menjelaskan pipeline ML dari komentar mentah hingga model yang siap
pakai, beserta cara menjalankan semuanya — termasuk dengan **satu perintah**
dengan progress di terminal.

## Pipeline Sekilas

```
data/raw/                       komentar hasil scrape (JSONL per sesi)
  └── fine-tuned-indobert/preprocessing/extract_unique.py     → komentar unik ke to_label/
  └── fine-tuned-indobert/preprocessing/merge_labels.py        → gabung label manual (QC) → comments_labeled
fine-tuned-indobert/dataset/relabel.py            → relabel ulang dgn rule engine → relabel_draft
fine-tuned-indobert/dataset/mark_sentiment.py     → tandai sentiment (seed 42, ~2,7% pos / 2,3% neg)
fine-tuned-indobert/dataset/combine.py            → gabung batch → all_generated.csv
fine-tuned-indobert/dataset/dedupe.py             → hapus duplikat/near-dup vs asli → merged_10k.csv
fine-tuned-indobert/dataset/to_jsonl.py           → tiktok_live_10k.jsonl (dataset final, 10.000)
fine-tuned-indobert/dataset/validate.py           → validasi struktur + laporan report.md
fine-tuned-indobert/preprocessing/build_dataset.py → split 80/10/10 terstratifikasi → indobert_dataset/
fine-tuned-indobert/train.py                      → fine-tuning IndoBERT (per run)
fine-tuned-indobert/evaluate.py + fine-tuned-indobert/threshold.py → evaluasi test set + analisis threshold
fine-tuned-indobert/predict.py, fine-tuned-indobert/serve.py       → inferensi CLI / API
```

## Taksonomi

Labeling memakai 8 intent dengan satu label dominan per komentar + 1 sentiment:

| label_id | Intent | Contoh singkat |
|---|---|---|
| 0 | `product_inquiry` | "bahan ap kak?", "spill etalase 2", "panjangnya berapa" |
| 1 | `size_inquiry` | "spil ukuran dong", "size s masih ada?", "ada ukuran m?" |
| 2 | `size_recommendation` | "bb 60 tb 165 ukuran apa", "muat ga bb 90" |
| 3 | `color_inquiry` | "warna navy ada?", "yg item ready?" |
| 4 | `price_inquiry` | "harga berapa?", "ongkir gratis?", "500k ya?" |
| 5 | `stock_availability` | "kapan restock?", "stoknya masih ad?" |
| 6 | `purchase_intent` | "co dulu", "mau beli 2", "dm buat order" |
| 7 | `not_relevant` | "wkwk", "fyp", emoji saja, spam |

Taksonomi lengkap + aturan labelling ada di `fine-tuned-indobert/configs/taxonomy.yaml`.

## Cara Menjalankan (Satu Perintah)

Pastikan dulu dependency ML terpasang:

```powershell
& ".\venv\Scripts\python.exe" -m pip install -r requirements-ml.txt
```

Jalankan seluruh pipeline (data → split → train → evaluasi) dengan progress di
terminal:

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py
```

Opsi berguna:

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --run run2      # simpan hasil ke run2
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --data-only      # sampai split saja (tanpa train)
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --only train,evaluate  # hanya langkah tertentu
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --force          # jalankan ulang langkah yang biasanya di-skip
```

Langkah yang asetnya sudah ada (mis. `comments_labeled.csv`,
`relabel_draft.csv`, `tiktok_live_10k.jsonl`) otomatis dilewati agar repotrain
tidak perlu mengulang satu demi satu. Gunakan `--force` hanya bila ingin
meregenerasi dari awal.

## Menjalankan Manual per-langkah

Urutan ekuivalennya (berguna untuk debugging atau eksperimen):

```powershell
$py = ".\venv\Scripts\python.exe"

# 1. preprocessing komentar mentah -> unik + batch label
& $py -X utf8 fine-tuned-indobert\preprocessing\extract_unique.py
& $py -X utf8 fine-tuned-indobert\preprocessing\merge_labels.py

# 2. relabel ulang komentar asli dengan rule engine
& $py -X utf8 fine-tuned-indobert\dataset\relabel.py

# 3. rakit dataset 10k dari batch teks + dedupe + validasi
& $py -X utf8 fine-tuned-indobert\dataset\mark_sentiment.py
& $py -X utf8 fine-tuned-indobert\dataset\combine.py
& $py -X utf8 fine-tuned-indobert\dataset\dedupe.py
& $py -X utf8 fine-tuned-indobert\dataset\to_jsonl.py
& $py -X utf8 fine-tuned-indobert\dataset\validate.py

# 4. split train(val/test (80/10/10, terstratifikasi per intent, seed 42)
& $py -X utf8 fine-tuned-indobert\preprocessing\build_dataset.py

# 5. fine-tuning
& $py -X utf8 fine-tuned-indobert\train.py --run run1

# 6. evaluasi + analisis threshold
& $py -X utf8 fine-tuned-indobert\evaluate.py --run run1
& $py -X utf8 fine-tuned-indobert\threshold.py --run run1
```

## Dataset Final

`data/dataset/tiktok_live_10k.jsonl` berisi 10.000 komentar:

- 8 intent × 1.250 komentar (seimbang) + 3 sentiment (`positive` 270,
  `neutral` 9.497, `negative` 233 — proporsi mengikuti distribusi asli).
- Skema tiap baris: `{"comment_id", "text", "intent", "sentiment"}`.
- Komposisi: **1.751 komentar asli hasil scrape langsung** dari sesi live TikTok
  + **8.249 komentar pengembangan** yang dibentuk dari pola/konteks komentar
  asli agar tiap intent punya jumlah yang seimbang. Seluruh proses pembentukan
  sudah melalui validasi otomatis (`validate.py`, menghasilkan `report.md`).

Cara menghitung ulang laporan dataset:

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\dataset\validate.py
```

## Training

Konfigurasi ada di `fine-tuned-indobert/configs/finetune.yaml`:

- Model: `indobenchmark/indobert-base-p1` (unduh otomatis saat pertama kali
  dijalankan, ± 1,5 GB).
- Data: `data/processed/indobert_dataset` (train 8.000 / val 1.000 / test
  1.000, split deterministik seed 42).
- Hyperparameter: batch 16, 5 epoch, LR 2e-5, FP16, early stopping (patience 2),
  class weight seimbang (`1.0` per intent karena dataset sudah seimbang).

Jika GPU OOM (mis. VRAM 4 GB), turunkan `batch_size` ke 8 di `finetune.yaml`.

Hasil tiap run disimpan di `outputs/models/indobert-intent/<run>/` (gitignored):
- `best/` — checkpoint terbaik (model + tokenizer) yang dipakai evaluasi/predict/serve
- `train_meta.json` — ringkasan konfigurasi dan metrik

## Evaluasi

- `evaluate.py --run <run>` menghasilkan di `outputs/evaluation/<run>/`:
  `classification_report.csv`, `confusion_matrix.csv`, `test_predictions.csv`
  (label asli vs prediksi + confidence), dan `report.json` (accuracy, macro/weighted F1,
  F1 per kelas).
- `threshold.py --run <run>` menganalisis pengaruh confidence threshold pada
  metrik (remap prediksi ber-skor rendah ke `other`) dan merekomendasikan
  threshold terbaik berdasarkan weighted F1.
- Untuk perbandingan dengan baseline non-neural: `fine-tuned-indobert/cv.py` (k-fold
  holdout) dan `fine-tuned-indobert/baseline.py` (TF-IDF + Logistic Regression) — dua-duanya
  memakai fold yang sama (session-based jika ada `session_id`, jika tidak
  stratified k-fold 5 lipatan dengan seed sama).

## Inferensi

### CLI

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\predict.py --text "bb 60 tb 165 size apa"
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\predict.py --file data\komentar_baru.csv --col text --out hasil.csv
```

### API

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\serve.py --port 8010
```

Endpoint: `GET /health`, `GET /intents`, `POST /predict` dengan body
`{"texts": ["komentar 1", "komentar 2"]}`. Opsional `threshold` untuk menolak
prediksi ber-skor rendah (diklasifikasi sebagai `other`).

## Reproducibility

- Semua langkah deterministik: seed tetap (42), urutan batch tetap, dedupe
  pakai normalisasi teks + Jaccard 4-gram (threshold 0,95).
- `outputs/` tidak di-track di git; hasil evaluasi muncul kembali setiap kali
  pipeline dijalankan.
- Versi CUDA/GPU berbeda bisa menghasilkan angka yang sedikit berbeda meski
  seed sama.

## Troubleshooting

- **Download model lambat/gagal** — pastikan internet stabil; model ditarik
  otomatis dari Hugging Face saat `train.py` pertama dijalankan.
- **CUDA OOM** — turunkan `batch_size` di `finetune.yaml` (16 → 8/4).
- **Karakter berantakan di terminal Windows** — selalu jalankan dengan `-X utf8`.
- **`fine-tuned-indobert/dataset/dedupe.py` lambat** — memakai indeks 4-gram; progress bar akan
  muncul di terminal (pakai `tqdm`).