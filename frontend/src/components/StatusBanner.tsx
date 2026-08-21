/**
 * StatusBanner — banner notifikasi error/warning di atas halaman
 * Spesifikasi Bagian 7.6: "Jangan expose stack trace atau raw error ke UI"
 */

interface StatusBannerProps {
  message: string;
  type?: 'error' | 'warning' | 'info';
  onDismiss?: () => void;
  onRetry?: () => void;
  retryLabel?: string;
}

export default function StatusBanner({
  message,
  type = 'error',
  onDismiss,
  onRetry,
  retryLabel = 'Coba Lagi',
}: StatusBannerProps) {
  const styles: Record<string, { bg: string; border: string; color: string; icon: string }> = {
    error:   { bg: 'var(--color-critical-bg)',  border: 'var(--color-critical)',  color: 'var(--color-critical)',  icon: '⚠' },
    warning: { bg: 'var(--color-warning-bg)',   border: 'var(--color-warning)',   color: 'var(--color-warning)',   icon: '⚡' },
    info:    { bg: 'var(--color-info-bg)',       border: 'var(--color-info)',      color: 'var(--color-info)',      icon: 'ℹ' },
  };
  const s = styles[type];

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        padding: 'var(--space-3) var(--space-4)',
        background: s.bg,
        border: `1px solid ${s.border}`,
        borderRadius: 'var(--radius-md)',
        fontSize: 'var(--text-sm)',
        color: s.color,
      }}
    >
      <span aria-hidden="true" style={{ fontSize: '1rem', flexShrink: 0 }}>{s.icon}</span>
      <span style={{ flex: 1, lineHeight: 1.5 }}>{message}</span>

      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '4px 12px',
            background: s.border,
            color: '#fff',
            borderRadius: 'var(--radius-sm)',
            fontSize: 'var(--text-xs)',
            fontWeight: 'var(--weight-medium)',
            flexShrink: 0,
          }}
        >
          {retryLabel}
        </button>
      )}

      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Tutup notifikasi"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 24,
            height: 24,
            borderRadius: 'var(--radius-sm)',
            color: s.color,
            flexShrink: 0,
            fontSize: '1rem',
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
