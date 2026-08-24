import type { DemoConfig, HealthResponse } from '@/contracts/livecoach';
import { formatElapsed } from '@/features/replay/replayState';
import Icon from '@/components/Icon';
import { describeHealth } from '@/features/replay/systemHealth';

interface AppHeaderProps {
  health: HealthResponse | null;
  config: DemoConfig | null;
  sessionId: string | null;
  elapsedMs: number;
}

export default function AppHeader({ health, config, sessionId, elapsedMs }: AppHeaderProps) {
  const healthPresentation = describeHealth(health);

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
        <span className="system-status" title={healthPresentation.detail} data-tone={healthPresentation.tone}>
          <span className="status-dot" data-status={health?.status} aria-hidden="true" />
          <span>{healthPresentation.label}</span>
        </span>
      </div>
    </header>
  );
}
