# Model Artifacts

Folder ini menyimpan model artifacts (checkpoint, adapter) yang dihasilkan
dari training. Untuk preliminary:

## IndoBERT Intent Classifier
- Checkpoint tersimpan di: `ai/intent_classifier/outputs/models/`
- Dijalankan sebagai service terpisah via `ai/intent_classifier/ml/serve.py`

## QLoRA LLM Adapter
- Adapter tersimpan di: `ai/grounded_llm/LLM dengan QLoRA/livecoach-qlora-adapter/`
- Dijalankan sebagai service terpisah (jika tersedia)

## Catatan
- Jika model tidak tersedia, backend otomatis menggunakan fallback:
  - NLP: keyword-based heuristic
  - LLM: template-based response
