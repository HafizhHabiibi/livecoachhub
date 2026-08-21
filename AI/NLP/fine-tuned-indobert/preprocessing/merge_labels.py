import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
LABELS_DIR = ROOT / "data" / "processed" / "labels"
BATCHES_DIR = ROOT / "data" / "processed" / "to_label" / "batches"
OUT_DIR = ROOT / "data" / "processed"
QC_DIR = ROOT / "outputs" / "labeling"
CONF_THRESHOLD = 0.6

with open(ROOT / "fine-tuned-indobert" / "configs" / "taxonomy.yaml", "r", encoding="utf-8") as f:
    taxonomy = yaml.safe_load(f)
VALID_INTENTS = {i["id"] for i in taxonomy["intents"]}
VALID_SENTIMENTS = {s["id"] for s in taxonomy["sentiments"]}


def read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


meta_rows = []
for fp in sorted(BATCHES_DIR.glob("batch_*.jsonl")):
    meta_rows.extend(read_jsonl(fp))
meta = pd.DataFrame(meta_rows)
meta["comment_id"] = meta["comment_id"].astype(str)
assert meta["comment_id"].is_unique, "duplikat comment_id di to_label/batches"

label_rows = []
for fp in sorted(LABELS_DIR.glob("batch_*.jsonl")):
    label_rows.extend(read_jsonl(fp))
labels = pd.DataFrame(label_rows)
labels["comment_id"] = labels["comment_id"].astype(str)

dup = labels["comment_id"].duplicated().sum()
missing = sorted(set(meta["comment_id"]) - set(labels["comment_id"]))
extra = sorted(set(labels["comment_id"]) - set(meta["comment_id"]))

bad_intent = labels[~labels["intent"].isin(VALID_INTENTS)]
bad_sentiment = labels[~labels["sentiment"].isin(VALID_SENTIMENTS)]
bad_conf = labels[(labels["confidence"] < 0.0) | (labels["confidence"] > 1.0)]

merged = meta.merge(labels, on="comment_id", how="inner", validate="one_to_one")
merged = merged[["comment_id", "text", "session_id", "source_file", "timestamp",
                 "intent", "sentiment", "confidence", "needs_review", "reason"]]

need_review = merged[merged["needs_review"] == True]
low_conf = merged[merged["confidence"] < CONF_THRESHOLD]

QC_DIR.mkdir(parents=True, exist_ok=True)
need_review.to_csv(QC_DIR / "qc_needs_review.csv", index=False, encoding="utf-8-sig")
low_conf.to_csv(QC_DIR / "qc_low_confidence.csv", index=False, encoding="utf-8-sig")
merged.to_parquet(OUT_DIR / "comments_labeled.parquet", index=False)
merged.to_csv(OUT_DIR / "comments_labeled.csv", index=False, encoding="utf-8-sig")

print(f"total label       : {len(labels)}")
print(f"duplicate label   : {dup} (harus 0)")
print(f"belum berlabel    : {len(missing)} (harus 0)")
print(f"label tanpa data  : {len(extra)} (harus 0)")
print(f"intent invalid    : {len(bad_intent)} (harus 0)")
print(f"sentiment invalid : {len(bad_sentiment)} (harus 0)")
print(f"confidence invalid: {len(bad_conf)} (harus 0)")
print("")
print("distribusi intent:")
for name, cnt in merged["intent"].value_counts().sort_index().items():
    print(f"  {name:<18}: {cnt:>4}")
print("distribusi sentiment:")
for name, cnt in merged["sentiment"].value_counts().sort_index().items():
    print(f"  {name:<18}: {cnt:>4}")
print("")
print(f"needs_review      : {len(need_review)} ({len(need_review)/len(merged):.1%})")
print(f"confidence < 0.6  : {len(low_conf)}")
print("output             :", OUT_DIR / "comments_labeled.parquet")
print("review             :", QC_DIR)

if dup or missing or extra or len(bad_intent) or len(bad_sentiment) or len(bad_conf):
    raise SystemExit("QC GAGAL - periksa masalah di atas")
print("QC OK")