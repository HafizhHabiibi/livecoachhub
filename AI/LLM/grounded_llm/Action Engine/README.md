# Action Engine

Mengubah agregat sinyal 60 detik (rolling window, hasil kerja M2/SCR-2) jadi
**satu** `AudienceSnapshot` dan **satu** `ActionDecision`, mengikuti aturan
deterministik di `action_rules.json`. Sesuai batas tanggung jawab di Section
3.1 dokumen: modul ini **tidak** memanggil LLM dan **tidak** menyusun kalimat
apa pun — hanya memutuskan *"apa yang harus dibicarakan"*, bukan *"bagaimana
mengucapkannya"*.

## Isi folder

| File | Isi |
|---|---|
| `action_engine.py` | Class `ActionEngine`, entry point `evaluate()` |
| `action_rules.json` | Konfigurasi threshold, tie-break, dan pemetaan state→action→fact_type |

## Kontrak output (selaras Section 10.4 & 11 dokumen)

```python
AudienceSnapshot(state, window_seconds, state_confidence, signals, evidence_comment_ids)
ActionDecision(selected_action, selected_signal, action_score, required_fact_types, required_fact_query, reason)
```

## Status rule aktif

| audience_state | selected_action | required_fact_types | source_intents | Status |
|---|---|---|---|---|
| `SIZE_INFORMATION_GAP` | `SHOW_SIZE_OPTIONS` | `["SIZE_GUIDE"]` | `["SIZE_AVAILABILITY"]` | ✅ Aktif |
| `SIZE_FRICTION` | `SHOW_SIZE_GUIDE` | `["SIZE_GUIDE"]` | `["SIZE_RECOMMENDATION"]` | ✅ Aktif |
| `COLOR_INFORMATION_GAP` | `SHOW_COLOR_OPTIONS` | `["PRODUCT_DETAIL"]` | `["COLOR_AVAILABILITY"]` | ✅ Aktif |
| `STOCK_FRICTION` | `CONFIRM_STOCK` | `["STOCK"]` | `["STOCK_AVAILABILITY"]` | ✅ Aktif |
| `PRODUCT_INFO_GAP` | `EXPLAIN_PRODUCT_DETAIL` | `["PRODUCT_DETAIL"]` | `["PRODUCT_DETAIL"]` | ✅ Aktif |
| `PRICE_FRICTION` | `EXPLAIN_PRICE_PROMO` | `["PRICE_PROMO"]` | `["PRICE_PROMO"]` | ✅ Aktif |
| `SHIPPING_FRICTION` | `EXPLAIN_SHIPPING` | `["SHIPPING"]` | `["SHIPPING"]` | ⏸ Ditunda (fact KB sudah siap) |
| `OBJECTION_SPIKE` | `HANDLE_OBJECTION` | `["FAQ_PLAYBOOK"]` | `["OBJECTION_COMPLAINT"]` | ⏸ Ditunda (fact KB sudah siap) |
| `PURCHASE_MOMENT` | `GUIDE_CHECKOUT` | `["CHECKOUT_GUIDE"]` | `["PURCHASE_INTENT"]` | ⏸ Ditunda (fact KB **belum ada**) |
| `NO_CLEAR_SIGNAL` | `NO_ACTION` | `[]` | — (fallback) | ✅ Aktif |

Tiga state yang ditunda ada di `action_rules.json` key `not_yet_implemented`
(bukan di `audience_states` yang aktif) — sengaja dipisah supaya
`ActionEngine` tidak salah pakai rule yang belum lengkap datasetnya.
Kronologi kenapa ditunda ada di `../DECISIONS_LOG.md`.

## Kebijakan threshold & tie-break

- Sebuah `audience_state` baru dipilih kalau seluruh threshold terpenuhi:
  minimal 2 komentar, minimal 2 pengguna unik, dan confidence gabungan ≥ 0.7.
- Kalau lebih dari satu state lolos threshold di window yang sama:
  urutkan berdasarkan pengguna unik, support, confidence, lalu
  `priority_rank` sebagai tie-break terakhir.
- Hysteresis mempertahankan sinyal aktif selama masih eligible. Challenger
  baru menggantikannya jika memiliki minimal 2 pengguna unik lebih banyak.
- `action_score` adalah confidence agregat dari sinyal terpilih.

## Cara jalankan

```bash
python3 action_engine.py
```

Regression formal dijalankan dari root repository:

```bash
python3 -m unittest -v tests/test_core_regressions.py
```

## Integrasi retrieval

Engine tetap murni deterministik dan tanpa I/O. Selain compatibility field
`required_fact_types`, setiap keputusan menghasilkan `required_fact_query`
berisi topic dan filter slot. Backend menambahkan `product_id` lalu memanggil
`KnowledgeBase.get_facts_by_query(...)`.
