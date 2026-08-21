/**
 * DemoPage — halaman /demo
 * Fase 6: rakit semua komponen + layout grid 3 kolom
 */

import { useReplayController } from '@/features/replay/useReplayController';
import AppHeader from '@/components/AppHeader';
import ReplayInputPanel from '@/components/ReplayInputPanel';
import CommentStream from '@/components/CommentStream';
import AudienceSnapshot from '@/components/AudienceSnapshot';
import CoachCard from '@/components/CoachCard';
import DecisionDetails from '@/components/DecisionDetails';
import StatusBanner from '@/components/StatusBanner';

export default function DemoPage() {
  const ctrl = useReplayController();

  const showBanner =
    ctrl.errorMessage !== null &&
    ctrl.uiState !== 'PAUSED'; // PAUSED error ditampilkan di panel kiri

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--color-bg)' }}>

      {/* Header sticky */}
      <AppHeader
        health={ctrl.health}
        config={ctrl.config}
        sessionId={ctrl.sessionId}
        elapsedMs={ctrl.elapsedMs}
      />

      {/* Error banner global */}
      {showBanner && ctrl.errorMessage && (
        <div style={{ padding: 'var(--space-3) var(--space-6)' }}>
          <StatusBanner
            message={ctrl.errorMessage}
            type="error"
            onDismiss={ctrl.dismissError}
            onRetry={ctrl.uiState === 'ERROR' ? ctrl.retryAfterError : undefined}
          />
        </div>
      )}

      {/* Layout utama: 3 kolom */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: 'var(--col-left) var(--col-middle) var(--col-right)',
        gridTemplateRows: '1fr auto',
        gap: 0,
        maxWidth: 'var(--max-width)',
        width: '100%',
        margin: '0 auto',
        minHeight: 0,
      }}>

        {/* Kolom kiri: input panel — span 2 rows */}
        <div style={{ gridRow: '1 / 3', borderRight: '1px solid var(--color-border)' }}>
          <ReplayInputPanel
            uiState={ctrl.uiState}
            file={ctrl.file}
            currentIndex={ctrl.currentIndex}
            health={ctrl.health}
            onFileLoaded={ctrl.loadFile}
            onStart={ctrl.start}
            onPause={ctrl.pause}
            onResume={ctrl.resume}
            onReset={ctrl.reset}
            retryAfterError={ctrl.retryAfterError}
            errorMessage={ctrl.uiState === 'PAUSED' ? ctrl.errorMessage : null}
          />
        </div>

        {/* Kolom tengah: comment stream + audience snapshot */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
          padding: 'var(--space-4)',
          overflowY: 'auto',
          borderRight: '1px solid var(--color-border)',
        }}>
          <CommentStream comments={ctrl.processedComments} />
          <AudienceSnapshot
            snapshot={ctrl.latestResult?.audience_snapshot ?? null}
          />
        </div>

        {/* Kolom kanan: coach card */}
        <div style={{
          padding: 'var(--space-4)',
          overflowY: 'auto',
        }}>
          <CoachCard result={ctrl.latestResult} />
        </div>

        {/* Baris bawah: decision details — span kolom tengah + kanan */}
        <div style={{
          gridColumn: '2 / 4',
          borderTop: '1px solid var(--color-border)',
          padding: 'var(--space-4)',
          background: 'var(--color-surface)',
        }}>
          <DecisionDetails result={ctrl.latestResult} />
        </div>
      </div>
    </div>
  );
}
