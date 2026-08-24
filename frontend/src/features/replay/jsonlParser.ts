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
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const errors: ParseError[] = [];
  const comments: CommentEntry[] = [];
  const seenIds = new Set<string>();

  // Batas error yang ditampilkan — jangan flood UI dengan ratusan error
  const MAX_ERRORS = 10;

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
    const lineNumber = i + 1;

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
      raw = JSON.parse(lines[i]);
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
    comments.push(entry);
  }

  // 4. Sort berdasarkan timestamp_ms (spesifikasi: dikirim berurutan)
  comments.sort((a, b) => a.timestamp_ms - b.timestamp_ms);

  const durationMs =
    comments.length > 0
      ? comments[comments.length - 1].timestamp_ms
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
