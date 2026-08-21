/**
 * LiveCoach AI — Replay State Machine
 * Spesifikasi Bagian 8: "Jangan mencampur state browser dengan
 * status hasil backend."
 *
 * ReplayUiState  → mengendalikan tombol dan timer (FRONTEND)
 * PipelineStatus → menjelaskan hasil AI komentar terakhir (BACKEND)
 */

import type { ReplayUiState } from '@/contracts/livecoach';

// ============================================================
// TRANSISI VALID
// ============================================================

/**
 * Map transisi yang diizinkan per state.
 * Dipakai untuk guard di useReplayController.
 */
export const VALID_TRANSITIONS: Record<ReplayUiState, ReplayUiState[]> = {
  EMPTY:     ['FILE_READY'],
  FILE_READY: ['EMPTY', 'STARTING'],
  STARTING:  ['RUNNING', 'ERROR'],
  RUNNING:   ['PAUSED', 'FINISHED', 'ERROR'],
  PAUSED:    ['RUNNING', 'FILE_READY', 'ERROR'],   // FILE_READY = setelah reset
  FINISHED:  ['FILE_READY'],                        // FILE_READY = setelah reset
  ERROR:     ['FILE_READY'],                        // FILE_READY = setelah reset/retry
};

export function canTransition(
  from: ReplayUiState,
  to: ReplayUiState,
): boolean {
  return VALID_TRANSITIONS[from].includes(to);
}

// ============================================================
// BUTTON VISIBILITY — Spesifikasi Bagian 7.2
// ============================================================

export interface ButtonVisibility {
  showStart: boolean;
  showPause: boolean;
  showResume: boolean;
  showReset: boolean;
  startDisabled: boolean;
}

/**
 * Tentukan tombol mana yang tampil dan aktif berdasarkan state.
 * isHealthReady: true jika GET /health status === 'READY'
 * isFileValid: true jika file .jsonl lolos validasi
 */
export function getButtonVisibility(
  state: ReplayUiState,
  isHealthReady: boolean,
  isFileValid: boolean,
): ButtonVisibility {
  switch (state) {
    case 'EMPTY':
      return {
        showStart: true,
        showPause: false,
        showResume: false,
        showReset: false,
        startDisabled: true,
      };

    case 'FILE_READY':
      return {
        showStart: true,
        showPause: false,
        showResume: false,
        showReset: false,
        // Start disabled jika health belum Ready atau file belum valid
        startDisabled: !isHealthReady || !isFileValid,
      };

    case 'STARTING':
      return {
        showStart: true,
        showPause: false,
        showResume: false,
        showReset: false,
        startDisabled: true, // Loading
      };

    case 'RUNNING':
      return {
        showStart: false,
        showPause: true,
        showResume: false,
        showReset: true,
        startDisabled: true,
      };

    case 'PAUSED':
      return {
        showStart: false,
        showPause: false,
        showResume: true,
        showReset: true,
        startDisabled: true,
      };

    case 'FINISHED':
      return {
        showStart: false,
        showPause: false,
        showResume: false,
        showReset: true,
        startDisabled: true,
      };

    case 'ERROR':
      return {
        showStart: false,
        showPause: false,
        showResume: false,
        showReset: true,
        startDisabled: true,
      };
  }
}

// ============================================================
// LABEL HELPERS — render enum ke teks Indonesia
// Spesifikasi Bagian 12.2 (Copy utama bahasa Indonesia)
// ============================================================

import type {
  AudienceState,
  SelectedAction,
  CommentIntent,
  Readiness,
  Urgency,
  PipelineStatus,
} from '@/contracts/livecoach';

export const AUDIENCE_STATE_LABELS: Record<AudienceState, string> = {
  PRICE_FRICTION:    'Pertanyaan Harga & Promo',
  SIZE_FRICTION:     'Pertanyaan Ukuran & Varian',
  STOCK_FRICTION:    'Pertanyaan Ketersediaan Stok',
  PRODUCT_INFO_GAP:  'Pertanyaan Detail Produk',
  SHIPPING_FRICTION: 'Pertanyaan Pengiriman',
  OBJECTION_SPIKE:   'Banyak Keberatan',
  PURCHASE_MOMENT:   'Momen Checkout',
  NO_CLEAR_SIGNAL:   'Belum ada pola kuat',
};

export const SELECTED_ACTION_LABELS: Record<SelectedAction, string> = {
  EXPLAIN_PRICE_PROMO:    'Jelaskan Harga & Promo',
  SHOW_SIZE_GUIDE:        'Tampilkan Panduan Ukuran',
  CONFIRM_STOCK:          'Konfirmasi Ketersediaan Stok',
  EXPLAIN_PRODUCT_DETAIL: 'Jelaskan Detail Produk',
  EXPLAIN_SHIPPING:       'Jelaskan Pengiriman',
  HANDLE_OBJECTION:       'Tangani Keberatan',
  GUIDE_CHECKOUT:         'Arahkan ke Checkout',
  NO_ACTION:              'Belum Ada Tindakan',
};

export const INTENT_LABELS: Record<CommentIntent, string> = {
  PRICE_PROMO:          'Harga/Promo',
  SIZE_VARIANT:         'Ukuran/Varian',
  STOCK_AVAILABILITY:   'Stok',
  PRODUCT_DETAIL:       'Detail Produk',
  SHIPPING:             'Pengiriman',
  PURCHASE_INTENT:      'Minat Beli',
  OBJECTION_COMPLAINT:  'Keberatan',
  IRRELEVANT_SPAM:      'Tidak Relevan',
};

export const READINESS_LABELS: Record<Readiness, string> = {
  LOW:    'Belum siap beli',
  MEDIUM: 'Mulai tertarik',
  HIGH:   'Siap beli',
};

export const URGENCY_LABELS: Record<Urgency, string> = {
  NORMAL:   'Normal',
  PRIORITY: 'Prioritas',
  CRITICAL: 'Kritis',
};

export const PIPELINE_STATUS_LABELS: Record<PipelineStatus, string> = {
  WAITING_SIGNAL: 'Belum ada sinyal kuat',
  CARD_READY:     'Rekomendasi siap',
  FALLBACK:       'Respons aman digunakan',
  ERROR:          'Rekomendasi belum dapat dibuat',
};

// ============================================================
// FORMAT HELPERS
// ============================================================

/** Format timestamp_ms ke mm:ss untuk CommentStream */
export function formatTimestamp(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/** Format confidence 0-1 ke "91%" — Spesifikasi Bagian 11.1 */
export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** Format file size ke KB/MB */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Format durasi ms ke "1m 32s" */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}d`;
  return `${minutes}m ${seconds}d`;
}

/** Format elapsed ms ke "mm:ss" untuk replay clock */
export function formatElapsed(ms: number): string {
  return formatTimestamp(ms);
}
