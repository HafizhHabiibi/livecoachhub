"""
LiveCoachHub Backend — Replay Engine

Untuk preliminary, replay dihandle oleh frontend:
- Frontend membaca file .jsonl
- Frontend mengirim komentar satu per satu via POST /api/v1/comments/analyze
- Frontend mengatur timing berdasarkan timestamp_ms

Modul ini menyediakan utility untuk memuat replay data
dari file JSONL jika dibutuhkan (misalnya untuk testing backend).

Sesuai PROJECT.MD Bagian 5 Tahap 1:
"Backend membaca file replay JSON/JSONL yang berisi
comment_id, user_id anonim, timestamp, dan text."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, TypedDict

from config import REPLAY_DIR


class CommentEntry(TypedDict):
    comment_id: str
    user_id: str
    timestamp_ms: int
    text: str


def load_replay_file(filename: str = "comments-demo.jsonl") -> List[CommentEntry]:
    """Load file replay JSONL dan return sebagai list of CommentEntry.

    Args:
        filename: Nama file di data/replay/ directory.

    Returns:
        List of CommentEntry, diurutkan berdasarkan timestamp_ms ascending.
    """
    filepath = REPLAY_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Replay file tidak ditemukan: {filepath}")

    comments: List[CommentEntry] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                comments.append(CommentEntry(
                    comment_id=entry["comment_id"],
                    user_id=entry["user_id"],
                    timestamp_ms=entry["timestamp_ms"],
                    text=entry["text"],
                ))
            except (json.JSONDecodeError, KeyError) as e:
                raise ValueError(f"Error parsing line {line_num}: {e}")

    # Sort by timestamp ascending
    comments.sort(key=lambda c: c["timestamp_ms"])
    return comments


def list_replay_files() -> List[str]:
    """List semua file .jsonl di data/replay/ directory."""
    if not REPLAY_DIR.exists():
        return []
    return [f.name for f in REPLAY_DIR.glob("*.jsonl")]
