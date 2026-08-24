import type { HealthResponse } from '@/contracts/livecoach';

export type HealthTone = 'neutral' | 'success' | 'warning' | 'error';

export interface HealthPresentation {
  label: string;
  detail: string;
  tone: HealthTone;
}

/** Ubah health teknis menjadi status yang jujur dan mudah dipahami operator. */
export function describeHealth(health: HealthResponse | null): HealthPresentation {
  if (!health) {
    return {
      label: 'Memeriksa sistem',
      detail: 'Status layanan sedang diperiksa.',
      tone: 'neutral',
    };
  }

  if (health.status === 'OFFLINE' || health.services.api === 'OFFLINE') {
    return {
      label: 'Sistem offline',
      detail: 'Backend tidak dapat dihubungi.',
      tone: 'error',
    };
  }

  if (health.services.nlp_model === 'OFFLINE') {
    return {
      label: 'NLP tidak tersedia',
      detail: 'Analisis komentar belum dapat dijalankan.',
      tone: 'error',
    };
  }

  if (health.services.llm_model === 'UNKNOWN') {
    return {
      label: 'Gemini belum diverifikasi',
      detail: 'Gemini akan diverifikasi saat rekomendasi pertama dibuat.',
      tone: 'neutral',
    };
  }

  if (health.services.llm_model === 'DEGRADED' || health.provider.llm === 'Template Fallback') {
    return {
      label: 'Mode fallback',
      detail: 'Rekomendasi aman tetap tersedia melalui template berbasis Knowledge Base.',
      tone: 'warning',
    };
  }

  if (health.services.nlp_model === 'DEGRADED') {
    return {
      label: 'Mode NLP terbatas',
      detail: 'Analisis berjalan menggunakan heuristic fallback.',
      tone: 'warning',
    };
  }

  return {
    label: 'Sistem siap',
    detail: 'IndoBERT dan Gemini telah terverifikasi.',
    tone: 'success',
  };
}

