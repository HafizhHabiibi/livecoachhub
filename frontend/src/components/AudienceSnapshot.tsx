/**
 * AudienceSnapshot — kolom tengah bawah
 * Spesifikasi Bagian 7.4: agregat 60 detik dari backend
 */

import type { AudienceSnapshot as AudienceSnapshotType } from '@/contracts/livecoach';
import { AUDIENCE_STATE_LABELS, formatConfidence } from '@/features/replay/replayState';

interface AudienceSnapshotProps {
  snapshot: AudienceSnapshotType | null;
}

export default function AudienceSnapshot({ snapshot }: AudienceSnapshotProps) {
  return (
    <section
      aria-label="Snapshot audiens 60 detik"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
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
          Snapshot Audiens
        </h2>
        {snapshot && (
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
            {snapshot.window_seconds}d terakhir
          </span>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: 'var(--space-4)' }}>
        {!snapshot ? (
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted)', textAlign: 'center' }}>
            Menunggu data audiens…
          </p>
        ) : (
          <>
            {/* State utama */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginBottom: 4 }}>
                Pola Dominan
              </p>
              <p style={{ fontSize: 'var(--text-base)', fontWeight: 'var(--weight-semibold)', color: 'var(--color-ink)', marginBottom: 4 }}>
                {AUDIENCE_STATE_LABELS[snapshot.audience_state]}
              </p>

              {/* Confidence bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <div style={{
                  flex: 1,
                  height: 6,
                  background: 'var(--color-border)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${Math.round(snapshot.state_confidence * 100)}%`,
                    height: '100%',
                    background: 'var(--color-primary)',
                    borderRadius: 'var(--radius-full)',
                    transition: 'width var(--transition-normal)',
                  }} />
                </div>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', flexShrink: 0 }}>
                  {formatConfidence(snapshot.state_confidence)}
                </span>
              </div>
            </div>

            {/* Statistik */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 'var(--space-2)',
            }}>
              <Stat label="Komentar relevan" value={snapshot.support_count} />
              <Stat label="Siap beli" value={snapshot.high_readiness_count} highlight />
              <Stat label="Prioritas" value={snapshot.priority_count} />
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function Stat({ label, value, highlight = false }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div style={{
      background: 'var(--color-bg)',
      borderRadius: 'var(--radius-sm)',
      padding: 'var(--space-2) var(--space-3)',
      textAlign: 'center',
      border: '1px solid var(--color-border)',
    }}>
      <p style={{
        fontSize: 'var(--text-xl)',
        fontWeight: 'var(--weight-bold)',
        color: highlight ? 'var(--color-primary)' : 'var(--color-ink)',
        lineHeight: 1.2,
      }}>
        {value}
      </p>
      <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginTop: 2 }}>
        {label}
      </p>
    </div>
  );
}
