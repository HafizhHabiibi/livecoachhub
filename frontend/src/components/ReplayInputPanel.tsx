import { useRef, useState } from 'react';
import type { HealthResponse, ParsedReplayFile, ReplayUiState } from '@/contracts/livecoach';
import { getFileSummaryText, isFileValid, parseJsonlFile } from '@/features/replay/jsonlParser';
import { formatFileSize, getButtonVisibility } from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface ReplayInputPanelProps {
  uiState: ReplayUiState;
  file: ParsedReplayFile | null;
  currentIndex: number;
  health: HealthResponse | null;
  onFileLoaded: (file: ParsedReplayFile) => void;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
  retryAfterError: () => void;
  errorMessage: string | null;
}

export default function ReplayInputPanel({
  uiState,
  file,
  currentIndex,
  health,
  onFileLoaded,
  onStart,
  onPause,
  onResume,
  onReset,
  retryAfterError,
  errorMessage,
}: ReplayInputPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const healthAvailable = health?.status === 'READY' || health?.status === 'DEGRADED';
  const fileValid = file !== null && isFileValid(file);
  const buttons = getButtonVisibility(uiState, healthAvailable, fileValid);
  const total = file?.comments.length ?? 0;
  const progress = total > 0 ? Math.round((currentIndex / total) * 100) : 0;

  async function handleFile(selected: File) {
    if (!selected.name.toLowerCase().endsWith('.jsonl')) {
      onFileLoaded({
        filename: selected.name,
        sizeBytes: selected.size,
        comments: [],
        durationMs: 0,
        errors: [{ line: 0, message: 'File harus berformat .jsonl' }],
      });
      return;
    }
    onFileLoaded(await parseJsonlFile(selected));
  }

  return (
    <aside className="control-rail" aria-label="Kontrol replay">
      <div className="rail-intro">
        <p className="rail-kicker">Sumber sesi</p>
        <h2 className="rail-title">Replay komentar</h2>
        <p className="rail-copy">Jalankan rekaman komentar untuk melihat sinyal audiens dan arahan host secara berurutan.</p>
      </div>

      <div className="rail-upload">
        <button
          type="button"
          className="dropzone"
          data-dragging={isDragging}
          aria-describedby="dropzone-hint"
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            const selected = event.dataTransfer.files?.[0];
            if (selected) void handleFile(selected);
          }}
        >
          <span className="dropzone-icon"><Icon name="upload" size={15} /></span>
          <span>
            <strong>Pilih file replay</strong>
            <span id="dropzone-hint">JSONL · klik atau letakkan di sini</span>
          </span>
        </button>
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept=".jsonl"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => {
            const selected = event.target.files?.[0];
            if (selected) void handleFile(selected);
            event.target.value = '';
          }}
        />
      </div>

      {file && (
        <div className="file-summary" data-valid={fileValid}>
          <div className="file-heading">
            <span className="file-name" title={file.filename}>{file.filename}</span>
            <span className="file-size">{formatFileSize(file.sizeBytes)}</span>
          </div>
          <p className="file-state">{getFileSummaryText(file)}</p>
          {file.errors.length > 0 && (
            <ul className="file-errors">
              {file.errors.map((error, index) => <li key={`${error.line}-${index}`}>{error.message}</li>)}
            </ul>
          )}
        </div>
      )}

      {(uiState === 'RUNNING' || uiState === 'PAUSED' || uiState === 'FINISHED') && total > 0 && (
        <div className="replay-progress">
          <div className="progress-labels">
            <span>{currentIndex} dari {total} komentar</span>
            <span>{progress}%</span>
          </div>
          <div className="progress-track" role="progressbar" aria-label="Progress replay" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="progress-fill" data-finished={uiState === 'FINISHED'} style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {errorMessage && uiState === 'PAUSED' && <div className="rail-alert">{errorMessage}</div>}

      <div className="rail-actions">
        {buttons.showStart && (
          <button type="button" className="button button-primary" onClick={onStart} disabled={buttons.startDisabled}>
            <span className="button-content"><Icon name="play" size={14} />{uiState === 'STARTING' ? 'Memulai sesi…' : 'Mulai replay'}</span>
          </button>
        )}
        {buttons.showPause && (
          <button type="button" className="button button-warning" onClick={onPause}>
            <span className="button-content"><Icon name="pause" size={14} />Jeda replay</span>
          </button>
        )}
        {buttons.showResume && (
          <button type="button" className="button button-primary" onClick={errorMessage ? retryAfterError : onResume}>
            <span className="button-content"><Icon name={errorMessage ? 'reset' : 'play'} size={14} />{errorMessage ? 'Coba komentar ini lagi' : 'Lanjutkan replay'}</span>
          </button>
        )}
        {buttons.showReset && (
          <button type="button" className="button button-quiet" onClick={onReset}>
            <span className="button-content"><Icon name="reset" size={14} />Reset sesi</span>
          </button>
        )}
      </div>

      {uiState === 'FINISHED' && <p className="rail-footnote" data-tone="success">Replay selesai · data sesi tetap dapat ditinjau</p>}
      {health?.status === 'DEGRADED' && <p className="rail-footnote" data-tone="warning">Mode terbatas aktif · respons aman dapat digunakan</p>}
      {health?.status === 'OFFLINE' && <p className="rail-footnote" data-tone="error">Backend tidak terhubung · replay belum dapat dimulai</p>}
    </aside>
  );
}
