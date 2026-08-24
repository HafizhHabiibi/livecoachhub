/**
 * LiveCoach AI — TypeScript Core Contracts
 * Sumber kebenaran: Spesifikasi Bagian 11 dan Lampiran TypeScript Core Contract
 *
 * ATURAN:
 * - Enum dibandingkan secara exact — jangan andalkan label tampilan untuk logika
 * - Confidence API selalu 0-1; UI yang format ke persen
 * - coach_card null berarti WAITING_SIGNAL — jangan ganti dengan object kosong
 * - Field wajib yang hilang harus menghasilkan contract error (via Zod)
 */

// ============================================================
// ENUMS — Spesifikasi Bagian 11 (Registry Enum)
// ============================================================

/** Status pipeline AI untuk komentar terakhir */
export type PipelineStatus =
  | 'WAITING_SIGNAL'  // Sinyal belum cukup, coach_card harus null
  | 'CARD_READY'      // Rekomendasi tersedia dan lolos validasi
  | 'FALLBACK'        // Rekomendasi pakai safe fallback (bukan error)
  | 'ERROR';          // Pipeline gagal, coach_card null

/** Tingkat kesiapan membeli penonton — BUKAN sentimen */
export type Readiness = 'LOW' | 'MEDIUM' | 'HIGH';

/** Kecepatan kebutuhan penanganan komentar */
export type Urgency = 'NORMAL' | 'PRIORITY' | 'CRITICAL';

/** Status validasi respons LLM */
export type ValidationStatus = 'PASSED' | 'FAILED' | 'NOT_RUN';

/** Sumber aktual seller script, terpisah dari hasil validasi. */
export type GenerationProvider = 'GEMINI' | 'TEMPLATE';

/**
 * Ringkasan masalah/peluang dominan pada audiens (rolling 60 detik)
 * Spesifikasi Bagian 4.2
 */
export type AudienceState =
  | 'PRICE_FRICTION'    // Banyak pertanyaan harga/promo
  | 'SIZE_FRICTION'     // Banyak pertanyaan ukuran/varian
  | 'STOCK_FRICTION'    // Pertanyaan ketersediaan stok
  | 'PRODUCT_INFO_GAP'  // Pertanyaan detail produk
  | 'SHIPPING_FRICTION' // Pertanyaan pengiriman
  | 'OBJECTION_SPIKE'   // Banyak komplain/keberatan
  | 'PURCHASE_MOMENT'   // Sinyal kesiapan checkout tinggi
  | 'NO_CLEAR_SIGNAL';  // Belum ada pola dominan

/**
 * Satu tindakan terpilih oleh action engine (deterministik)
 * Spesifikasi Bagian 4.2 — Frontend TIDAK melakukan ranking kedua
 */
export type SelectedAction =
  | 'EXPLAIN_PRICE_PROMO'    // Jelaskan harga/promo
  | 'SHOW_SIZE_GUIDE'        // Tampilkan panduan ukuran
  | 'CONFIRM_STOCK'          // Konfirmasi ketersediaan stok
  | 'EXPLAIN_PRODUCT_DETAIL' // Jelaskan detail produk
  | 'EXPLAIN_SHIPPING'       // Jelaskan pengiriman
  | 'HANDLE_OBJECTION'       // Tangani keberatan
  | 'GUIDE_CHECKOUT'         // Arahkan ke checkout
  | 'NO_ACTION';             // Belum ada aksi; coach_card harus null

/**
 * Intent komentar (multi-label) — Spesifikasi Bagian 4.1
 * Satu komentar bisa punya lebih dari satu intent
 */
export type CommentIntent =
  | 'PRICE_PROMO'
  | 'SIZE_VARIANT'
  | 'STOCK_AVAILABILITY'
  | 'PRODUCT_DETAIL'
  | 'SHIPPING'
  | 'PURCHASE_INTENT'
  | 'OBJECTION_COMPLAINT'
  | 'IRRELEVANT_SPAM';

// ============================================================
// UI STATE — Spesifikasi Bagian 8.1 (ReplayUiState)
// ============================================================

/**
 * State frontend yang mengendalikan tombol dan timer replay.
 * JANGAN campur dengan pipeline_status dari backend.
 */
export type ReplayUiState =
  | 'EMPTY'      // Belum ada file
  | 'FILE_READY' // File valid, siap diputar
  | 'STARTING'   // Menunggu session/start response
  | 'RUNNING'    // Replay berjalan
  | 'PAUSED'     // Replay dijeda
  | 'FINISHED'   // Semua komentar selesai diproses
  | 'ERROR';     // Error fatal (backend offline, dll)

// ============================================================
// JSONL FILE — Spesifikasi Bagian 9
// ============================================================

/** Satu baris dalam file replay .jsonl */
export interface CommentEntry {
  comment_id: string;    // Unique per file; duplikat = error validasi
  user_id: string;       // Identitas anonim; wajib konsisten antar komentar user yang sama
  timestamp_ms: number;  // Integer ms dari awal sesi; harus ascending
  text: string;          // Render sebagai plain text — JANGAN sebagai HTML
}

/** Hasil parsing file .jsonl — dipakai di ReplayInputPanel */
export interface ParsedReplayFile {
  filename: string;
  sizeBytes: number;
  comments: CommentEntry[];
  durationMs: number;         // timestamp_ms komentar terakhir
  errors: ParseError[];       // Kosong = file valid
}

export interface ParseError {
  line: number;
  message: string;
}

// ============================================================
// API PAYLOADS — Spesifikasi Bagian 10
// ============================================================

/** GET /health — Spesifikasi 10.1 */
export interface HealthResponse {
  schema_version: 'health.v1';
  status: 'READY' | 'DEGRADED' | 'OFFLINE';
  services: {
    api: 'READY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
    nlp_model: 'READY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
    llm_model: 'READY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
  };
  provider: {
    nlp: 'IndoBERT' | 'Heuristic Fallback';
    llm: 'Gemini API' | 'Gemini API (unverified)' | 'Template Fallback';
  };
}

/** GET /api/v1/demo-config — Spesifikasi 10.2 */
export interface DemoConfig {
  schema_version: 'demo_config.v1';
  product: {
    product_id: string;
    display_name: string;
  };
  replay: {
    window_seconds: number;  // Default 60
    speed: number;           // Default 1 (MVP selalu 1x)
  };
  models: {
    nlp: string;   // Contoh: 'indobertweet-livecoach-v1.0'
    llm: string;   // Contoh: 'livecoach-grounded-v1.0'
  };
}

/** POST /api/v1/session/start request */
export interface SessionStartRequest {
  product_id: string;
}

/** POST /api/v1/session/start response — Spesifikasi 10.3 */
export interface SessionStartResponse {
  schema_version: 'session.v1';
  session_id: string;
  status: 'STARTED';
}

/** POST /api/v1/comments/analyze request — Spesifikasi 10.4 */
export interface CommentAnalyzeRequest {
  session_id: string;
  comment_id: string;
  user_id: string;
  timestamp_ms: number;
  text: string;
}

/** POST /api/v1/session/reset request */
export interface SessionResetRequest {
  session_id: string;
}

/** POST /api/v1/session/reset response */
export interface SessionResetResponse {
  schema_version: 'session.v1';
  session_id: string;
  status: 'RESET';
}

/** GET /api/v1/session/card response */
export interface SessionCardResponse {
  session_id: string;
  is_generating: boolean;
  pending_action: SelectedAction | null;
  coach_card: CoachCard | null;
  pipeline_status: PipelineStatus;
  gen_latency: number | null;
}

/** Error response dari backend — Spesifikasi 10.6 */
export interface ApiErrorResponse {
  schema_version: 'error.v1';
  error: {
    code: ApiErrorCode;
    message: string;
    retryable: boolean;
    request_id: string;
  };
}

export type ApiErrorCode =
  | 'MODEL_UNAVAILABLE'
  | 'SESSION_NOT_FOUND'
  | 'INVALID_REQUEST'
  | 'RATE_LIMITED'
  | 'INTERNAL_ERROR';

// ============================================================
// PIPELINE RESULT — Spesifikasi Bagian 11 (Core Contract)
// ============================================================

/** Hasil analisis NLP per komentar — Spesifikasi Bagian 4.1 */
export interface NlpPrediction {
  schema_version: 'nlp_prediction.v1';
  model_version: string;
  comment_id: string;
  intents: IntentScore[];          // Multi-label; tampilkan 2-3 tertinggi
  readiness: Readiness;
  urgency: Urgency;
  overall_confidence: number;      // 0-1
  usable_for_decision: boolean;    // false = Low confidence marker
}

export interface IntentScore {
  intent: CommentIntent;
  score: number;  // 0-1; gunakan untuk urutan chip
}

/** State agregat 60 detik — Spesifikasi Bagian 4.2 dan 7.4 */
export interface AudienceSnapshot {
  schema_version: 'audience_snapshot.v1';
  session_id: string;
  audience_state: AudienceState;
  window_seconds: number;          // Selalu 60 pada MVP
  support_count: number;           // Jumlah komentar mendukung state
  high_readiness_count: number;
  priority_count: number;          // Komentar PRIORITY atau CRITICAL
  evidence_comment_ids: string[];  // IDs yang dipakai sebagai bukti
  state_confidence: number;        // 0-1
}

/** Keputusan action engine — Spesifikasi Bagian 4.2 */
export interface ActionDecision {
  schema_version: 'action_decision.v1';
  selected_action: SelectedAction;
  audience_state: AudienceState;
  action_score: number;            // 0-1; tampilkan di DecisionDetails
  required_fact_types: string[];   // Contoh: ['SIZE_GUIDE']
}

/** Output Coach Card — Spesifikasi Bagian 7.5 */
export interface CoachCard {
  schema_version: 'coach_card.v1';
  priority: Urgency;               // Badge NORMAL/PRIORITY/CRITICAL
  situation: string;               // Ringkasan audience state dalam bahasa manusia
  selected_action: SelectedAction;
  reason: string;                  // Sinyal terukur, mis. "4 pertanyaan ukuran / 60 detik"
  evidence_comment_ids: string[];  // Maksimal 3 comment IDs
  suggested_response: string;      // Hasil LLM atau safe fallback — SARAN, bukan auto-kirim
  confidence: number;              // 0-1
  validation_status: ValidationStatus;
  generation_provider: GenerationProvider;
  fallback_used: boolean;          // Harus terlihat jelas di UI jika true
  used_fact_ids: string[];
}

/**
 * Hasil lengkap pipeline per komentar — Spesifikasi Bagian 11
 * Ini yang dikembalikan POST /api/v1/comments/analyze
 */
export interface PipelineResult {
  schema_version: 'pipeline_result.v1';
  session_id: string;
  pipeline_status: PipelineStatus;
  processed_count: number;
  nlp_prediction: NlpPrediction;
  audience_snapshot: AudienceSnapshot;
  action_decision: ActionDecision;
  coach_card: CoachCard | null;   // null ketika WAITING_SIGNAL atau ERROR
  latency_ms?: {
    nlp?: number;
    generation?: number;
    total: number;
  };
}

// ============================================================
// HELPER TYPES
// ============================================================

/** Komentar yang sudah diproses backend — dipakai di CommentStream */
export interface ProcessedComment {
  entry: CommentEntry;
  nlp: NlpPrediction;
  receivedAt: number;  // Date.now() saat response diterima
}

/** State global yang dibawa useReplayController */
export interface ReplayState {
  uiState: ReplayUiState;
  sessionId: string | null;
  file: ParsedReplayFile | null;
  processedComments: ProcessedComment[];  // Max 5 terbaru untuk stream
  currentIndex: number;
  latestResult: PipelineResult | null;
  errorMessage: string | null;
  config: DemoConfig | null;
  health: HealthResponse | null;
}
