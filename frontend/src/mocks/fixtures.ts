/**
 * LiveCoach AI — Mock Fixtures
 * Spesifikasi Bagian 13.3: "Frontend boleh memakai fixture lokal yang
 * mengikuti schema persis."
 *
 * PENTING: Mock mode HARUS dimatikan saat Proof of Work AIC.
 * Gunakan VITE_USE_MOCK=true di .env untuk aktifkan mock.
 * Default selalu false agar demo pakai backend sungguhan.
 */

import type {
  HealthResponse,
  DemoConfig,
  SessionStartResponse,
  PipelineResult,
  ParsedReplayFile,
} from '@/contracts/livecoach';

// ============================================================
// HEALTH & CONFIG
// ============================================================

export const mockHealth: HealthResponse = {
  schema_version: 'health.v1',
  status: 'READY',
  services: {
    api: 'READY',
    nlp_model: 'READY',
    llm_model: 'READY',
  },
  provider: { nlp: 'IndoBERT', llm: 'Gemini API' },
};

export const mockHealthDegraded: HealthResponse = {
  schema_version: 'health.v1',
  status: 'DEGRADED',
  services: {
    api: 'READY',
    nlp_model: 'READY',
    llm_model: 'DEGRADED',
  },
  provider: { nlp: 'IndoBERT', llm: 'Template Fallback' },
};

export const mockDemoConfig: DemoConfig = {
  schema_version: 'demo_config.v1',
  product: {
    product_id: 'TSHIRT-01',
    display_name: 'Essential Cotton T-Shirt',
  },
  replay: {
    window_seconds: 60,
    speed: 1,
  },
  models: {
    nlp: 'indobertweet-livecoach-v1.0',
    llm: 'livecoach-grounded-v1.0',
  },
};

export const mockSessionStart: SessionStartResponse = {
  schema_version: 'session.v1',
  session_id: 'LIVE-DEMO-8F21',
  status: 'STARTED',
};

// ============================================================
// PIPELINE RESULTS — 3 skenario utama
// ============================================================

/** T06: WAITING_SIGNAL — coach_card harus null */
export const mockResultWaiting: PipelineResult = {
  schema_version: 'pipeline_result.v1',
  session_id: 'LIVE-DEMO-8F21',
  pipeline_status: 'WAITING_SIGNAL',
  processed_count: 2,
  nlp_prediction: {
    schema_version: 'nlp_prediction.v1',
    model_version: 'indobertweet-livecoach-v1.0',
    comment_id: 'CMT-002',
    raw_intent: 'product_inquiry',
    normalized_signal: 'PRODUCT_DETAIL',
    slots: { product_attribute: 'material' },
    intents: [
      { intent: 'PRODUCT_DETAIL', score: 0.71 },
      { intent: 'IRRELEVANT', score: 0.14 },
    ],
    readiness: 'LOW',
    urgency: 'NORMAL',
    overall_confidence: 0.71,
    usable_for_decision: true,
  },
  audience_snapshot: {
    schema_version: 'audience_snapshot.v1',
    session_id: 'LIVE-DEMO-8F21',
    audience_state: 'NO_CLEAR_SIGNAL',
    dominant_signal: 'IRRELEVANT',
    window_seconds: 60,
    support_count: 1,
    unique_user_count: 1,
    latest_timestamp_ms: 1724501100000,
    slots_summary: { product_attribute: 'material' },
    high_readiness_count: 0,
    priority_count: 0,
    evidence_comment_ids: ['CMT-002'],
    state_confidence: 0.41,
  },
  action_decision: {
    schema_version: 'action_decision.v1',
    selected_action: 'NO_ACTION',
    selected_signal: 'IRRELEVANT',
    audience_state: 'NO_CLEAR_SIGNAL',
    action_score: 0.0,
    required_fact_types: [],
    required_fact_query: {},
  },
  priority_event: null,
  coach_card: null,  // null = WAITING_SIGNAL
  latency_ms: { nlp: 38, total: 38 },
};

/** T07: CARD_READY — contoh SIZE_FRICTION dari spesifikasi */
export const mockResultCardReady: PipelineResult = {
  schema_version: 'pipeline_result.v1',
  session_id: 'LIVE-DEMO-8F21',
  pipeline_status: 'CARD_READY',
  processed_count: 5,
  nlp_prediction: {
    schema_version: 'nlp_prediction.v1',
    model_version: 'indobertweet-livecoach-v1.0',
    comment_id: 'CMT-005',
    raw_intent: 'size_recommendation',
    normalized_signal: 'SIZE_RECOMMENDATION',
    slots: { body_weight: 55 },
    intents: [
      { intent: 'SIZE_RECOMMENDATION', score: 0.94 },
      { intent: 'PURCHASE_INTENT', score: 0.61 },
    ],
    readiness: 'HIGH',
    urgency: 'PRIORITY',
    overall_confidence: 0.94,
    usable_for_decision: true,
  },
  audience_snapshot: {
    schema_version: 'audience_snapshot.v1',
    session_id: 'LIVE-DEMO-8F21',
    audience_state: 'SIZE_FRICTION',
    dominant_signal: 'SIZE_RECOMMENDATION',
    window_seconds: 60,
    support_count: 4,
    unique_user_count: 3,
    latest_timestamp_ms: 1724501160000,
    slots_summary: { body_weight: 55 },
    high_readiness_count: 2,
    priority_count: 1,
    evidence_comment_ids: ['CMT-003', 'CMT-004', 'CMT-005'],
    state_confidence: 0.88,
  },
  action_decision: {
    schema_version: 'action_decision.v1',
    selected_action: 'SHOW_SIZE_GUIDE',
    selected_signal: 'SIZE_RECOMMENDATION',
    audience_state: 'SIZE_FRICTION',
    action_score: 0.88,
    required_fact_types: ['SIZE_GUIDE'],
    required_fact_query: {
      fact_type: 'SIZE_GUIDE',
      topic: 'size_recommendation',
      product_id: 'TSHIRT-01',
      filters: { body_weight: 55 },
    },
  },
  priority_event: null,
  coach_card: {
    schema_version: 'coach_card.v1',
    priority: 'PRIORITY',
    situation: '4 komentar menanyakan ukuran dalam 60 detik terakhir',
    selected_action: 'SHOW_SIZE_GUIDE',
    reason: '4 pertanyaan ukuran / 60 detik; 2 pembeli siap beli (readiness HIGH)',
    evidence_comment_ids: ['CMT-003', 'CMT-004', 'CMT-005'],
    suggested_response:
      'Untuk BB 55 kg, pilih M agar pas; pilih L agar longgar.',
    confidence: 0.91,
    validation_status: 'PASSED',
    generation_provider: 'GEMINI',
    fallback_used: false,
    used_fact_ids: ['FACT-TS01-SIZE-M', 'FACT-TS01-SIZE-L'],
  },
  latency_ms: { nlp: 42, generation: 318, total: 401 },
};

/** T08: FALLBACK — validasi LLM gagal, pakai safe response */
export const mockResultFallback: PipelineResult = {
  schema_version: 'pipeline_result.v1',
  session_id: 'LIVE-DEMO-8F21',
  pipeline_status: 'FALLBACK',
  processed_count: 7,
  nlp_prediction: {
    schema_version: 'nlp_prediction.v1',
    model_version: 'indobertweet-livecoach-v1.0',
    comment_id: 'CMT-007',
    raw_intent: 'stock_availability',
    normalized_signal: 'STOCK_AVAILABILITY',
    slots: { requested_color: 'hitam', requested_size: 'XL' },
    intents: [
      { intent: 'STOCK_AVAILABILITY', score: 0.87 },
      { intent: 'PURCHASE_INTENT', score: 0.72 },
    ],
    readiness: 'HIGH',
    urgency: 'CRITICAL',
    overall_confidence: 0.87,
    usable_for_decision: true,
  },
  audience_snapshot: {
    schema_version: 'audience_snapshot.v1',
    session_id: 'LIVE-DEMO-8F21',
    audience_state: 'STOCK_FRICTION',
    dominant_signal: 'STOCK_AVAILABILITY',
    window_seconds: 60,
    support_count: 3,
    unique_user_count: 2,
    latest_timestamp_ms: 1724501220000,
    slots_summary: { requested_color: 'hitam' },
    high_readiness_count: 3,
    priority_count: 2,
    evidence_comment_ids: ['CMT-006', 'CMT-007'],
    state_confidence: 0.82,
  },
  action_decision: {
    schema_version: 'action_decision.v1',
    selected_action: 'CONFIRM_STOCK',
    selected_signal: 'STOCK_AVAILABILITY',
    audience_state: 'STOCK_FRICTION',
    action_score: 0.82,
    required_fact_types: ['STOCK'],
    required_fact_query: {
      fact_type: 'STOCK',
      topic: 'stock_availability',
      product_id: 'TSHIRT-01',
      filters: { requested_color: 'hitam', requested_size: 'XL' },
    },
  },
  priority_event: {
    comment_id: 'CMT-006',
    user_id: 'USR-006',
    signal: 'PURCHASE_INTENT',
    confidence: 0.93,
    priority_level: 'HIGH',
    text: 'kalau hitam XL ready aku checkout',
    slots: { requested_color: 'hitam', requested_size: 'XL' },
  },
  coach_card: {
    schema_version: 'coach_card.v1',
    priority: 'CRITICAL',
    situation: 'Penonton menanyakan stok — siap beli tapi belum yakin tersedia',
    selected_action: 'CONFIRM_STOCK',
    reason: '3 pertanyaan stok; semua pembeli readiness HIGH',
    evidence_comment_ids: ['CMT-006', 'CMT-007'],
    // Safe fallback karena respons LLM gagal validasi
    suggested_response:
      'Stok masih tersedia, silakan langsung checkout sekarang.',
    confidence: 0.75,
    validation_status: 'FAILED',
    generation_provider: 'TEMPLATE',
    fallback_used: true,   // Badge FALLBACK harus terlihat jelas
    used_fact_ids: ['FACT-TS01-STOCK'],
  },
  latency_ms: { nlp: 51, generation: 445, total: 531 },
};

/** Low confidence — usable_for_decision: false */
export const mockResultLowConfidence: PipelineResult = {
  ...mockResultWaiting,
  processed_count: 3,
  nlp_prediction: {
    ...mockResultWaiting.nlp_prediction,
    comment_id: 'CMT-003',
    raw_intent: 'not_relevant',
    normalized_signal: 'IRRELEVANT',
    slots: {},
    intents: [
      { intent: 'IRRELEVANT', score: 0.52 },
    ],
    overall_confidence: 0.38,
    usable_for_decision: false,  // Low confidence marker di CommentStream
  },
};

// ============================================================
// FILE FIXTURE — Lampiran A spesifikasi
// ============================================================

/** Fixture .jsonl minimal sesuai Lampiran A spesifikasi */
export const mockParsedFile: ParsedReplayFile = {
  filename: 'comments-demo.jsonl',
  sizeBytes: 412,
  durationMs: 52000,
  errors: [],
  comments: [
    { comment_id: 'CMT-001', user_id: 'USR-001', timestamp_ms: 0,     text: 'halo kak' },
    { comment_id: 'CMT-002', user_id: 'USR-002', timestamp_ms: 5000,  text: 'bahannya apa?' },
    { comment_id: 'CMT-003', user_id: 'USR-003', timestamp_ms: 12000, text: 'bb 55 ambil m atau l?' },
    { comment_id: 'CMT-004', user_id: 'USR-004', timestamp_ms: 18000, text: 'aku 160 cm pilih size apa kak' },
    { comment_id: 'CMT-005', user_id: 'USR-005', timestamp_ms: 24000, text: 'M buat BB berapa?' },
    { comment_id: 'CMT-006', user_id: 'USR-006', timestamp_ms: 30000, text: 'jawab size dong mau checkout' },
    { comment_id: 'CMT-007', user_id: 'USR-007', timestamp_ms: 42000, text: 'yang hitam L masih ada?' },
    { comment_id: 'CMT-008', user_id: 'USR-008', timestamp_ms: 52000, text: 'kalau ada langsung checkout' },
  ],
};

/** File .jsonl demo sebagai string — untuk download/export */
export const mockJsonlContent = `{"comment_id":"CMT-001","user_id":"USR-001","timestamp_ms":0,"text":"halo kak"}
{"comment_id":"CMT-002","user_id":"USR-002","timestamp_ms":5000,"text":"bahannya apa?"}
{"comment_id":"CMT-003","user_id":"USR-003","timestamp_ms":12000,"text":"bb 55 ambil m atau l?"}
{"comment_id":"CMT-004","user_id":"USR-004","timestamp_ms":18000,"text":"aku 160 cm pilih size apa kak"}
{"comment_id":"CMT-005","user_id":"USR-005","timestamp_ms":24000,"text":"M buat BB berapa?"}
{"comment_id":"CMT-006","user_id":"USR-006","timestamp_ms":30000,"text":"jawab size dong mau checkout"}
{"comment_id":"CMT-007","user_id":"USR-007","timestamp_ms":42000,"text":"yang hitam L masih ada?"}
{"comment_id":"CMT-008","user_id":"USR-008","timestamp_ms":52000,"text":"kalau ada langsung checkout"}`;

// ============================================================
// MOCK API — aktif hanya saat VITE_USE_MOCK=true
// ============================================================

/** Urutan hasil mock yang disimulasikan replay */
export const mockResultSequence: PipelineResult[] = [
  mockResultWaiting,           // CMT-001: halo kak
  mockResultWaiting,           // CMT-002: bahannya apa?
  mockResultLowConfidence,     // CMT-003: bb 55 ambil m atau l?
  mockResultWaiting,           // CMT-004: aku 160 cm...
  mockResultCardReady,         // CMT-005: M buat BB berapa? → CARD_READY
  mockResultCardReady,         // CMT-006: jawab size dong
  mockResultFallback,          // CMT-007: yang hitam L → FALLBACK
  mockResultFallback,          // CMT-008: kalau ada langsung checkout
];

/**
 * Cek apakah mock mode aktif.
 * Set VITE_USE_MOCK=true di .env untuk development tanpa backend.
 * WAJIB false saat Proof of Work AIC.
 */
export const isMockMode = (): boolean => {
  return import.meta.env.VITE_USE_MOCK === 'true';
};
