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
- **Action rules**: `ai/grounded_llm/Action Engine/action_rules.json`
- **Product facts**: `ai/grounded_llm/Knowledge Base/product_facts_v2.json`
