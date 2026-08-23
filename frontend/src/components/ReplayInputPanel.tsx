/**
 * ReplayInputPanel — kolom kiri
 * Spesifikasi Bagian 7.2: dropzone + file summary + tombol kontrol
 */

import { useRef, useCallback } from 'react';
import type { ParsedReplayFile, ReplayUiState, HealthResponse } from '@/contracts/livecoach';
import { parseJsonlFile, isFileValid, getFileSummaryText } from '@/features/replay/jsonlParser';
import { getButtonVisibility, formatFileSize } from '@/features/replay/replayState';

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
  const isDraggingRef = useRef(false);

  const healthAvailable = health?.status === 'READY' || health?.status === 'DEGRADED';
  const fileValid = file !== null && isFileValid(file);
  const btn = getButtonVisibility(uiState, healthAvailable, fileValid);

  // Progress bar
  const total = file?.comments.length ?? 0;
  const progress = total > 0 ? Math.round((currentIndex / total) * 100) : 0;

  async function handleFile(f: File) {
    if (!f.name.endsWith('.jsonl')) {
      onFileLoaded({
        filename: f.name,
        sizeBytes: f.size,
        comments: [],
        durationMs: 0,
        errors: [{ line: 0, message: 'File harus berformat .jsonl' }],
      });
      return;
    }
    const parsed = await parseJsonlFile(f);
    onFileLoaded(parsed);
  }

  const handleInputChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) await handleFile(f);
    // Reset input agar file yang sama bisa dipilih ulang
    if (inputRef.current) inputRef.current.value = '';
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    isDraggingRef.current = false;
    const f = e.dataTransfer.files?.[0];
    if (f) await handleFile(f);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;
  }, []);

  return (
    <aside
      style={{
        width: 'var(--col-left)',
        minWidth: 260,
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        padding: 'var(--space-4)',
        background: 'var(--color-surface)',
        borderRight: '1px solid var(--color-border)',
        overflowY: 'auto',
      }}
    >
      <h2 style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)', color: 'var(--color-ink)' }}>
        Replay File
      </h2>

      {/* Dropzone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload file replay komentar .jsonl"
        aria-describedby="dropzone-hint"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => { isDraggingRef.current = false; }}
        style={{
          border: '2px dashed var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-6) var(--space-4)',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'border-color var(--transition-fast), background var(--transition-fast)',
          background: 'var(--color-bg)',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-primary)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-border)';
        }}
      >
        <div style={{ fontSize: '2rem', marginBottom: 'var(--space-2)' }} aria-hidden="true">📂</div>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink)', fontWeight: 'var(--weight-medium)', marginBottom: 4 }}>
          Pilih atau drop file
        </p>
        <p id="dropzone-hint" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
          Format: .jsonl
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".jsonl"
          onChange={handleInputChange}
          style={{ display: 'none' }}
          aria-hidden="true"
        />
      </div>

      {/* File summary */}
      {file && (
        <div
          style={{
            background: 'var(--color-bg)',
            border: `1px solid ${isFileValid(file) ? 'var(--color-border)' : 'var(--color-critical)'}`,
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3)',
            fontSize: 'var(--text-xs)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontWeight: 'var(--weight-medium)', color: 'var(--color-ink)', wordBreak: 'break-all' }}>
              {file.filename}
            </span>
            <span style={{ color: 'var(--color-muted)', flexShrink: 0, marginLeft: 8 }}>
              {formatFileSize(file.sizeBytes)}
            </span>
          </div>

          <p style={{ color: isFileValid(file) ? 'var(--color-muted)' : 'var(--color-critical)', marginBottom: 4 }}>
            {getFileSummaryText(file)}
          </p>

          {/* Error list */}
          {file.errors.length > 0 && (
            <ul style={{ margin: 0, padding: '0 0 0 16px', color: 'var(--color-critical)', lineHeight: 1.6 }}>
              {file.errors.map((err, i) => (
                <li key={i}>{err.message}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Progress bar */}
      {(uiState === 'RUNNING' || uiState === 'PAUSED' || uiState === 'FINISHED') && total > 0 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginBottom: 4 }}>
            <span>{currentIndex} / {total} komentar</span>
            <span>{progress}%</span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Progress replay"
            style={{ height: 6, background: 'var(--color-border)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}
          >
            <div
              style={{
                width: `${progress}%`,
                height: '100%',
                background: uiState === 'FINISHED' ? '#16a34a' : 'var(--color-primary)',
                borderRadius: 'var(--radius-full)',
                transition: 'width var(--transition-normal)',
              }}
            />
          </div>
        </div>
      )}

      {/* Error dari controller (timeout dll) */}
      {errorMessage && uiState === 'PAUSED' && (
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-warning)', background: 'var(--color-warning-bg)', padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)' }}>
          {errorMessage}
        </div>
      )}

      {/* Tombol kontrol */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'auto' }}>
        {btn.showStart && (
          <button
            onClick={onStart}
            disabled={btn.startDisabled}
            aria-disabled={btn.startDisabled}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: btn.startDisabled ? 'var(--color-border)' : 'var(--color-primary)',
              color: btn.startDisabled ? 'var(--color-muted)' : '#fff',
              borderRadius: 'var(--radius-md)',
              fontWeight: 'var(--weight-medium)',
              fontSize: 'var(--text-sm)',
              transition: 'opacity var(--transition-fast)',
            }}
          >
            {uiState === 'STARTING' ? 'Memulai…' : '▶ Mulai Replay'}
          </button>
        )}

        {btn.showPause && (
          <button
            onClick={onPause}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: 'var(--color-warning-bg)',
              color: 'var(--color-warning)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 'var(--weight-medium)',
              fontSize: 'var(--text-sm)',
              border: '1px solid var(--color-warning)',
            }}
          >
            ⏸ Jeda
          </button>
        )}

        {btn.showResume && (
          <button
            onClick={uiState === 'PAUSED' && errorMessage ? retryAfterError : onResume}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: 'var(--color-primary)',
              color: '#fff',
              borderRadius: 'var(--radius-md)',
              fontWeight: 'var(--weight-medium)',
              fontSize: 'var(--text-sm)',
            }}
          >
            {errorMessage ? '↺ Coba Lagi' : '▶ Lanjutkan'}
          </button>
        )}

        {btn.showReset && (
          <button
            onClick={onReset}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: 'transparent',
              color: 'var(--color-muted)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 'var(--weight-medium)',
              fontSize: 'var(--text-sm)',
              border: '1px solid var(--color-border)',
            }}
          >
            ↺ Reset
          </button>
        )}

        {uiState === 'FINISHED' && (
          <p style={{ fontSize: 'var(--text-xs)', color: '#16a34a', textAlign: 'center', fontWeight: 'var(--weight-medium)' }}>
            ✓ Replay selesai
          </p>
        )}
      </div>

      {/* Health info */}
      {health && health.status === 'DEGRADED' && (
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-warning)', textAlign: 'center' }}>
          Mode Cepat — Respons template bawaan aktif
        </div>
      )}
      {health && health.status === 'OFFLINE' && (
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-critical)', textAlign: 'center' }}>
          Backend offline — Start tidak tersedia
        </div>
      )}
    </aside>
  );
}
