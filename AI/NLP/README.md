# TTL Comment Scraper — Klasifikasi Intent Komentar TikTok Live

Proyek end-to-end untuk **mengumpulkan komentar siaran langsung (live) TikTok
lalu melatih model NLP Bahasa Indonesia** untuk memahami maksud pembeli di
live selling fashion.

Bagian dari repository [LiveCoachHub](https://github.com/HafizhHabiibi/livecoachhub)
di folder `ai/NLP/`.

- **Scraper**: aplikasi FastAPI + WebSocket (`tiktok-comment-scraper/`) yang
  menangkap komentar realtime menggunakan Python.
- **Dataset**: 10.000 komentar terkurasi dengan 8 intent + 3 sentiment,
  deterministik dan tervalidasi.
- **Model**: fine-tuning `IndoBERT` (base p1) untuk klasifikasi intent,
  lengkap dengan evaluasi, analisis threshold, baseline, inferensi CLI/API.

## Fitur

- Scraping komentar live TikTok per sesi → file JSONL dengan metadata sesi.
- Dashboard realtime di browser (tanpa framework frontend, vanilla JS).
- Pipeline ML murni Python (tanpa notebook) dengan **satu perintah**
  `fine-tuned-indobert/pipeline.py` disertai progress di terminal.
- Dataset 10.000 komentar seimbang (8 intent × 1.250) + laporan validasi.
- Evaluasi menyeluruh: classification report, confusion matrix, threshold
  confidence, k-fold, dan baseline TF-IDF + Logistic Regression.
- Inferensi via CLI (`fine-tuned-indobert/predict.py`) dan REST API
  (`fine-tuned-indobert/serve.py`).

## Dataset

`data/dataset/tiktok_live_10k.jsonl` berisi **10.000 komentar** TikTok live
selling fashion. Komposisinya transparan:

- **1.751 komentar asli** di-scrape langsung dari sesi live 5 akun fashion
  (4endshop, dcavca, erigo.store, mybasic.indonesia).
- **8.249 komentar pengembangan** dibentuk mengikuti pola/konteks komentar
  asli sehingga setiap intent punya jumlah sama banyak (1.250).
- Sentiment mengikuti distribusi asli: `neutral` 95%, `positive` 2,7%,
  `negative` 2,3%. Keseimbangan antar intent sengaja dibuat agar model tidak
  bias ke kelas mayoritas — tanpa mengubah distribusi sentiment.
- Setiap baris tervalidasi otomatis
  (`fine-tuned-indobert/dataset/validate.py` → `data/dataset/report.md`).

## Struktur Repository

```
ai/NLP/
├── tiktok-comment-scraper/           # Aplikasi scraper (FastAPI + WebSocket)
│   ├── main.py                       #   entry point uvicorn
│   ├── api/                          #   REST /live/* + WebSocket /ws
│   ├── models/ schemas/              #   dataclass Comment, request schema
│   ├── services/                     #   TikTokLive, comment, JSONL writer, broadcast
│   └── static/index.html             #   dashboard single-page (vanilla JS)
├── fine-tuned-indobert/              # Pipeline ML
│   ├── pipeline.py                   # ★ SATU PERINTAH: data → train → evaluate
│   ├── preprocessing/                #   extract_unique, merge_labels, build_dataset
│   ├── dataset/                      #   relabel, mark_sentiment, combine, dedupe,
│   │                                 #   to_jsonl, validate, style_stats
│   ├── configs/                      #   taxonomy.yaml, finetune.yaml
│   ├── train.py / evaluate.py        #   fine-tuning & evaluasi
│   ├── cv.py / baseline.py           #   k-fold & baseline non-neural
│   ├── threshold.py                  #   analisis confidence threshold
│   ├── predict.py / serve.py         #   inferensi CLI / API
│   └── outputs/                      #   evaluation reports (models di-exclude)
├── data/
│   ├── raw/                          #   hasil scrape per sesi (JSONL)
│   ├── dataset/                      #   artefak dataset final
│   │   ├── tiktok_live_10k.jsonl     #     dataset final 10.000 komentar
│   │   ├── merged_10k.csv            #     versi CSV (asli + pengembangan, sudah dedupe)
│   │   ├── relabel_draft.csv         #     hasil relabel 1.751 komentar asli
│   │   ├── report.md                 #     laporan validasi dataset
│   │   └── gen/                      #     batch augmentasi komentar
│   └── processed/                    #   comments_labeled.*, indobert_dataset/
├── docs/
│   ├── scraper.md                    #   cara pakai aplikasi scraper
│   └── fine-tuning.md                #   pipeline ML lengkap + cara menjalankan
├── requirements.txt                  #   dependency scraper
├── requirements-ml.txt               #   dependency ML
└── .gitignore
```

## Cara Pakai Lokal (Quick Start)

Prasyarat: Python 3.11+, GPU NVIDIA CUDA (opsional — CPU tetap jalan).

```powershell
# 1. Clone repo
git clone https://github.com/HafizhHabiibi/livecoachhub.git
cd livecoachhub\ai\NLP

# 2. Environment
python -m venv venv
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\venv\Scripts\python.exe" -m pip install -r requirements-ml.txt
```

```powershell
# 3. (Opsional) Kumpulkan komentar sendiri: jalankan scraper lalu buka dashboard
& ".\venv\Scripts\python.exe" -m uvicorn tiktok-comment-scraper.main:app --reload
#    → http://127.0.0.1:8000 → isi username TikTok yang sedang live → Start
#    Hasil: file JSONL di data/raw/  (detail di docs/scraper.md)
```

```powershell
# 4. Pipeline ML satu perintah (preprocess → dataset → split → train → evaluate)
#    dengan progress di terminal. Dataset final sudah tersedia di repo,
#    jadi langkah data otomatis dilewati dan langsung latih model.
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --run run1
```

Variasi yang sering dipakai:

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --data-only
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --only train,evaluate
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\pipeline.py --force
```

```powershell
# 5. Inferensi cepat
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\predict.py --text "bb 60 tb 165 size apa"

#    atau lewat API (port 8010):
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\serve.py --port 8010
#    POST http://127.0.0.1:8010/predict  {"texts": ["harga berapa kak"]}
```

Penjelasan tiap langkah, taksonomi, dan konfigurasi ada di
[docs/fine-tuning.md](docs/fine-tuning.md).

## Hasil

`outputs/evaluation/` berisi laporan evaluasi. Output model di-exclude dari
git karena ukurannya besar. Untuk menghasilkan ulang:

```powershell
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\evaluate.py --run run1
& ".\venv\Scripts\python.exe" -X utf8 fine-tuned-indobert\threshold.py --run run1
```

Hasil bisa dilihat di `fine-tuned-indobert/outputs/evaluation/run1/`.

## Catatan Etika

- Scrape komentar hanya untuk akun/sesi yang Anda miliki atau telah disetujui,
  dan patuhi ketentuan layanan TikTok.
- Komentar yang dipublikasikan di dataset final telah dibersihkan dari
  identitas pengguna (hanya teks yang disimpan); sisanya berupa pengembangan
  pola komentar, bukan data pengguna baru.
