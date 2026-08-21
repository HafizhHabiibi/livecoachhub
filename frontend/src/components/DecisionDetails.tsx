/**
 * DecisionDetails — panel detail teknis yang bisa di-collapse
 * Spesifikasi Bagian 7.6: NLP + action score + latency
 * Default: collapsed — juri bisa expand saat pitching
 */

import { useState } from 'react';
import type { PipelineResult } from '@/contracts/livecoach';
import {
  INTENT_LABELS,
  AUDIENCE_STATE_LABELS,
  SELECTED_ACTION_LABELS,
  PIPELINE_STATUS_LABELS,
  formatConfidence,
} from '@/features/replay/replayState';

interface DecisionDetailsProps {
  result: PipelineResult | null;
}

export default function DecisionDetails({ result }: DecisionDetailsProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
      }}
    >
      {/* Toggle header */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
        style={{
          width: '100%',
          padding: 'var(--space-3) var(--space-4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'none',
          cursor: 'pointer',
          borderBottom: isOpen ? '1px solid var(--color-border)' : 'none',
        }}
      >
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)', color: 'var(--color-ink)' }}>
          Detail Teknis Pipeline
        </span>
        <span style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--color-muted)',
          transform: isOpen ? 'rotate(180deg)' : 'none',
          transition: 'transform var(--transition-fast)',
          display: 'inline-block',
        }}>
          ▼
        </span>
      </button>

      {/* Content */}
      {isOpen && (
        <div style={{
          padding: 'var(--space-4)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-4)',
          fontSize: 'var(--text-xs)',
        }}>
          {!result ? (
            <p style={{ color: 'var(--color-muted)', gridColumn: '1 / -1' }}>
              Belum ada data pipeline.
            </p>
          ) : (
            <>
              {/* Pipeline status */}
              <DetailBlock title="Status Pipeline">
                <Row label="Status" value={PIPELINE_STATUS_LABELS[result.pipeline_status]} />
                <Row label="Diproses" value={`${result.processed_count} komentar`} />
                {result.latency_ms && (
                  <Row label="Total latency" value={`${result.latency_ms.total}ms`} mono />
                )}
                {result.latency_ms?.nlp && (
                  <Row label="NLP" value={`${result.latency_ms.nlp}ms`} mono />
                )}
                {result.latency_ms?.generation && (
                  <Row label="Generation" value={`${result.latency_ms.generation}ms`} mono />
                )}
              </DetailBlock>

              {/* NLP Prediction */}
              <DetailBlock title="NLP Prediction">
                <Row label="Comment ID" value={result.nlp_prediction.comment_id} mono />
                <Row label="Model" value={result.nlp_prediction.model_version} mono />
                <Row label="Confidence" value={formatConfidence(result.nlp_prediction.overall_confidence)} />
                <Row label="Readiness" value={result.nlp_prediction.readiness} />
                <Row label="Urgency" value={result.nlp_prediction.urgency} />
                <Row label="Usable" value={result.nlp_prediction.usable_for_decision ? 'Ya' : 'Tidak (low confidence)'} />
                <div style={{ marginTop: 4 }}>
                  <span style={{ color: 'var(--color-muted)' }}>Intents:</span>
                  {result.nlp_prediction.intents
                    .sort((a, b) => b.score - a.score)
                    .map((i) => (
                      <div key={i.intent} style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 8, marginTop: 2 }}>
                        <span>{INTENT_LABELS[i.intent]}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-muted)' }}>
                          {formatConfidence(i.score)}
                        </span>
                      </div>
                    ))
                  }
                </div>
              </DetailBlock>

              {/* Audience Snapshot */}
              <DetailBlock title="Audience Snapshot">
                <Row label="State" value={AUDIENCE_STATE_LABELS[result.audience_snapshot.audience_state]} />
                <Row label="Confidence" value={formatConfidence(result.audience_snapshot.state_confidence)} />
                <Row label="Window" value={`${result.audience_snapshot.window_seconds}d`} />
                <Row label="Support count" value={String(result.audience_snapshot.support_count)} />
                <Row label="High readiness" value={String(result.audience_snapshot.high_readiness_count)} />
                <Row label="Priority count" value={String(result.audience_snapshot.priority_count)} />
              </DetailBlock>

              {/* Action Decision */}
              <DetailBlock title="Action Decision">
                <Row label="Action" value={SELECTED_ACTION_LABELS[result.action_decision.selected_action]} />
                <Row label="Score" value={formatConfidence(result.action_decision.action_score)} />
                {result.action_decision.required_fact_types.length > 0 && (
                  <Row label="Facts needed" value={result.action_decision.required_fact_types.join(', ')} mono />
                )}
              </DetailBlock>

              {/* Coach Card (jika ada) */}
              {result.coach_card && (
                <DetailBlock title="Coach Card">
                  <Row label="Validasi" value={result.coach_card.validation_status} />
                  <Row label="Fallback" value={result.coach_card.fallback_used ? 'Ya' : 'Tidak'} />
                  <Row label="Evidence" value={result.coach_card.evidence_comment_ids.join(', ')} mono />
                  {result.coach_card.used_fact_ids.length > 0 && (
                    <Row label="Used facts" value={result.coach_card.used_fact_ids.join(', ')} mono />
                  )}
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
    <div style={{
      background: 'var(--color-bg)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-sm)',
      padding: 'var(--space-3)',
    }}>
      <p style={{
        fontSize: 'var(--text-xs)',
        fontWeight: 'var(--weight-semibold)',
        color: 'var(--color-primary)',
        marginBottom: 8,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      }}>
        {title}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {children}
      </div>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
      <span style={{ color: 'var(--color-muted)', flexShrink: 0 }}>{label}</span>
      <span style={{
        color: 'var(--color-ink)',
        fontFamily: mono ? 'var(--font-mono)' : 'inherit',
        textAlign: 'right',
        wordBreak: 'break-all',
      }}>
        {value}
      </span>
    </div>
  );
}
