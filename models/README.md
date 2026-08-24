# Model Artifacts

Folder ini menyimpan model artifacts (checkpoint) yang dihasilkan
dari training. Untuk preliminary:

## IndoBERT Intent Classifier
- Checkpoint tersimpan di: `AI/NLP/fine-tuned-indobert/outputs/models/`
- Dijalankan sebagai service terpisah via `AI/NLP/fine-tuned-indobert/serve.py`

## LLM (Gemini API)
- Menggunakan Gemini API (`gemini-2.5-flash`) — tidak memerlukan model lokal
- Konfigurasi API key di `.env` atau `.env.enc`

## Catatan
- Jika model/API tidak tersedia, backend otomatis menggunakan fallback:
  - NLP: keyword-based heuristic
  - LLM: template-based response
