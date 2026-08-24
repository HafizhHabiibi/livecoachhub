/**
 * LiveCoach AI — JSONL Parser
 * Spesifikasi Bagian 9 + Bagian 12 (error messages)
 *
 * Validasi dilakukan DI BROWSER sebelum file dikirim ke backend.
 * Spesifikasi: "Frontend memvalidasi format tanpa mengirim seluruh file ke backend."
 *
 * Aturan validasi:
 * 1. Setiap baris harus JSON valid
 * 2. Setiap baris harus punya comment_id, user_id, timestamp_ms, text
 * 3. comment_id harus unik dalam satu file
 * 4. timestamp_ms harus integer >= 0
 * 5. File tidak boleh kosong
 */

import { CommentEntrySchema } from '@/contracts/livecoachSchemas';
import type { ParsedReplayFile, ParseError, CommentEntry } from '@/contracts/livecoach';

export const MAX_REPLAY_FILE_BYTES = 5 * 1024 * 1024;
export const MAX_REPLAY_ROWS = 10_000;

// ============================================================
// PARSER UTAMA
// ============================================================

/**
 * Parse file .jsonl menjadi ParsedReplayFile.
 * Selalu mengembalikan hasil — errors[] kosong berarti valid.
 */
export function parseJsonlFile(file: File): Promise<ParsedReplayFile> {
  return new Promise((resolve) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      const text = e.target?.result as string;
      const result = parseJsonlText(text, file.name, file.size);
      resolve(result);
    };

    reader.onerror = () => {
      resolve({
        filename: file.name,
        sizeBytes: file.size,
        comments: [],
        durationMs: 0,
        errors: [{ line: 0, message: 'Gagal membaca file.' }],
      });
    };

    reader.readAsText(file, 'utf-8');
  });
}

/**
 * Parse string JSONL — dipisah dari parseJsonlFile agar bisa ditest.
 */
export function parseJsonlText(
  text: string,
  filename = 'unknown.jsonl',
  sizeBytes = 0,
): ParsedReplayFile {
  const lines = text
    .split(/\r?\n/)
    .map((content, index) => ({ content: content.trim(), lineNumber: index + 1 }))
    .filter((line) => line.content.length > 0);
  const errors: ParseError[] = [];
  const comments: CommentEntry[] = [];
  const seenIds = new Set<string>();
  const commentLineNumbers = new Map<string, number>();

  // Batas error yang ditampilkan — jangan flood UI dengan ratusan error
  const MAX_ERRORS = 10;

  if (sizeBytes > MAX_REPLAY_FILE_BYTES) {
    return {
      filename,
      sizeBytes,
      comments: [],
      durationMs: 0,
      errors: [{ line: 0, message: 'Ukuran file melebihi batas 5 MB.' }],
    };
  }

  if (lines.length > MAX_REPLAY_ROWS) {
    return {
      filename,
      sizeBytes,
      comments: [],
      durationMs: 0,
      errors: [{ line: 0, message: `File melebihi batas ${MAX_REPLAY_ROWS.toLocaleString('id-ID')} komentar.` }],
    };
  }

  if (lines.length === 0) {
    return {
      filename,
      sizeBytes,
      comments: [],
      durationMs: 0,
      errors: [{ line: 0, message: 'File tidak memiliki komentar yang dapat diproses.' }],
    };
  }

  for (let i = 0; i < lines.length; i++) {
    const { content, lineNumber } = lines[i];

    // Batas error
    if (errors.length >= MAX_ERRORS) {
      errors.push({
        line: lineNumber,
        message: `... dan ${lines.length - i} baris lainnya mungkin bermasalah.`,
      });
      break;
    }

    // 1. Cek JSON valid
    let raw: unknown;
    try {
      raw = JSON.parse(content);
    } catch {
      errors.push({
        line: lineNumber,
        message: `Baris ${lineNumber} bukan JSON yang valid.`,
      });
      continue;
    }

    // 2. Validasi schema dengan Zod
    const parsed = CommentEntrySchema.safeParse(raw);
    if (!parsed.success) {
      const issues = parsed.error.issues;
      const firstIssue = issues[0];

      // Pesan error yang actionable sesuai spesifikasi Bagian 12
      let message: string;
      if (firstIssue.path.includes('text')) {
        message = `Baris ${lineNumber} tidak memiliki text.`;
      } else if (firstIssue.path.includes('user_id')) {
        message = `Baris ${lineNumber} tidak memiliki user_id.`;
      } else if (firstIssue.path.includes('comment_id')) {
        message = `Baris ${lineNumber} tidak memiliki comment_id.`;
      } else if (firstIssue.path.includes('timestamp_ms')) {
        message = `Baris ${lineNumber}: timestamp_ms harus berupa angka bulat >= 0.`;
      } else {
        message = `Baris ${lineNumber}: ${firstIssue.message}`;
      }

      errors.push({ line: lineNumber, message });
      continue;
    }

    const entry = parsed.data;

    // 3. Cek duplicate comment_id
    if (seenIds.has(entry.comment_id)) {
      errors.push({
        line: lineNumber,
        message: `comment_id "${entry.comment_id}" muncul lebih dari sekali.`,
      });
      continue;
    }

    seenIds.add(entry.comment_id);
    commentLineNumbers.set(entry.comment_id, lineNumber);
    comments.push(entry);
  }

  // 4. Tolak urutan timestamp menurun; jangan diam-diam mengubah input pengguna.
  for (let i = 1; i < comments.length; i++) {
    if (comments[i].timestamp_ms < comments[i - 1].timestamp_ms) {
      const originalLine = commentLineNumbers.get(comments[i].comment_id) ?? 0;
      errors.push({
        line: originalLine,
        message: `Baris ${originalLine}: timestamp_ms harus berurutan naik.`,
      });
      if (errors.length >= MAX_ERRORS) break;
    }
  }

  const durationMs =
    comments.length > 0
      ? Math.max(...comments.map((comment) => comment.timestamp_ms))
      : 0;

  return {
    filename,
    sizeBytes,
    comments,
    durationMs,
    errors,
  };
}

// ============================================================
// HELPERS
// ============================================================

/** File valid jika tidak ada errors dan minimal 1 komentar */
export function isFileValid(file: ParsedReplayFile): boolean {
  return file.errors.length === 0 && file.comments.length > 0;
}

/** Ambil preview singkat komentar pertama untuk file summary */
export function getFileSummaryText(file: ParsedReplayFile): string {
  if (file.errors.length > 0) return 'File tidak valid';
  const count = file.comments.length;
  const durSec = Math.ceil(file.durationMs / 1000);
  return `${count} komentar · ${durSec} detik`;
}
