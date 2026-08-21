# Aplikasi Scraper Komentar TikTok Live

Bagian ini menjelaskan cara menjalankan dan memakai aplikasi scraper di folder
`tiktok-comment-scraper/`. Aplikasi menangkap komentar dari siaran langsung (`live`) TikTok
menggunakan library pihak ketiga [TikTokLive](https://github.com/isaackogan/TikTokLive),
menyimpannya per-sesi ke JSONL, dan menampilkan dashboard realtime di browser.

## Prasyarat

- Python 3.11+ (repo ini dikembangkan di Python 3.14).
- Akun TikTok yang sedang **live** — scraper hanya menangkap komentar dari sesi
  yang sedang berjalan, bukan riwayat/video.
- Akses internet.

## Instalasi

```powershell
python -m venv venv
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Dependency scraper (`requirements.txt`):

| Paket | Fungsi |
|---|---|
| `fastapi` + `uvicorn` | REST API dan server WebSocket |
| `TikTokLive` | koneksi ke live TikTok dan event komentar |
| `python-dotenv` | baca konfigurasi dari `.env` (opsional) |

## Menjalankan

```powershell
& ".\venv\Scripts\python.exe" -m uvicorn tiktok-comment-scraper.main:app --reload
```

Buka <http://127.0.0.1:8000> di browser → isi username TikTok (boleh dengan atau
tanpa `@`) → klik **Start**. Hentikan dengan tombol **Stop** di dashboard, atau
lewat API.

## Endpoint API

Semua endpoint di bawah prefix `/live`:

| Method | Path | Deskripsi |
|---|---|---|
| `POST` | `/live/start` | Mulai menangkap komentar. Body: `{"username": "namaakun"}` |
| `POST` | `/live/stop` | Hentikan sesi yang sedang berjalan |
| `GET`  | `/live/status` | Cek status (`running` + `username`) |

### WebSocket `/ws`

Dashboard memakai WebSocket untuk menerima update realtime. Pesan yang dikirim
server ke klien:

```json
{"type": "status", "running": true, "username": "@akun", "session_id": "...", "room_id": "...", "file": "...", "comment_count": 0}
{"type": "comment", "session_id": "...", "nickname": "nama", "username": "id", "text": "isi komentar"}
```

## Format Output

Setiap sesi live ditulis ke satu file JSONL di `data/raw/` dengan penamaan
`<username>_<room_id>_<tanggal>-<jam>.jsonl`. Tiga tipe baris:

### `session_start` (baris pertama)

```json
{"type": "session_start", "session_id": "...", "username": "@akun", "room_id": "...", "started_at": "2026-08-08T16:18:02"}
```

### `comment` (satu baris per komentar)

```json
{"type": "comment", "session_id": "...", "timestamp": 1760000000, "text": "kak bb 60 size apa"}
```

### `session_end` (baris terakhir)

```json
{"type": "session_end", "session_id": "...", "ended_at": "2026-08-08T17:20:11", "comment_count": 153}
```

> Catatan: `comment` tidak menyimpan `nickname`/`username` ke file — hanya isi
> teks komentar. Metadata lengkap hanya tampil di terminal dan dashboard.

## Alur ke Pipeline ML

1. Scrape beberapa sesi → kumpulan file di `data/raw/` (gitignored).
2. `fine-tuned-indobert/pipeline.py` (lihat [fine-tuning.md](fine-tuning.md)) membaca `data/raw/`,
   mengekstrak komentar unik, melabeli, menyusun dataset 10.000 komentar
   (`data/dataset/tiktok_live_10k.jsonl`), melatih model, dan mengevaluasinya.

## Catatan & Batasan

- TikTok dapat mengubah protocol koneksi kapan saja; `TikTokLive` bersifat
  komunitas dan tidak resmi. Jika koneksi gagal, perbarui versi library atau
  tunggu pembaruan maintainer.
- Akun yang tidak sedang live akan gagal pada `POST /live/start`.
- Scrape sebaiknya dibatasi pada akun/sesi yang Anda miliki atau telah
  disetujui, serta mematuhi ketentuan layanan TikTok.