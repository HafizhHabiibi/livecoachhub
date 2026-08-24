import { useState } from 'react';
import type { PipelineResult } from '@/contracts/livecoach';
import {
  AUDIENCE_STATE_LABELS,
  INTENT_LABELS,
  PIPELINE_STATUS_LABELS,
  SELECTED_ACTION_LABELS,
  formatConfidence,
} from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface DecisionDetailsProps {
  result: PipelineResult | null;
}

export default function DecisionDetails({ result }: DecisionDetailsProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="pipeline-details" aria-label="Detail pipeline">
      <button type="button" className="details-toggle" onClick={() => setIsOpen((open) => !open)} aria-expanded={isOpen}>
        <span>Detail keputusan</span>
        <span className="details-toggle-meta">
          {result ? PIPELINE_STATUS_LABELS[result.pipeline_status] : 'Belum ada data'}
          <Icon name="chevron" size={14} />
        </span>
      </button>

      {isOpen && (
        <div className="details-content">
          {!result ? (
            <p className="detail-empty">Pipeline belum menerima komentar untuk dianalisis.</p>
          ) : (
            <>
              <DetailBlock title="Pipeline">
                <Row label="Status" value={PIPELINE_STATUS_LABELS[result.pipeline_status]} />
                <Row label="Diproses" value={`${result.processed_count} komentar`} />
                {result.latency_ms && <Row label="Total" value={`${result.latency_ms.total}ms`} mono />}
                {result.latency_ms?.nlp !== undefined && <Row label="NLP" value={`${result.latency_ms.nlp}ms`} mono />}
                {result.latency_ms?.generation !== undefined && <Row label="Generasi" value={`${result.latency_ms.generation}ms`} mono />}
              </DetailBlock>

              <DetailBlock title="Prediksi NLP">
                <Row label="Comment ID" value={result.nlp_prediction.comment_id} mono />
                <Row label="Model" value={result.nlp_prediction.model_version} mono />
                <Row label="Raw intent" value={result.nlp_prediction.raw_intent} mono />
                <Row label="Signal" value={INTENT_LABELS[result.nlp_prediction.normalized_signal]} />
                {Object.keys(result.nlp_prediction.slots).length > 0 && (
                  <Row label="Slots" value={JSON.stringify(result.nlp_prediction.slots)} mono />
                )}
                <Row label="Confidence" value={formatConfidence(result.nlp_prediction.overall_confidence)} />
                <Row label="Readiness" value={result.nlp_prediction.readiness} />
                <Row label="Urgency" value={result.nlp_prediction.urgency} />
                <div className="intent-list">
                  {[...result.nlp_prediction.intents]
                    .sort((a, b) => b.score - a.score)
                    .map((intent) => (
                      <Row key={intent.intent} label={INTENT_LABELS[intent.intent]} value={formatConfidence(intent.score)} />
                    ))}
                </div>
              </DetailBlock>

              <DetailBlock title="Snapshot audiens">
                <Row label="Pola" value={AUDIENCE_STATE_LABELS[result.audience_snapshot.audience_state]} />
                <Row label="Signal" value={INTENT_LABELS[result.audience_snapshot.dominant_signal]} />
                <Row label="Confidence" value={formatConfidence(result.audience_snapshot.state_confidence)} />
                <Row label="Window" value={`${result.audience_snapshot.window_seconds} detik`} />
                <Row label="Support" value={String(result.audience_snapshot.support_count)} />
                <Row label="Pengguna unik" value={String(result.audience_snapshot.unique_user_count)} />
                {result.audience_snapshot.latest_timestamp_ms > 0 && (
                  <Row label="Event time" value={`${result.audience_snapshot.latest_timestamp_ms} ms`} mono />
                )}
                {Object.keys(result.audience_snapshot.slots_summary).length > 0 && (
                  <Row label="Slot agregat" value={JSON.stringify(result.audience_snapshot.slots_summary)} mono />
                )}
                <Row label="Siap beli" value={String(result.audience_snapshot.high_readiness_count)} />
                <Row label="Prioritas" value={String(result.audience_snapshot.priority_count)} />
              </DetailBlock>

              <DetailBlock title="Keputusan aksi">
                <Row label="Aksi" value={SELECTED_ACTION_LABELS[result.action_decision.selected_action]} />
                <Row label="Signal" value={INTENT_LABELS[result.action_decision.selected_signal]} />
                <Row label="Score" value={formatConfidence(result.action_decision.action_score)} />
                {result.action_decision.required_fact_types.length > 0 && (
                  <Row label="Fakta" value={result.action_decision.required_fact_types.join(', ')} mono />
                )}
                {Object.keys(result.action_decision.required_fact_query).length > 0 && (
                  <Row label="Fact query" value={JSON.stringify(result.action_decision.required_fact_query)} mono />
                )}
              </DetailBlock>

              {result.coach_card && (
                <DetailBlock title="Coach card">
                  <Row
                    label="Validasi"
                    value={result.coach_card.validation_status === 'PASSED' ? 'Sesuai Knowledge Base' : 'Perlu ditinjau'}
                  />
                  <Row
                    label="Sumber"
                    value={result.coach_card.generation_provider === 'GEMINI' ? 'Gemini API' : 'Template Knowledge Base'}
                  />
                  <Row label="Evidence" value={result.coach_card.evidence_comment_ids.join(', ')} mono />
                  {result.coach_card.used_fact_ids.length > 0 && <Row label="Used facts" value={result.coach_card.used_fact_ids.join(', ')} mono />}
                </DetailBlock>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}

function DetailBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="detail-block">
      <p className="detail-title">{title}</p>
      <div className="detail-list">{children}</div>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="detail-row">
      <span className="detail-key">{label}</span>
      <span className="detail-value" data-mono={mono}>{value}</span>
    </div>
  );
}
