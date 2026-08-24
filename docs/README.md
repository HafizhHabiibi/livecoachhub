# Dokumentasi Teknis LiveCoachHub

Lihat [PROJECT.md](../PROJECT.md) untuk desain sistem terintegrasi.

## Arsitektur Pipeline

```
Comment → Preprocessing → Spam Filter → NLP (IndoBERT)
  → Taxonomy Adapter → Rolling Window 60s
  → [Trend Lane] → Action Engine → Fact Retrieval → LLM (Gemini API) → Validator
  → [Priority Lane] → Priority Alert
  → PipelineResult → Frontend
```

## Referensi

- **Frontend contracts**: `frontend/src/contracts/livecoachSchemas.ts`
- **Backend config**: `backend/config.py`
- **Backend orchestrator**: `backend/orchestrator.py`
- **Action rules**: `AI/LLM/grounded_llm/Action Engine/action_rules.json`
- **Product facts**: `AI/LLM/grounded_llm/Knowledge Base/product_facts_v2.json`
- **NLP Intent Classifier**: `AI/NLP/fine-tuned-indobert/serve.py` (port 8010)
- **NLP Model**: `AI/NLP/fine-tuned-indobert/outputs/models/indobert-intent/run1/best/`
- **NLP Pipeline**: `AI/NLP/fine-tuned-indobert/pipeline.py`
- **Replay Data**: `data/replay/comments-demo.jsonl`
- **Product Facts (copy)**: `data/product_facts/product_facts_v2.json`
