/**
 * CoachCard — kolom kanan, output utama AI
 * Spesifikasi Bagian 7.5: tiga state tampilan
 *
 * WAITING_SIGNAL → coach_card null, pipeline_status WAITING_SIGNAL
 * CARD_READY     → coach_card ada, fallback_used false
 * FALLBACK       → coach_card ada, fallback_used true (HARUS terlihat jelas)
 *
 * ATURAN:
 * - suggested_response adalah SARAN, bukan auto-kirim
 * - Tombol "Salin" adalah copy teks ke clipboard
 * - Jangan pernah tampilkan suggested_response saat coach_card null
 */

import type { PipelineResult } from '@/contracts/livecoach';
import { SELECTED_ACTION_LABELS, URGENCY_LABELS, formatConfidence } from '@/features/replay/replayState';
import { useState, useCallback } from 'react';

interface CoachCardProps {
  result: PipelineResult | null;
}

const PRIORITY_STYLES = {
  NORMAL: {
    border: 'var(--color-border)',
    headerBg: 'var(--color-bg)',
    badgeBg: 'var(--color-urgency-normal-bg)',
    badgeColor: 'var(--color-urgency-normal)',
    accent: 'var(--color-primary)',
  },
  PRIORITY: {
    border: '#fcd34d',
    headerBg: '#fffbeb',
    badgeBg: 'var(--color-urgency-priority-bg)',
    badgeColor: 'var(--color-urgency-priority)',
    accent: '#d97706',
  },
  CRITICAL: {
    border: '#fca5a5',
    headerBg: '#fff5f5',
    badgeBg: 'var(--color-urgency-critical-bg)',
    badgeColor: 'var(--color-urgency-critical)',
    accent: '#dc2626',
  },
};

export default function CoachCard({ result }: CoachCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback untuk browser yang tidak support clipboard API
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  // --- WAITING_SIGNAL state ---
  if (!result || !result.coach_card || result.pipeline_status === 'WAITING_SIGNAL') {
    return (
      <section
        aria-label="Rekomendasi AI Coach"
        aria-live="polite"
        aria-atomic="true"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-8) var(--space-6)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          minHeight: 240,
          gap: 'var(--space-3)',
        }}
      >
        <span style={{ fontSize: '2.5rem' }} aria-hidden="true">
          {!result ? '⏳' : '📡'}
        </span>
        <p style={{ fontSize: 'var(--text-base)', fontWeight: 'var(--weight-semibold)', color: 'var(--color-ink)' }}>
          {!result ? 'Menunggu replay dimulai' : 'Mengumpulkan sinyal…'}
        </p>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted)', maxWidth: 280 }}>
          {!result
            ? 'Upload file .jsonl dan tekan Mulai Replay'
            : 'Sistem menganalisis pola komentar. Rekomendasi akan muncul saat sinyal cukup kuat.'}
        </p>
        {result && (
          <span style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--color-muted)',
            background: 'var(--color-bg)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--color-border)',
          }}>
            {result.processed_count} komentar dianalisis
          </span>
        )}
      </section>
    );
  }

  // --- CARD_READY atau FALLBACK state ---
  const card = result.coach_card;
  const style = PRIORITY_STYLES[card.priority];
  const isFallback = card.fallback_used;

  return (
    <section
      aria-label="Rekomendasi AI Coach"
      aria-live="polite"
      aria-atomic="true"
      className="animate-fade-in"
      style={{
        background: 'var(--color-surface)',
        border: `2px solid ${style.border}`,
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div style={{
        background: style.headerBg,
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: `1px solid ${style.border}`,
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        flexWrap: 'wrap',
      }}>
        {/* Priority badge */}
        <span
          className="chip"
          style={{
            background: style.badgeBg,
            color: style.badgeColor,
            fontWeight: 'var(--weight-semibold)',
            fontSize: 'var(--text-xs)',
          }}
        >
          {URGENCY_LABELS[card.priority]}
        </span>

        {/* Action label */}
        <span style={{
          fontSize: 'var(--text-sm)',
          fontWeight: 'var(--weight-semibold)',
          color: 'var(--color-ink)',
          flex: 1,
        }}>
          {SELECTED_ACTION_LABELS[card.selected_action]}
        </span>

        {/* Fallback badge — WAJIB terlihat jelas */}
        {isFallback && (
          <span
            className="chip"
            style={{
              background: 'var(--color-warning-bg)',
              color: 'var(--color-warning)',
              fontSize: 'var(--text-xs)',
            }}
            title="Validasi LLM gagal — menggunakan respons aman"
          >
            ⚡ Fallback
          </span>
        )}

        {/* Confidence */}
        <span style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--color-muted)',
          fontFamily: 'var(--font-mono)',
        }}>
          {formatConfidence(card.confidence)}
        </span>
      </div>

      {/* Body */}
      <div style={{ padding: 'var(--space-5)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', flex: 1 }}>

        {/* Situasi */}
        <div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Situasi
          </p>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink)', lineHeight: 1.5 }}>
            {card.situation}
          </p>
        </div>

        {/* Alasan */}
        <div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Sinyal
          </p>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted)', lineHeight: 1.5 }}>
            {card.reason}
          </p>
        </div>

        {/* Divider */}
        <hr className="divider" />

        {/* Suggested response — box utama */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Saran Ucapan Host
            </p>
            {/* Validation badge */}
            <span
              className="chip"
              style={{
                background: card.validation_status === 'PASSED'
                  ? 'var(--color-success-bg)'
                  : card.validation_status === 'FAILED'
                  ? 'var(--color-critical-bg)'
                  : 'var(--color-bg)',
                color: card.validation_status === 'PASSED'
                  ? 'var(--color-success)'
                  : card.validation_status === 'FAILED'
                  ? 'var(--color-critical)'
                  : 'var(--color-muted)',
                fontSize: 'var(--text-xs)',
                border: '1px solid var(--color-border)',
              }}
              title={`Status validasi: ${card.validation_status}`}
            >
              {card.validation_status === 'PASSED' ? '✓ Tervalidasi'
                : card.validation_status === 'FAILED' ? '⚠ Tidak lolos validasi'
                : '— Belum divalidasi'}
            </span>
          </div>

          <div style={{
            background: 'var(--color-bg)',
            border: `1px solid ${isFallback ? '#fcd34d' : style.border}`,
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-4)',
            position: 'relative',
          }}>
            {/* Teks saran — PLAIN TEXT */}
            <p style={{
              fontSize: 'var(--text-base)',
              color: 'var(--color-ink)',
              lineHeight: 1.6,
              fontWeight: 'var(--weight-medium)',
              paddingRight: 'var(--space-8)',
            }}>
              {card.suggested_response}
            </p>

            {/* Tombol salin */}
            <button
              onClick={() => handleCopy(card.suggested_response)}
              aria-label="Salin saran ucapan"
              title="Salin ke clipboard"
              style={{
                position: 'absolute',
                top: 'var(--space-3)',
                right: 'var(--space-3)',
                padding: '4px 8px',
                background: copied ? 'var(--color-success-bg)' : 'var(--color-surface)',
                color: copied ? 'var(--color-success)' : 'var(--color-muted)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--text-xs)',
                transition: 'all var(--transition-fast)',
              }}
            >
              {copied ? '✓ Disalin' : 'Salin'}
            </button>
          </div>

          {/* Disclaimer: ini saran, bukan auto-kirim */}
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginTop: 6, fontStyle: 'italic' }}>
            Ini saran ucapan untuk host — tidak dikirim otomatis
          </p>
        </div>
      </div>
    </section>
  );
}
