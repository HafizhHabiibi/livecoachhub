# Dokumentasi Teknis LiveCoachHub

Lihat [PROJECT.md](../PROJECT.md) untuk desain sistem terintegrasi.

## Arsitektur Pipeline

```
Comment → Preprocessing → Spam Filter → NLP (IndoBERT)
→ Taxonomy Adapter → Rolling Window 60s
→ [Trend Lane] → Action Engine → Fact Retrieval → LLM → Validator
→ [Priority Lane] → Priority Alert
→ PipelineResult → Frontend
```

## Referensi
- **Frontend contracts**: `frontend/src/contracts/livecoach.ts`
- **Backend config**: `backend/config.py`
- **Action rules**: `AI/grounded_llm/Action Engine/action_rules.json`
- **Product facts**: `AI/grounded_llm/Knowledge Base/product_facts_v2.json`
- **NLP Intent Classifier**: `AI/NLP/fine-tuned-indobert/serve.py` (port 8010)
- **NLP Model**: `AI/NLP/fine-tuned-indobert/outputs/models/indobert-intent/run1/best/`
- **NLP Pipeline**: `AI/NLP/fine-tuned-indobert/pipeline.py`
