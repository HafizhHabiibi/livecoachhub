import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JSONL = ROOT / "data" / "dataset" / "tiktok_live_10k.jsonl"
REPORT = ROOT / "data" / "dataset" / "report.md"

VALID_INTENTS = {
    "product_inquiry",
    "size_inquiry",
    "size_recommendation",
    "color_inquiry",
    "price_inquiry",
    "stock_availability",
    "purchase_intent",
    "not_relevant",
}
VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def main():
    rows = []
    with open(JSONL, encoding="utf-8") as f:
        for ln in f:
            rows.append(json.loads(ln))

    errors = []
    if len(rows) != 10000:
        errors.append(f"jumlah baris {len(rows)} != 10000")

    ids = [r["comment_id"] for r in rows]
    if len(set(ids)) != len(ids):
        errors.append("ada comment_id duplikat")

    texts = [r["text"].strip() for r in rows]
    empty = [i for i, t in enumerate(texts) if not t]
    if empty:
        errors.append(f"ada teks kosong di baris {empty[:5]}")

    bad_intent = [r["comment_id"] for r in rows if r["intent"] not in VALID_INTENTS]
    if bad_intent:
        errors.append(f"intent tidak valid: {bad_intent[:5]}")

    bad_sent = [r["comment_id"] for r in rows if r["sentiment"] not in VALID_SENTIMENTS]
    if bad_sent:
        errors.append(f"sentiment tidak valid: {bad_sent[:5]}")

    intent_counts = Counter(r["intent"] for r in rows)
    sentiment_counts = Counter(r["sentiment"] for r in rows)

    for intent, c in intent_counts.items():
        if c != 1250:
            errors.append(f"{intent}: {c} != 1250")

    lines = [
        "# Laporan Dataset Komentar TikTok Live (10.000 Komentar)",
        "",
        "## Ringkasan",
        f"- Total komentar: {len(rows)}",
        f"- Intent valid: {'ya' if not bad_intent else 'TIDAK (' + str(len(bad_intent)) + ')'}",
        f"- Sentiment valid: {'ya' if not bad_sent else 'TIDAK (' + str(len(bad_sent)) + ')'}",
        f"- Duplikat comment_id: {'tidak ada' if len(set(ids)) == len(ids) else 'ADA'}",
        "",
        "## Sebaran Intent",
        "",
        "| Intent | Jumlah |",
        "|---|---|",
    ]
    for intent in sorted(intent_counts):
        lines.append(f"| {intent} | {intent_counts[intent]} |")

    lines += [
        "",
        "## Sebaran Sentiment",
        "",
        "| Sentiment | Jumlah |",
        "|---|---|",
    ]
    for s in sorted(sentiment_counts):
        lines.append(f"| {s} | {sentiment_counts[s]} |")

    lines += ["", "## Contoh (10 per intent)", ""]
    shown = {}
    for r in rows:
        if shown.get(r["intent"], 0) >= 10:
            continue
        shown[r["intent"]] = shown.get(r["intent"], 0) + 1
        lines.append(f"- `{r['comment_id']}` [{r['intent']}/{r['sentiment']}] {r['text']}")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    if errors:
        print("VALIDASI GAGAL:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)

    print("VALIDASI LULUS: 10000 baris, 8 intent x 1250, sentiment valid")
    print("report:", REPORT)


if __name__ == "__main__":
    main()