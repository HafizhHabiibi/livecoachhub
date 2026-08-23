import Icon from '@/components/Icon';

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
  retryLabel = 'Coba lagi',
}: StatusBannerProps) {
  return (
    <div className="status-banner" data-type={type} role="alert" aria-live="assertive">
      <Icon name={type === 'info' ? 'info' : 'alert'} size={16} />
      <span>{message}</span>
      <span className="banner-actions">
        {onRetry && <button type="button" className="banner-button" onClick={onRetry}>{retryLabel}</button>}
        {onDismiss && (
          <button type="button" className="banner-button banner-close" onClick={onDismiss} aria-label="Tutup notifikasi">
            <Icon name="x" size={14} />
          </button>
        )}
      </span>
    </div>
  );
}
