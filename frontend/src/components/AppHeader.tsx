/**
 * AppHeader — header aplikasi
 * Spesifikasi Bagian 7.1: health status dot + nama model
 */

import type { HealthResponse, DemoConfig } from '@/contracts/livecoach';

interface AppHeaderProps {
  health: HealthResponse | null;
  config: DemoConfig | null;
  sessionId: string | null;
  elapsedMs: number;
}

function HealthDot({ status }: { status: HealthResponse['status'] | undefined }) {
  const color =
    status === 'READY'    ? '#16a34a' :
    status === 'DEGRADED' ? '#d97706' :
    status === 'OFFLINE'  ? '#dc2626' : '#94a3b8';

  const label =
    status === 'READY'    ? 'Sistem siap' :
    status === 'DEGRADED' ? 'Sistem terdegradasi' :
    status === 'OFFLINE'  ? 'Sistem offline' : 'Memeriksa status...';

  return (
    <span
      title={label}
      aria-label={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-1)',
        fontSize: 'var(--text-xs)',
        color: 'var(--color-muted)',
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: color,
          display: 'inline-block',
          flexShrink: 0,
        }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

export default function AppHeader({ health, config, sessionId, elapsedMs }: AppHeaderProps) {
  return (
    <header
      style={{
        height: 'var(--header-height)',
        background: 'var(--color-surface)',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 var(--space-6)',
        gap: 'var(--space-4)',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      {/* Logo + nama */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
        <span style={{ fontSize: '1.25rem' }} aria-hidden="true">🎯</span>
        <span style={{ fontWeight: 'var(--weight-semibold)', color: 'var(--color-ink)', fontSize: 'var(--text-base)' }}>
          LiveCoach AI
        </span>
        <span
          style={{
            fontSize: 'var(--text-xs)',
            background: 'var(--color-info-bg)',
            color: 'var(--color-info)',
            padding: '1px 6px',
            borderRadius: 'var(--radius-full)',
            fontWeight: 'var(--weight-medium)',
          }}
        >
          DEMO
        </span>
      </div>

      {/* Produk */}
      {config && (
        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-muted)', flexShrink: 0 }}>
          {config.product.display_name}
        </span>
      )}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Elapsed clock */}
      {sessionId && (
        <span
          aria-label={`Waktu replay: ${formatElapsed(elapsedMs)}`}
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--text-sm)',
            color: 'var(--color-ink)',
            background: 'var(--color-bg)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            flexShrink: 0,
          }}
        >
          {formatElapsed(elapsedMs)}
        </span>
      )}

      {/* Model info */}
      {config && (
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', flexShrink: 0 }}>
          {config.models.nlp}
        </span>
      )}

      {/* Health dot */}
      <HealthDot status={health?.status} />
    </header>
  );
}
