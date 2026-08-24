import type { PriorityEvent } from '@/contracts/livecoach';
import { formatConfidence } from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface PriorityAlertProps {
  event: PriorityEvent | null;
}

const SLOT_LABELS: Record<string, string> = {
  requested_size: 'Size',
  requested_color: 'Warna',
  body_weight: 'BB',
  body_height: 'TB',
};

export default function PriorityAlert({ event }: PriorityAlertProps) {
  if (!event) return null;

  const visibleSlots = Object.entries(event.slots).filter(([key]) => key in SLOT_LABELS);

  return (
    <aside className="priority-alert" aria-label="Komentar prioritas" aria-live="polite">
      <span className="priority-alert-icon"><Icon name="alert" size={16} /></span>
      <div className="priority-alert-content">
        <div className="priority-alert-heading">
          <strong>Calon pembeli perlu perhatian</strong>
          <span>{formatConfidence(event.confidence)} · {event.priority_level === 'HIGH' ? 'Prioritas tinggi' : 'Prioritas'}</span>
        </div>
        <p>“{event.text}”</p>
        {visibleSlots.length > 0 && (
          <div className="priority-slots">
            {visibleSlots.map(([key, value]) => (
              <span key={key}>{SLOT_LABELS[key]}: {value}{key === 'body_weight' ? ' kg' : key === 'body_height' ? ' cm' : ''}</span>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
