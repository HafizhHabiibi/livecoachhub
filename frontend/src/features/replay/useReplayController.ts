/**
 * LiveCoach AI — useReplayController
 * Spesifikasi Bagian 8 (State UI) + Bagian 3.2 (Alur satu komentar)
 *
 * Hook ini adalah otak dari seluruh aplikasi. Tugasnya:
 * 1. Menerima file .jsonl yang sudah diparsing
 * 2. Mengirim komentar ke backend SATU PER SATU (sequential)
 * 3. Menunggu response sebelum mengirim komentar berikutnya
 * 4. Handle pause/resume yang benar (simpan sisa delay)
 * 5. Handle timeout → pause + retry comment yang sama
 * 6. Reject late response (session_id lama setelah reset)
 * 7. Expose state ke komponen UI
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type {
  ReplayUiState,
  ParsedReplayFile,
  PipelineResult,
  ProcessedComment,
  HealthResponse,
  DemoConfig,
  SelectedAction,
} from '@/contracts/livecoach';
import {
  getHealth,
  getDemoConfig,
  startSession,
  analyzeComment,
  resetSession,
  getSessionCard,
  ApiError,
} from '@/services/livecoachApi';
import { canTransition } from '@/features/replay/replayState';

// ============================================================
// TYPES
// ============================================================

export interface ReplayController {
  // --- State ---
  uiState: ReplayUiState;
  sessionId: string | null;
  file: ParsedReplayFile | null;
  processedComments: ProcessedComment[];  // Max 5 terbaru
  currentIndex: number;                   // Komentar yang sedang/akan diproses
  latestResult: PipelineResult | null;
  errorMessage: string | null;
  config: DemoConfig | null;
  health: HealthResponse | null;
  isHealthRefreshing: boolean;
  isGenerating: boolean;
  pendingAction: SelectedAction | null;
  canRetryError: boolean;
  elapsedMs: number;                      // Untuk replay clock

  // --- Actions ---
  loadFile: (file: ParsedReplayFile) => void;
  start: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  reset: () => Promise<void>;
  dismissError: () => void;
  retryAfterError: () => Promise<void>;
  refreshHealth: () => Promise<void>;
}

// ============================================================
// CONSTANTS
// ============================================================

const MAX_STREAM_COMMENTS = 5;       // Spesifikasi Bagian 7.3: max 5 komentar
const INTER_COMMENT_DELAY_MS = 500;  // Jeda antar komentar saat tidak ada timestamp gap
const CARD_POLL_INTERVAL_MS = 1500;

const OFFLINE_HEALTH: HealthResponse = {
  schema_version: 'health.v1',
  status: 'OFFLINE',
  services: {
    api: 'OFFLINE',
    nlp_model: 'OFFLINE',
    llm_model: 'OFFLINE',
  },
  provider: {
    nlp: 'Heuristic Fallback',
    llm: 'Template Fallback',
  },
};

// ============================================================
// HOOK
// ============================================================

export function useReplayController(): ReplayController {

  // --- Core state ---
  const [uiState, setUiState] = useState<ReplayUiState>('EMPTY');
  const [file, setFile] = useState<ParsedReplayFile | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [processedComments, setProcessedComments] = useState<ProcessedComment[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [latestResult, setLatestResult] = useState<PipelineResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isHealthRefreshing, setIsHealthRefreshing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [pendingAction, setPendingAction] = useState<SelectedAction | null>(null);
  const [canRetryError, setCanRetryError] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);

  // --- Refs (tidak trigger re-render) ---
  const sessionIdRef = useRef<string | null>(null);      // Untuk cek late response
  const isPausedRef = useRef(false);                     // Cek pause di dalam loop async
  const isRunningRef = useRef(false);                    // Cek apakah loop sedang berjalan
  const remainingDelayRef = useRef(0);                   // Sisa delay saat pause
  const currentIndexRef = useRef(0);                     // Index komentar saat ini
  const fileRef = useRef<ParsedReplayFile | null>(null); // File saat ini
  const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedStartRef = useRef(0);
  const elapsedAccRef = useRef(0);                       // Akumulasi elapsed saat pause
  const lastCardSignatureRef = useRef<string | null>(null);

  // ============================================================
  // HELPERS
  // ============================================================

  function transition(to: ReplayUiState) {
    setUiState((prev: ReplayUiState) => {
      if (!canTransition(prev, to)) {
        console.warn(`[Replay] Transisi tidak valid: ${prev} → ${to}`);
        return prev;
      }
      return to;
    });
  }

  /**
   * Mengatur timer untuk penunjuk waktu (elapsed clock).
   * Ditingkatkan untuk membersihkan interval lama agar tidak menumpuk (memory leak/double speed).
   */
  function startElapsedTimer() {
    if (elapsedTimerRef.current) {
      clearInterval(elapsedTimerRef.current);
    }
    elapsedStartRef.current = Date.now();
    elapsedTimerRef.current = setInterval(() => {
      setElapsedMs(elapsedAccRef.current + (Date.now() - elapsedStartRef.current));
    }, 200);
  }

  function pauseElapsedTimer() {
    if (elapsedTimerRef.current) {
      clearInterval(elapsedTimerRef.current);
      elapsedTimerRef.current = null;
    }
    elapsedAccRef.current += Date.now() - elapsedStartRef.current;
  }

  function resetElapsedTimer() {
    if (elapsedTimerRef.current) {
      clearInterval(elapsedTimerRef.current);
      elapsedTimerRef.current = null;
    }
    elapsedAccRef.current = 0;
    setElapsedMs(0);
  }

  const refreshHealth = useCallback(async () => {
    setIsHealthRefreshing(true);
    try {
      setHealth(await getHealth());
    } catch {
      setHealth(OFFLINE_HEALTH);
    } finally {
      setIsHealthRefreshing(false);
    }
  }, []);

  // Cleanup timer saat unmount
  useEffect(() => {
    return () => {
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    };
  }, []);

  // ============================================================
  // INIT — load health dan config saat hook pertama kali dipanggil
  // ============================================================

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setIsHealthRefreshing(true);
      const [healthResult, configResult] = await Promise.allSettled([
        getHealth(),
        getDemoConfig(),
      ]);
      if (cancelled) return;

      setHealth(healthResult.status === 'fulfilled' ? healthResult.value : OFFLINE_HEALTH);
      setIsHealthRefreshing(false);

      if (configResult.status === 'fulfilled') {
        setConfig(configResult.value);
      } else {
        setErrorMessage('Konfigurasi demo gagal dimuat. Muat ulang halaman untuk mencoba lagi.');
        setCanRetryError(false);
      }
    }

    void init();
    return () => { cancelled = true; };
  }, []);

  // ============================================================
  // BACKGROUND CARD POLLER
  // Polling Coach Card dari LLM asinkron selama replay aktif atau setelah FINISHED
  // ============================================================

  useEffect(() => {
    if (!sessionId) return;
    if (!['RUNNING', 'PAUSED', 'FINISHED'].includes(uiState)) return;

    let isSubscribed = true;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const scheduleNext = () => {
      if (isSubscribed) timer = setTimeout(() => void poll(), CARD_POLL_INTERVAL_MS);
    };

    const poll = async () => {
      if (!isSubscribed || sessionIdRef.current !== sessionId) return;

      try {
        const cardData = await getSessionCard(sessionId);
        if (!isSubscribed || sessionIdRef.current !== sessionId) return;

        setIsGenerating(cardData.is_generating);
        setPendingAction(cardData.pending_action);

        if (cardData.coach_card) {
          setLatestResult((prev: PipelineResult | null) => {
            if (!prev) return prev;
            return {
              ...prev,
              coach_card: cardData.coach_card,
              pipeline_status: cardData.pipeline_status,
            };
          });

          const signature = [
            cardData.coach_card.generation_provider,
            cardData.coach_card.validation_status,
            cardData.coach_card.selected_action,
            cardData.coach_card.suggested_response,
          ].join('|');
          if (signature !== lastCardSignatureRef.current) {
            lastCardSignatureRef.current = signature;
            void refreshHealth();
          }
        }

        if (uiState !== 'FINISHED' || cardData.is_generating) scheduleNext();
      } catch (err) {
        if (err instanceof ApiError && err.code === 'SESSION_NOT_FOUND') {
          setErrorMessage(err.userMessage);
          setCanRetryError(false);
          transition('ERROR');
          return;
        }
        console.debug('[Card Poller] Poll check:', err);
        if (uiState !== 'FINISHED') scheduleNext();
      }
    };

    void poll();

    return () => {
      isSubscribed = false;
      if (timer) clearTimeout(timer);
    };
  }, [refreshHealth, sessionId, uiState]);

  // ============================================================
  // SLEEP dengan support pause dan abort (cancel)
  // Tidur selama 'ms' milidetik, tapi bisa dihentikan saat pause/reset.
  // ============================================================

  function sleepWithPause(
    ms: number,
    activeSessionId: string
  ): Promise<'done' | 'paused' | 'aborted'> {
    return new Promise((resolve) => {
      const start = Date.now();

      function checkPause() {
        // Cek jika session telah berubah (Reset/Start Baru) atau loop dibatalkan
        if (sessionIdRef.current !== activeSessionId || !isRunningRef.current) {
          resolve('aborted');
          return;
        }

        if (isPausedRef.current) {
          // Simpan sisa delay untuk resume
          const elapsed = Date.now() - start;
          remainingDelayRef.current = Math.max(0, ms - elapsed);
          resolve('paused');
          return;
        }

        const elapsed = Date.now() - start;
        if (elapsed >= ms) {
          resolve('done');
          return;
        }
        setTimeout(checkPause, 50);
      }

      setTimeout(checkPause, 50);
    });
  }

  // ============================================================
  // REPLAY LOOP — inti dari sequential request
  // ============================================================

  async function runReplayLoop(
    startIndex: number,
    activeSessionId: string,
    currentFile: ParsedReplayFile,
  ) {
    isRunningRef.current = true;
    let index = startIndex;

    while (index < currentFile.comments.length) {
      // Cek apakah session masih aktif (bukan late response dari session lama)
      if (sessionIdRef.current !== activeSessionId) {
        console.log('[Replay] Session berubah — loop dihentikan');
        break;
      }

      const comment = currentFile.comments[index];
      const nextComment = currentFile.comments[index + 1];

      // Hitung delay ke komentar berikutnya berdasarkan timestamp
      const delayToNext = nextComment
        ? Math.max(0, nextComment.timestamp_ms - comment.timestamp_ms)
        : 0;

      // --- Kirim ke backend ---
      let result: PipelineResult;
      try {
        result = await analyzeComment({
          session_id: activeSessionId,
          comment_id: comment.comment_id,
          user_id: comment.user_id,
          timestamp_ms: comment.timestamp_ms,
          text: comment.text,
        });
      } catch (err) {
        // Cek apakah masih sesi yang sama
        if (sessionIdRef.current !== activeSessionId) break;

        if (err instanceof ApiError) {
          if (err.code === 'TIMEOUT') {
            // Timeout → pause replay, user bisa retry
            isPausedRef.current = true;
            pauseElapsedTimer();
            transition('PAUSED');
            // Simpan index saat ini agar retry mengirim comment yang sama
            currentIndexRef.current = index;
            setCurrentIndex(index);
            setErrorMessage(err.userMessage);
            setCanRetryError(true);
          } else {
            // Error lain → ERROR state
            transition('ERROR');
            setErrorMessage(err.userMessage);
            setCanRetryError(err.retryable);
          }
        } else {
          transition('ERROR');
          setErrorMessage('Terjadi kesalahan yang tidak diketahui.');
          setCanRetryError(false);
        }
        isRunningRef.current = false;
        return;
      }

      // Cek late response — session sudah berubah saat request berjalan
      if (sessionIdRef.current !== activeSessionId) {
        console.log('[Replay] Late response diabaikan — session sudah berubah');
        break;
      }

      // --- Update UI dengan hasil (pertahankan coach_card aktif jika ada) ---
      setLatestResult((prev: PipelineResult | null) => {
        const effectiveCoachCard = result.coach_card ?? prev?.coach_card ?? null;
        return {
          ...result,
          coach_card: effectiveCoachCard,
          pipeline_status: result.coach_card
            ? result.pipeline_status
            : (effectiveCoachCard ? (prev?.pipeline_status ?? result.pipeline_status) : result.pipeline_status),
        };
      });
      setProcessedComments((prev: ProcessedComment[]) => {
        const newEntry: ProcessedComment = {
          entry: comment,
          nlp: result.nlp_prediction,
          receivedAt: Date.now(),
        };
        // Tambah ke bawah, maksimal MAX_STREAM_COMMENTS
        return [...prev, newEntry].slice(-MAX_STREAM_COMMENTS);
      });

      index++;
      currentIndexRef.current = index;
      setCurrentIndex(index);

      // Selesai semua komentar
      if (index >= currentFile.comments.length) {
        pauseElapsedTimer();
        transition('FINISHED');
        isRunningRef.current = false;
        return;
      }

      // --- Delay ke komentar berikutnya ---
      const effectiveDelay = remainingDelayRef.current > 0
        ? remainingDelayRef.current
        : Math.max(INTER_COMMENT_DELAY_MS, delayToNext);

      remainingDelayRef.current = 0;

      // Tidur sesuai delay, dengan monitoring status pause/abort
      const sleepResult = await sleepWithPause(effectiveDelay, activeSessionId);

      if (sleepResult === 'aborted') {
        // Di-reset atau sesi diganti saat sedang delay
        isRunningRef.current = false;
        return;
      }

      if (sleepResult === 'paused') {
        // Loop dihentikan karena pause — tunggu resume
        currentIndexRef.current = index;
        setCurrentIndex(index);
        isRunningRef.current = false;
        return;
      }

      // Cek lagi setelah delay
      if (sessionIdRef.current !== activeSessionId) break;
    }

    isRunningRef.current = false;
  }

  // ============================================================
  // ACTIONS
  // ============================================================

  /** Dipanggil saat user memilih file .jsonl yang sudah diparsing */
  const loadFile = useCallback((parsed: ParsedReplayFile) => {
    setFile(parsed);
    fileRef.current = parsed;
    setUiState(parsed.comments.length > 0 && parsed.errors.length === 0
      ? 'FILE_READY'
      : 'EMPTY'
    );
  }, []);

  /** Dipanggil saat tombol Start ditekan */
  async function start() {
    const currentFile = fileRef.current;
    if (!currentFile || currentFile.comments.length === 0) return;
    if (!config) return;

    transition('STARTING');
    setErrorMessage(null);
    setCanRetryError(false);
    setProcessedComments([]);
    setLatestResult(null);
    currentIndexRef.current = 0;
    setCurrentIndex(0);
    remainingDelayRef.current = 0;
    isPausedRef.current = false;

    try {
      const session = await startSession({ product_id: config.product.product_id });
      const newSessionId = session.session_id;

      // Update session ID — dipakai untuk deteksi late response
      sessionIdRef.current = newSessionId;
      setSessionId(newSessionId);

      transition('RUNNING');
      resetElapsedTimer();
      startElapsedTimer();

      void runReplayLoop(0, newSessionId, currentFile);
    } catch (err) {
      transition('ERROR');
      if (err instanceof ApiError) {
        setErrorMessage(err.userMessage);
        setCanRetryError(err.retryable);
      } else {
        setErrorMessage('Gagal memulai sesi. Coba lagi.');
        setCanRetryError(true);
      }
    }
  }

  /** Dipanggil saat tombol Pause ditekan */
  const pause = useCallback(() => {
    isPausedRef.current = true;
    pauseElapsedTimer();
    transition('PAUSED');
  }, []);

  /** Dipanggil saat tombol Resume ditekan */
  function resume() {
    const currentFile = fileRef.current;
    const activeSessionId = sessionIdRef.current;

    if (!currentFile || !activeSessionId) return;
    if (isRunningRef.current) return; // Sudah running

    isPausedRef.current = false;
    transition('RUNNING');
    startElapsedTimer();

    void runReplayLoop(
      currentIndexRef.current,
      activeSessionId,
      currentFile,
    );
  }

  /** Dipanggil saat tombol Reset ditekan */
  const reset = useCallback(async () => {
    // Hentikan loop yang sedang berjalan
    isPausedRef.current = true;
    isRunningRef.current = false;

    // Invalidasi session lama — semua late response akan diabaikan
    const oldSessionId = sessionIdRef.current;
    sessionIdRef.current = null;
    setSessionId(null);

    // Reset backend jika ada session aktif
    if (oldSessionId) {
      try {
        await resetSession({ session_id: oldSessionId });
      } catch {
        // Ignore — UI tetap di-reset
      }
    }

    // Reset semua state UI
    isPausedRef.current = false;
    currentIndexRef.current = 0;
    remainingDelayRef.current = 0;
    resetElapsedTimer();

    setCurrentIndex(0);
    setProcessedComments([]);
    setLatestResult(null);
    setErrorMessage(null);
    setCanRetryError(false);
    setIsGenerating(false);
    setPendingAction(null);
    lastCardSignatureRef.current = null;

    // Kembali ke FILE_READY jika file masih ada, atau EMPTY
    const currentFile = fileRef.current;
    if (currentFile && currentFile.errors.length === 0 && currentFile.comments.length > 0) {
      setUiState('FILE_READY');
    } else {
      setUiState('EMPTY');
    }
  }, []);

  /** Dismiss error banner tanpa reset */
  const dismissError = useCallback(() => {
    setErrorMessage(null);
  }, []);

  /**
   * Retry setelah timeout — kirim komentar yang SAMA lagi.
   * Spesifikasi Bagian 12: "Retry mengirim comment_id yang sama sekali lagi"
   */
  async function retryAfterError() {
    const currentFile = fileRef.current;
    const activeSessionId = sessionIdRef.current;

    if (!currentFile || !canRetryError) return;

    if (!activeSessionId) {
      await start();
      return;
    }

    setErrorMessage(null);
    setCanRetryError(false);
    isPausedRef.current = false;
    transition('RUNNING');
    startElapsedTimer();

    // Mulai dari index yang sama (bukan index+1)
    void runReplayLoop(
      currentIndexRef.current,
      activeSessionId,
      currentFile,
    );
  }

  // ============================================================
  // RETURN
  // ============================================================

  return {
    uiState,
    sessionId,
    file,
    processedComments,
    currentIndex,
    latestResult,
    errorMessage,
    config,
    health,
    isHealthRefreshing,
    isGenerating,
    pendingAction,
    canRetryError,
    elapsedMs,
    loadFile,
    start,
    pause,
    resume,
    reset,
    dismissError,
    retryAfterError,
    refreshHealth,
  };
}
