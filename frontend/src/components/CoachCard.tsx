import { useCallback, useState } from 'react';
import type { PipelineResult } from '@/contracts/livecoach';
import { SELECTED_ACTION_LABELS, URGENCY_LABELS, formatConfidence } from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface CoachCardProps {
  result: PipelineResult | null;
}

export default function CoachCard({ result }: CoachCardProps) {
  const [copied, setCopied] = useState(false);

  const copyScript = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }, []);

  if (!result || !result.coach_card || result.pipeline_status === 'WAITING_SIGNAL') {
    const hasResult = result !== null;
    return (
      <section className="module coach-module coach-waiting" aria-label="Arahan host" aria-live="polite">
        <div>
          <span className="waiting-visual"><Icon name={hasResult ? 'signal' : 'activity'} size={23} /></span>
          <h2>{hasResult ? 'Membaca pola audiens' : 'Arahan host belum aktif'}</h2>
          <p>
            {hasResult
              ? 'Analisis berjalan. Arahan akan muncul ketika pola komentar cukup kuat untuk mendukung satu tindakan.'
              : 'Muat replay dan mulai sesi. LiveCoach akan menempatkan tindakan paling relevan di area ini.'}
          </p>
          {hasResult && <span className="waiting-count">{result.processed_count} komentar dianalisis</span>}
        </div>
      </section>
    );
  }

  const card = result.coach_card;
  const validationLabel = card.validation_status === 'PASSED'
    ? 'Tervalidasi fakta'
    : card.validation_status === 'FAILED'
      ? 'Respons aman · validasi gagal'
      : 'Belum divalidasi';

  return (
    <section
      key={`${result.processed_count}-${card.selected_action}`}
      className="module coach-module animate-row-enter"
      data-priority={card.priority}
      aria-label="Arahan host"
      aria-live="polite"
      aria-atomic="true"
    >
      <header className="coach-header">
        <div className="coach-header-main">
          <p className="coach-eyebrow">Tindakan sekarang</p>
          <p className="coach-action-label">{SELECTED_ACTION_LABELS[card.selected_action]}</p>
        </div>
        <div className="coach-confidence">
          {card.fallback_used && <span className="fallback-label">Fallback</span>}
          <span className="priority-label">{URGENCY_LABELS[card.priority]}</span>
          <span aria-label={`Confidence ${formatConfidence(card.confidence)}`}>{formatConfidence(card.confidence)}</span>
        </div>
      </header>

      <div className="coach-body">
        <p className="coach-situation">{card.situation}</p>
        <p className="coach-reason">Sinyal pendukung: {card.reason}</p>

        <hr className="coach-divider" />

        <div className="script-label-row">
          <p className="script-label">Ucapkan ke audiens</p>
          <span className="validation-label" data-status={card.validation_status}>
            {card.generation_provider === 'GEMINI' ? 'Gemini' : 'Template'} · {validationLabel}
          </span>
        </div>
        <div className="host-script">
          <p>{card.suggested_response}</p>
          <button
            type="button"
            className="copy-button"
            data-copied={copied}
            onClick={() => void copyScript(card.suggested_response)}
            aria-label={copied ? 'Saran ucapan disalin' : 'Salin saran ucapan'}
            title={copied ? 'Disalin' : 'Salin ke clipboard'}
          >
            <Icon name={copied ? 'check' : 'copy'} size={14} />
          </button>
        </div>
        <p className="script-note">Saran untuk dibacakan host · tidak pernah dikirim otomatis</p>
      </div>
    </section>
  );
}
