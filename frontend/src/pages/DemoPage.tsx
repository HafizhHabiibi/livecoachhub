import { useReplayController } from '@/features/replay/useReplayController';
import AppHeader from '@/components/AppHeader';
import AudienceSnapshot from '@/components/AudienceSnapshot';
import CoachCard from '@/components/CoachCard';
import CommentStream from '@/components/CommentStream';
import DecisionDetails from '@/components/DecisionDetails';
import ReplayInputPanel from '@/components/ReplayInputPanel';
import StatusBanner from '@/components/StatusBanner';
import PriorityAlert from '@/components/PriorityAlert';

const SESSION_LABELS = {
  EMPTY: 'Siapkan sumber replay',
  FILE_READY: 'Replay siap dimulai',
  STARTING: 'Membuka sesi analisis',
  RUNNING: 'Analisis berlangsung',
  PAUSED: 'Replay dijeda',
  FINISHED: 'Replay selesai',
  ERROR: 'Sesi memerlukan perhatian',
} as const;

export default function DemoPage() {
  const controller = useReplayController();
  const showGlobalError = controller.errorMessage !== null && controller.uiState !== 'PAUSED';
  const isLive = controller.uiState === 'RUNNING';

  return (
    <div className="app-shell">
      <AppHeader
        health={controller.health}
        config={controller.config}
        sessionId={controller.sessionId}
        elapsedMs={controller.elapsedMs}
      />

      {showGlobalError && controller.errorMessage && (
        <div className="global-banner">
          <StatusBanner
            message={controller.errorMessage}
            type="error"
            onDismiss={controller.dismissError}
            onRetry={controller.uiState === 'ERROR' && controller.canRetryError ? controller.retryAfterError : undefined}
          />
        </div>
      )}

      <main className="workspace">
        <ReplayInputPanel
          uiState={controller.uiState}
          file={controller.file}
          currentIndex={controller.currentIndex}
          health={controller.health}
          onFileLoaded={controller.loadFile}
          onStart={controller.start}
          onPause={controller.pause}
          onResume={controller.resume}
          onReset={controller.reset}
          retryAfterError={controller.retryAfterError}
          errorMessage={controller.uiState === 'PAUSED' ? controller.errorMessage : null}
          isHealthRefreshing={controller.isHealthRefreshing}
          onRefreshHealth={controller.refreshHealth}
        />

        <section className="live-workspace" aria-label="Live operations desk">
          <div className="workspace-heading">
            <div>
              <span className="workspace-kicker">Live operations</span>
              <h1>Audience signal desk</h1>
              <p>Fokus pada perubahan audiens, komentar yang perlu perhatian, dan satu tindakan berikutnya.</p>
            </div>
            <span className="inline-status" data-active={isLive}>
              <span className="live-pulse" aria-hidden="true" />
              <span>{SESSION_LABELS[controller.uiState]}</span>
            </span>
          </div>

          <AudienceSnapshot snapshot={controller.latestResult?.audience_snapshot ?? null} />

          <PriorityAlert event={controller.latestResult?.priority_event ?? null} />

          <div className="operations-grid">
            <CommentStream comments={controller.processedComments} />
            <CoachCard
              result={controller.latestResult}
              isGenerating={controller.isGenerating}
              pendingAction={controller.pendingAction}
            />
          </div>

          <DecisionDetails result={controller.latestResult} />
        </section>
      </main>
    </div>
  );
}
