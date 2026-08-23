import type { DemoConfig, HealthResponse } from '@/contracts/livecoach';
import { formatElapsed } from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface AppHeaderProps {
  health: HealthResponse | null;
  config: DemoConfig | null;
  sessionId: string | null;
  elapsedMs: number;
}

const HEALTH_LABELS: Record<HealthResponse['status'], string> = {
  READY: 'Sistem siap',
  DEGRADED: 'Mode terbatas',
  OFFLINE: 'Sistem offline',
};

export default function AppHeader({ health, config, sessionId, elapsedMs }: AppHeaderProps) {
  const healthLabel = health ? HEALTH_LABELS[health.status] : 'Memeriksa sistem';

  return (
    <header className="app-header">
      <div className="brand-lockup">
        <span className="brand-mark"><Icon name="activity" size={16} /></span>
        <span className="brand-name">LiveCoach</span>
        <span className="brand-edition">AI Live Desk</span>
      </div>

      <div className="header-product">
        <span className="product-label">
          Produk aktif&nbsp;·&nbsp; <strong>{config?.product.display_name ?? 'Memuat konfigurasi…'}</strong>
        </span>
      </div>

      <div className="header-meta">
        {sessionId && (
          <span className="session-clock" aria-label={`Waktu replay: ${formatElapsed(elapsedMs)}`}>
            <Icon name="clock" size={13} />
            {formatElapsed(elapsedMs)}
          </span>
        )}
        {config && <span className="model-label" title={config.models.nlp}>{config.models.nlp}</span>}
        <span className="system-status" title={healthLabel}>
          <span className="status-dot" data-status={health?.status} aria-hidden="true" />
          <span>{healthLabel}</span>
        </span>
      </div>
    </header>
  );
}
