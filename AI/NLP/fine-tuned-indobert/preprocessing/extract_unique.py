import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "data" / "processed" / "to_label"
BATCH_SIZE = 150

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "batches").mkdir(exist_ok=True)

records = []
for fp in sorted((DATA_DIR / "raw").glob("*.jsonl")):
    with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict) and rec.get("type") == "comment" and rec.get("text"):
                text = str(rec["text"]).strip()
                if text:
                    records.append({
                        "text": text,
                        "session_id": rec.get("session_id"),
                        "source_file": fp.name,
                        "timestamp": rec.get("timestamp"),
                    })

full_rows = []
for i, r in enumerate(records, 1):
    full_rows.append({"comment_id": f"comment_{i:06d}", **r})

comment_id_by_text = {}
unique_rows = []
for r in full_rows:
    key = r["text"]
    if key not in comment_id_by_text:
        comment_id_by_text[key] = r["comment_id"]
        unique_rows.append(r)

with open(OUT_DIR / "comments_full.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["comment_id", "text", "session_id", "source_file", "timestamp"])
    w.writeheader()
    w.writerows(full_rows)

with open(OUT_DIR / "comments_unique.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["comment_id", "text", "session_id", "source_file", "timestamp"])
    w.writeheader()
    w.writerows(unique_rows)

n_batches = (len(unique_rows) + BATCH_SIZE - 1) // BATCH_SIZE
for b in range(n_batches):
    chunk = unique_rows[b * BATCH_SIZE:(b + 1) * BATCH_SIZE]
    batch_path = OUT_DIR / "batches" / f"batch_{b + 1:02d}.jsonl"
    with open(batch_path, "w", encoding="utf-8") as f:
        for row in chunk:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"komentar total   : {len(full_rows)}")
print(f"komentar unik    : {len(unique_rows)}")
print(f"jumlah batch     : {n_batches} (ukuran {BATCH_SIZE})")
print("output dir       :", OUT_DIR)