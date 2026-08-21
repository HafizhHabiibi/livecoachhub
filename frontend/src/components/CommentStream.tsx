/**
 * CommentStream — kolom tengah atas
 * Spesifikasi Bagian 7.3: 5 komentar terbaru, intent chips dari backend
 * ATURAN: render text sebagai plain text, JANGAN innerHTML
 */

import type { ProcessedComment } from '@/contracts/livecoach';
import { INTENT_LABELS, READINESS_LABELS, URGENCY_LABELS, formatTimestamp } from '@/features/replay/replayState';

interface CommentStreamProps {
  comments: ProcessedComment[];
}

const URGENCY_COLORS = {
  NORMAL:   { bg: 'var(--color-urgency-normal-bg)',   text: 'var(--color-urgency-normal)' },
  PRIORITY: { bg: 'var(--color-urgency-priority-bg)', text: 'var(--color-urgency-priority)' },
  CRITICAL: { bg: 'var(--color-urgency-critical-bg)', text: 'var(--color-urgency-critical)' },
};

const READINESS_COLORS = {
  LOW:    { bg: 'var(--color-readiness-low-bg)',    text: 'var(--color-readiness-low)' },
  MEDIUM: { bg: 'var(--color-readiness-medium-bg)', text: 'var(--color-readiness-medium)' },
  HIGH:   { bg: 'var(--color-readiness-high-bg)',   text: 'var(--color-readiness-high)' },
};

export default function CommentStream({ comments }: CommentStreamProps) {
  // Tampilkan terbaru di atas
  const reversed = [...comments].reverse();

  return (
    <section
      aria-label="Komentar terbaru"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div style={{
        padding: 'var(--space-3) var(--space-4)',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <h2 style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)', color: 'var(--color-ink)' }}>
          Komentar Terbaru
        </h2>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
          {comments.length > 0 ? `${comments.length} ditampilkan` : 'Menunggu replay…'}
        </span>
      </div>

      {/* Comment list */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {reversed.length === 0 ? (
          <div style={{
            padding: 'var(--space-8) var(--space-4)',
            textAlign: 'center',
            color: 'var(--color-muted)',
            fontSize: 'var(--text-sm)',
          }}>
            Komentar akan muncul di sini saat replay berjalan
          </div>
        ) : (
          reversed.map((c, i) => {
            const nlp = c.nlp;
            const isNewest = i === 0;
            const urgencyStyle = URGENCY_COLORS[nlp.urgency];
            const readinessStyle = READINESS_COLORS[nlp.readiness];

            // Ambil 2 intent tertinggi
            const topIntents = [...nlp.intents]
              .sort((a, b) => b.score - a.score)
              .slice(0, 2);

            return (
              <article
                key={c.entry.comment_id}
                className={isNewest ? 'animate-slide-in' : undefined}
                style={{
                  padding: 'var(--space-3) var(--space-4)',
                  borderBottom: '1px solid var(--color-border)',
                  background: isNewest ? 'var(--color-bg)' : 'var(--color-surface)',
                  opacity: isNewest ? 1 : 0.8,
                }}
              >
                {/* Baris atas: timestamp + urgency badge */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
                    {formatTimestamp(c.entry.timestamp_ms)}
                  </span>

                  <span
                    style={{
                      fontSize: 'var(--text-xs)',
                      fontWeight: 'var(--weight-medium)',
                      padding: '1px 6px',
                      borderRadius: 'var(--radius-full)',
                      background: urgencyStyle.bg,
                      color: urgencyStyle.text,
                    }}
                  >
                    {URGENCY_LABELS[nlp.urgency]}
                  </span>

                  {/* Low confidence marker */}
                  {!nlp.usable_for_decision && (
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }} title="Confidence rendah">
                      ≈
                    </span>
                  )}
                </div>

                {/* Teks komentar — plain text, JANGAN dangerouslySetInnerHTML */}
                <p style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--color-ink)',
                  marginBottom: 6,
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                }}>
                  {c.entry.text}
                </p>

                {/* Intent chips */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {topIntents.map((intent) => (
                    <span
                      key={intent.intent}
                      className="chip"
                      style={{
                        background: 'var(--color-info-bg)',
                        color: 'var(--color-info)',
                        fontSize: 'var(--text-xs)',
                      }}
                      title={`Confidence: ${Math.round(intent.score * 100)}%`}
                    >
                      {INTENT_LABELS[intent.intent]}
                    </span>
                  ))}

                  {/* Readiness badge */}
                  <span
                    className="chip"
                    style={{
                      background: readinessStyle.bg,
                      color: readinessStyle.text,
                      fontSize: 'var(--text-xs)',
                      marginLeft: 'auto',
                    }}
                    title={READINESS_LABELS[nlp.readiness]}
                  >
                    {READINESS_LABELS[nlp.readiness]}
                  </span>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
