/**
 * LiveCoach AI — Zod Runtime Schemas
 * Spesifikasi Bagian 11.1: "Gunakan runtime schema validation (misalnya Zod)
 * pada response agar contract drift terlihat saat development."
 *
 * Setiap schema di sini harus IDENTIK dengan types di livecoach.ts.
 * Jika backend mengubah payload, Zod akan throw ZodError — terdeteksi langsung.
 */

import { z } from 'zod';

// ============================================================
// ENUM SCHEMAS
// ============================================================

export const PipelineStatusSchema = z.enum([
  'WAITING_SIGNAL',
  'CARD_READY',
  'FALLBACK',
  'ERROR',
]);

export const ReadinessSchema = z.enum(['LOW', 'MEDIUM', 'HIGH']);

export const UrgencySchema = z.enum(['NORMAL', 'PRIORITY', 'CRITICAL']);

export const ValidationStatusSchema = z.enum(['PASSED', 'FAILED', 'NOT_RUN']);
export const GenerationProviderSchema = z.enum(['GEMINI', 'TEMPLATE']);

export const AudienceStateSchema = z.enum([
  'PRICE_FRICTION',
  'SIZE_FRICTION',
  'STOCK_FRICTION',
  'PRODUCT_INFO_GAP',
  'SHIPPING_FRICTION',
  'OBJECTION_SPIKE',
  'PURCHASE_MOMENT',
  'NO_CLEAR_SIGNAL',
]);

export const SelectedActionSchema = z.enum([
  'EXPLAIN_PRICE_PROMO',
  'SHOW_SIZE_GUIDE',
  'CONFIRM_STOCK',
  'EXPLAIN_PRODUCT_DETAIL',
  'EXPLAIN_SHIPPING',
  'HANDLE_OBJECTION',
  'GUIDE_CHECKOUT',
  'NO_ACTION',
]);

export const CommentIntentSchema = z.enum([
  'PRICE_PROMO',
  'SIZE_VARIANT',
  'STOCK_AVAILABILITY',
  'PRODUCT_DETAIL',
  'SHIPPING',
  'PURCHASE_INTENT',
  'OBJECTION_COMPLAINT',
  'IRRELEVANT_SPAM',
]);

// ============================================================
// API RESPONSE SCHEMAS
// ============================================================

export const HealthResponseSchema = z.object({
  schema_version: z.literal('health.v1'),
  status: z.enum(['READY', 'DEGRADED', 'OFFLINE']),
  services: z.object({
    api: z.enum(['READY', 'DEGRADED', 'OFFLINE', 'UNKNOWN']),
    nlp_model: z.enum(['READY', 'DEGRADED', 'OFFLINE', 'UNKNOWN']),
    llm_model: z.enum(['READY', 'DEGRADED', 'OFFLINE', 'UNKNOWN']),
  }),
  provider: z.object({
    nlp: z.enum(['IndoBERT', 'Heuristic Fallback']),
    llm: z.enum(['Gemini API', 'Gemini API (unverified)', 'Template Fallback']),
  }),
});

export const DemoConfigSchema = z.object({
  schema_version: z.literal('demo_config.v1'),
  product: z.object({
    product_id: z.string().min(1),
    display_name: z.string().min(1),
  }),
  replay: z.object({
    window_seconds: z.number().positive(),
    speed: z.number().positive(),
  }),
  models: z.object({
    nlp: z.string().min(1),
    llm: z.string().min(1),
  }),
});

export const SessionStartResponseSchema = z.object({
  schema_version: z.literal('session.v1'),
  session_id: z.string().min(1),
  status: z.literal('STARTED'),
});

export const SessionResetResponseSchema = z.object({
  schema_version: z.literal('session.v1'),
  session_id: z.string().min(1),
  status: z.literal('RESET'),
});

export const ApiErrorResponseSchema = z.object({
  schema_version: z.literal('error.v1'),
  error: z.object({
    code: z.enum([
      'MODEL_UNAVAILABLE',
      'SESSION_NOT_FOUND',
      'INVALID_REQUEST',
      'RATE_LIMITED',
      'INTERNAL_ERROR',
    ]),
    message: z.string(),
    retryable: z.boolean(),
    request_id: z.string(),
  }),
});

// ============================================================
// PIPELINE RESULT SCHEMA — Spesifikasi Bagian 11
// ============================================================

export const IntentScoreSchema = z.object({
  intent: CommentIntentSchema,
  score: z.number().min(0).max(1),
});

export const NlpPredictionSchema = z.object({
  schema_version: z.literal('nlp_prediction.v1'),
  model_version: z.string().min(1),
  comment_id: z.string().min(1),
  intents: z.array(IntentScoreSchema),
  readiness: ReadinessSchema,
  urgency: UrgencySchema,
  overall_confidence: z.number().min(0).max(1),
  usable_for_decision: z.boolean(),
});

export const AudienceSnapshotSchema = z.object({
  schema_version: z.literal('audience_snapshot.v1'),
  session_id: z.string().min(1),
  audience_state: AudienceStateSchema,
  window_seconds: z.number().positive(),
  support_count: z.number().int().nonnegative(),
  high_readiness_count: z.number().int().nonnegative(),
  priority_count: z.number().int().nonnegative(),
  evidence_comment_ids: z.array(z.string()),
  state_confidence: z.number().min(0).max(1),
});

export const ActionDecisionSchema = z.object({
  schema_version: z.literal('action_decision.v1'),
  selected_action: SelectedActionSchema,
  audience_state: AudienceStateSchema,
  action_score: z.number().min(0).max(1),
  required_fact_types: z.array(z.string()),
});

export const CoachCardSchema = z.object({
  schema_version: z.literal('coach_card.v1'),
  priority: UrgencySchema,
  situation: z.string().min(1),
  selected_action: SelectedActionSchema,
  reason: z.string().min(1),
  evidence_comment_ids: z.array(z.string()).max(3),
  suggested_response: z.string().min(1),
  confidence: z.number().min(0).max(1),
  validation_status: ValidationStatusSchema,
  generation_provider: GenerationProviderSchema,
  fallback_used: z.boolean(),
  used_fact_ids: z.array(z.string()),
}).superRefine((card, context) => {
  if (card.fallback_used !== (card.generation_provider === 'TEMPLATE')) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['fallback_used'],
      message: 'fallback_used harus konsisten dengan generation_provider',
    });
  }
});

export const SessionCardResponseSchema = z.object({
  session_id: z.string().min(1),
  is_generating: z.boolean(),
  pending_action: SelectedActionSchema.nullable(),
  coach_card: CoachCardSchema.nullable(),
  pipeline_status: PipelineStatusSchema,
  gen_latency: z.number().nonnegative().nullable(),
});

export const PipelineResultSchema = z.object({
  schema_version: z.literal('pipeline_result.v1'),
  session_id: z.string().min(1),
  pipeline_status: PipelineStatusSchema,
  processed_count: z.number().int().nonnegative(),
  nlp_prediction: NlpPredictionSchema,
  audience_snapshot: AudienceSnapshotSchema,
  action_decision: ActionDecisionSchema,
  coach_card: CoachCardSchema.nullable(),
  latency_ms: z
    .object({
      nlp: z.number().optional(),
      generation: z.number().optional(),
      total: z.number(),
    })
    .optional(),
});

// ============================================================
// JSONL ROW SCHEMA — untuk jsonlParser.ts
// ============================================================

export const CommentEntrySchema = z.object({
  comment_id: z.string().min(1, 'comment_id tidak boleh kosong'),
  user_id: z.string().min(1, 'user_id tidak boleh kosong'),
  timestamp_ms: z
    .number()
    .int('timestamp_ms harus integer')
    .nonnegative('timestamp_ms harus >= 0'),
  text: z.string().min(1, 'text tidak boleh kosong'),
});

// ============================================================
// SAFE PARSE HELPERS
// ============================================================

/**
 * Parse dengan Zod dan lempar error yang mudah dibaca.
 * Dipakai di livecoachApi.ts untuk validasi setiap response.
 */
export function parseOrThrow<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  label: string
): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    // Log detail untuk debugging, tapi jangan expose ke UI
    console.error(`[Contract Error] ${label}:`, result.error.flatten());
    throw new Error(
      `Contract mismatch pada ${label}. Cek konsol untuk detail.`
    );
  }
  return result.data;
}

// Export inferred types dari Zod (identik dengan types di livecoach.ts)
// Dipakai untuk type-safe tanpa import ganda
export type HealthResponseZ = z.infer<typeof HealthResponseSchema>;
export type DemoConfigZ = z.infer<typeof DemoConfigSchema>;
export type PipelineResultZ = z.infer<typeof PipelineResultSchema>;
export type CommentEntryZ = z.infer<typeof CommentEntrySchema>;
