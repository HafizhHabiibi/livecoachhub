import type { AudienceSnapshot as AudienceSnapshotType } from '@/contracts/livecoach';
import { AUDIENCE_STATE_LABELS, formatConfidence } from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface AudienceSnapshotProps {
  snapshot: AudienceSnapshotType | null;
}

export default function AudienceSnapshot({ snapshot }: AudienceSnapshotProps) {
  return (
    <section className="signal-strip" aria-label="Sinyal audiens 60 detik">
      {!snapshot ? (
        <div className="signal-empty">
          <span className="signal-empty-icon"><Icon name="signal" size={16} /></span>
          <span>
            <strong>Belum ada sinyal audiens</strong>
            <span>Distribusi akan terbentuk setelah komentar mulai dianalisis.</span>
          </span>
        </div>
      ) : (
        <div className="signal-content">
          <div className="dominant-signal">
            <div className="signal-title"><Icon name="signal" size={13} />Pola dominan · {snapshot.window_seconds} detik</div>
            <p className="signal-name">{AUDIENCE_STATE_LABELS[snapshot.audience_state]}</p>
            <div className="confidence-line" aria-label={`Keyakinan pola ${formatConfidence(snapshot.state_confidence)}`}>
              <span className="confidence-track" aria-hidden="true"><span style={{ width: `${Math.round(snapshot.state_confidence * 100)}%` }} /></span>
              <span className="confidence-value">{formatConfidence(snapshot.state_confidence)} yakin</span>
            </div>
          </div>
          <SignalStat value={snapshot.support_count} label="Komentar relevan" />
          <SignalStat value={snapshot.unique_user_count} label="Pengguna unik" />
          <SignalStat value={snapshot.high_readiness_count} label="Siap membeli" tone="positive" />
          <SignalStat value={snapshot.priority_count} label="Perlu perhatian" tone="attention" />
        </div>
      )}
    </section>
  );
}

function SignalStat({ value, label, tone = 'default' }: { value: number; label: string; tone?: 'default' | 'positive' | 'attention' }) {
  return (
    <div className="signal-stat" data-tone={tone}>
      <p className="signal-stat-value">{value}</p>
      <p className="signal-stat-label">{label}</p>
    </div>
  );
}
