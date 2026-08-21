/**
 * LiveCoach AI — API Service
 * Spesifikasi Bagian 10: semua 5 endpoint
 *
 * Endpoint:
 *   GET  /health
 *   GET  /api/v1/demo-config
 *   POST /api/v1/session/start
 *   POST /api/v1/comments/analyze
 *   POST /api/v1/session/reset
 *
 * ATURAN:
 * - Semua response divalidasi Zod via parseOrThrow()
 * - Jangan expose stack trace atau raw error ke UI
 * - Error code dipetakan ke pesan ramah pengguna
 * - Timeout default 15 detik untuk /comments/analyze
 */

import type {
  HealthResponse,
  DemoConfig,
  SessionStartResponse,
  SessionStartRequest,
  CommentAnalyzeRequest,
  PipelineResult,
  SessionResetRequest,
  SessionResetResponse,
  ApiErrorCode,
} from '@/contracts/livecoach';

import {
  HealthResponseSchema,
  DemoConfigSchema,
  SessionStartResponseSchema,
  PipelineResultSchema,
  SessionResetResponseSchema,
  ApiErrorResponseSchema,
  parseOrThrow,
} from '@/contracts/livecoachSchemas';

import {
  isMockMode,
  mockHealth,
  mockDemoConfig,
  mockSessionStart,
  mockResultSequence,
} from '@/mocks/fixtures';

// ============================================================
// CONFIG
// ============================================================

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const ANALYZE_TIMEOUT_MS = 15_000; // 15 detik — Spesifikasi Bagian 12

// Counter untuk mock sequence
let mockSequenceIndex = 0;

// ============================================================
// ERROR TYPES
// ============================================================

export class ApiError extends Error {
  constructor(
    public readonly code: ApiErrorCode | 'NETWORK_ERROR' | 'TIMEOUT' | 'CONTRACT_ERROR',
    public readonly userMessage: string,
    public readonly retryable: boolean,
    public readonly requestId?: string,
  ) {
    super(userMessage);
    this.name = 'ApiError';
  }
}

/** Petakan error.code backend ke pesan ramah pengguna Indonesia */
function mapErrorCode(
  code: ApiErrorCode,
  retryable: boolean,
  requestId: string,
): ApiError {
  const messages: Record<ApiErrorCode, string> = {
    MODEL_UNAVAILABLE: 'Model AI belum siap. Coba beberapa saat lagi.',
    SESSION_NOT_FOUND: 'Sesi tidak ditemukan. Silakan reset dan mulai ulang.',
    INVALID_REQUEST: 'Data komentar tidak valid.',
    RATE_LIMITED: 'Terlalu banyak permintaan. Tunggu sebentar.',
    INTERNAL_ERROR: 'Terjadi kesalahan internal. Coba ulangi.',
  };
  return new ApiError(code, messages[code], retryable, requestId);
}

// ============================================================
// FETCH HELPER
// ============================================================

interface FetchOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  timeoutMs?: number;
}

async function apiFetch<T>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { method = 'GET', body, timeoutMs } = options;

  // Abort controller untuk timeout
  const controller = new AbortController();
  const timerId = timeoutMs
    ? setTimeout(() => controller.abort(), timeoutMs)
    : null;

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    if (timerId) clearTimeout(timerId);

    // Cek apakah response adalah error dari backend
    if (!response.ok) {
      let errorData: unknown;
      try {
        errorData = await response.json();
      } catch {
        throw new ApiError(
          'INTERNAL_ERROR',
          'Service analisis belum dapat dihubungi.',
          true,
        );
      }

      // Coba parse sebagai ApiErrorResponse
      const parsed = ApiErrorResponseSchema.safeParse(errorData);
      if (parsed.success) {
        const { code, retryable, request_id } = parsed.data.error;
        throw mapErrorCode(code, retryable, request_id);
      }

      throw new ApiError(
        'INTERNAL_ERROR',
        'Terjadi kesalahan yang tidak diketahui.',
        true,
      );
    }

    const data = await response.json();
    return data as T;
  } catch (err) {
    if (timerId) clearTimeout(timerId);

    // Re-throw ApiError langsung
    if (err instanceof ApiError) throw err;

    // Timeout (AbortError)
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(
        'TIMEOUT',
        'Analisis terlalu lama. Replay dijeda agar komentar tidak terlewat.',
        true, // retryable — kirim comment_id yang sama
      );
    }

    // Network error (fetch gagal sama sekali)
    throw new ApiError(
      'NETWORK_ERROR',
      'Service analisis belum dapat dihubungi.',
      true,
    );
  }
}

// ============================================================
// MOCK HELPERS
// ============================================================

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function nextMockResult(): PipelineResult {
  const result = mockResultSequence[mockSequenceIndex % mockResultSequence.length];
  mockSequenceIndex++;
  return result;
}

export function resetMockSequence(): void {
  mockSequenceIndex = 0;
}

// ============================================================
// API FUNCTIONS
// ============================================================

/**
 * GET /health
 * Spesifikasi Bagian 10.1 + 7.1
 * Dipanggil saat halaman /demo dibuka dan sebelum Start diaktifkan.
 */
export async function getHealth(): Promise<HealthResponse> {
  if (isMockMode()) {
    await delay(300);
    return mockHealth;
  }

  const raw = await apiFetch<unknown>('/health');
  return parseOrThrow(HealthResponseSchema, raw, 'GET /health');
}

/**
 * GET /api/v1/demo-config
 * Spesifikasi Bagian 10.2
 * Dipanggil sekali saat load untuk mendapat product_id, model versions, dll.
 */
export async function getDemoConfig(): Promise<DemoConfig> {
  if (isMockMode()) {
    await delay(200);
    return mockDemoConfig;
  }

  const raw = await apiFetch<unknown>('/api/v1/demo-config');
  return parseOrThrow(DemoConfigSchema, raw, 'GET /api/v1/demo-config');
}

/**
 * POST /api/v1/session/start
 * Spesifikasi Bagian 10.3
 * Dipanggil SEKALI saat tombol Start ditekan.
 * Session dibuat satu kali per replay — jangan panggil ulang saat resume.
 */
export async function startSession(
  req: SessionStartRequest,
): Promise<SessionStartResponse> {
  if (isMockMode()) {
    await delay(400);
    resetMockSequence();
    return { ...mockSessionStart, session_id: `LIVE-DEMO-${Date.now()}` };
  }

  const raw = await apiFetch<unknown>('/api/v1/session/start', {
    method: 'POST',
    body: req,
  });
  return parseOrThrow(SessionStartResponseSchema, raw, 'POST /api/v1/session/start');
}

/**
 * POST /api/v1/comments/analyze
 * Spesifikasi Bagian 10.4 + Bagian 3.2
 *
 * ATURAN KRITIS:
 * - Hanya satu request aktif per sesi
 * - Komentar berikutnya baru dikirim SETELAH response diterima
 * - Timeout 15 detik → pause + retry comment_id yang sama
 * - Late response (session_id berbeda) diabaikan di useReplayController
 */
export async function analyzeComment(
  req: CommentAnalyzeRequest,
): Promise<PipelineResult> {
  if (isMockMode()) {
    // Simulasi latency backend
    await delay(400 + Math.random() * 300);
    const result = nextMockResult();
    // Pastikan session_id dan comment_id sesuai request
    return {
      ...result,
      session_id: req.session_id,
      nlp_prediction: {
        ...result.nlp_prediction,
        comment_id: req.comment_id,
      },
    };
  }

  const raw = await apiFetch<unknown>('/api/v1/comments/analyze', {
    method: 'POST',
    body: req,
    timeoutMs: ANALYZE_TIMEOUT_MS,
  });
  return parseOrThrow(PipelineResultSchema, raw, 'POST /api/v1/comments/analyze');
}

/**
 * POST /api/v1/session/reset
 * Spesifikasi Bagian 10.5
 * Dipanggil saat tombol Reset ditekan.
 * Membersihkan state backend; UI juga harus reset ke FILE_READY.
 */
export async function resetSession(
  req: SessionResetRequest,
): Promise<SessionResetResponse> {
  if (isMockMode()) {
    await delay(200);
    resetMockSequence();
    return {
      schema_version: 'session.v1',
      session_id: req.session_id,
      status: 'RESET',
    };
  }

  const raw = await apiFetch<unknown>('/api/v1/session/reset', {
    method: 'POST',
    body: req,
  });
  return parseOrThrow(SessionResetResponseSchema, raw, 'POST /api/v1/session/reset');
}
